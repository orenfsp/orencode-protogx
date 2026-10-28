from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import Guardian, UserRole, has_current_consent
from apps.competitions.models import AuditEvent
from apps.competitions.services import age_on
from apps.ratings.models import AthleteRating
from apps.ratings.services import active_restriction

from .models import RegionalTeam, TeamDecisionHistory, TeamMembership


def require_federation(request):
    role = request.session.get("active_role")
    if not request.user.is_authenticated or role != UserRole.Role.FEDERATION or not request.user.role_assignments.filter(role=role).exists():
        raise PermissionDenied("Active federation role required")


def eligibility_snapshot(*, athlete, team):
    reference = date(team.season.year, 1, 1)
    age = age_on(athlete.date_of_birth, reference) if athlete.date_of_birth else None
    minor_guardian = age is not None and age < 18 and Guardian.objects.filter(minor=athlete, confirmation_status="verified").exists()
    restriction = active_restriction(athlete.pk)
    rating = AthleteRating.objects.filter(athlete=athlete, season=team.season, discipline=team.discipline).first()
    return {
        "eligible": bool(athlete.date_of_birth and age is not None and team.age_group.min_age <= age <= team.age_group.max_age and has_current_consent(athlete) and (age >= 18 or minor_guardian) and restriction is None),
        "age": age,
        "age_group": team.age_group.name,
        "consent": has_current_consent(athlete),
        "guardian_verified": minor_guardian,
        "restriction": restriction.kind if restriction else None,
        "rating_score": str(rating.rating_score) if rating else None,
        "rating_id": rating.pk if rating else None,
        "checked_on": reference.isoformat(),
        "restriction_checked_on": timezone.localdate().isoformat(),
    }


def validate_athlete_for_team(athlete, team):
    if not athlete.role_assignments.filter(role=UserRole.Role.ATHLETE).exists():
        raise ValidationError("Athlete role is required")
    if not athlete.date_of_birth:
        raise ValidationError("Athlete date of birth is required")
    snapshot = eligibility_snapshot(athlete=athlete, team=team)
    if not snapshot["eligible"]:
        raise ValidationError({"athlete": "Athlete is outside the selected age group or has an active restriction/invalid consent"})
    return snapshot


def _record(actor, team, action, membership=None, before=None, after=None):
    after = dict(after or {})
    after.setdefault("active_role", UserRole.Role.FEDERATION)
    TeamDecisionHistory.objects.create(team=team, membership=membership, actor=actor, action=action, before=before or {}, after=after)
    AuditEvent.objects.create(actor=actor, action=f"regional_team.{action}", target_type=team._meta.model_name, target_id=team.pk, before=before or {}, after=after)


def _invalidate_finalization(actor, team):
    if team.status == RegionalTeam.Status.PUBLISHED:
        team.status = RegionalTeam.Status.DRAFT
        team.save(update_fields=("status", "updated_at"))
        _record(actor, team, "finalization_invalidated", before={"status": RegionalTeam.Status.PUBLISHED}, after={"status": team.status})


@transaction.atomic
def create_team(*, actor, validated_data):
    team = RegionalTeam.objects.create(created_by=actor, **validated_data)
    _record(actor, team, "created", after={"name": team.name, "season": team.season.year, "discipline": team.discipline.code, "age_group": team.age_group.name})
    return team


@transaction.atomic
def add_member(*, actor, team, athlete, note=""):
    team = RegionalTeam.objects.select_for_update().get(pk=team.pk)
    snapshot = validate_athlete_for_team(athlete, team)
    existing = TeamMembership.objects.filter(team=team, athlete=athlete, removed_at__isnull=True).first()
    if existing:
        raise ValidationError({"athlete": "Athlete is already selected"})
    position = (TeamMembership.objects.filter(team=team, removed_at__isnull=True).order_by("-position").values_list("position", flat=True).first() or 0) + 1
    membership = TeamMembership.objects.create(team=team, athlete=athlete, position=position, selected_by=actor, eligibility_snapshot=snapshot, selection_note=note)
    _invalidate_finalization(actor, team)
    _record(actor, team, "member_added", membership, after={"athlete_id": athlete.pk, "position": position, "eligibility": snapshot})
    return membership


@transaction.atomic
def remove_member(*, actor, membership, reason=""):
    RegionalTeam.objects.select_for_update().get(pk=membership.team_id)
    membership = TeamMembership.objects.select_for_update().select_related("team", "athlete").get(pk=membership.pk)
    if membership.removed_at:
        raise ValidationError("Membership is already removed")
    before = {"athlete_id": membership.athlete_id, "position": membership.position}
    membership.removed_at = timezone.now()
    membership.removal_reason = reason
    membership.save(update_fields=("removed_at", "removal_reason"))
    _invalidate_finalization(actor, membership.team)
    _record(actor, membership.team, "member_removed", membership, before=before, after={"reason": reason})
    return membership


@transaction.atomic
def reorder_members(*, actor, team, member_ids):
    team = RegionalTeam.objects.select_for_update().get(pk=team.pk)
    memberships = list(TeamMembership.objects.select_for_update().filter(team=team, removed_at__isnull=True))
    current = {m.pk: m for m in memberships}
    try:
        requested = [int(item) for item in member_ids]
    except (TypeError, ValueError):
        raise ValidationError({"member_ids": "Member ids must be integers"})
    if set(requested) != set(current) or len(requested) != len(current):
        raise ValidationError({"member_ids": "All active members must be included exactly once"})
    before = {str(m.pk): m.position for m in memberships}
    if requested == [m.pk for m in sorted(memberships, key=lambda m: m.position)]:
        return list(sorted(memberships, key=lambda m: m.position))
    # Move all positions above the existing range first: the conditional unique
    # constraint is immediate on both PostgreSQL and SQLite.
    offset = max((m.position for m in memberships), default=0) + len(memberships)
    for index, member in enumerate(memberships, start=1):
        member.position = offset + index
        member.save(update_fields=("position",))
    for position, member_id in enumerate(requested, start=1):
        current[member_id].position = position
        current[member_id].save(update_fields=("position",))
    _invalidate_finalization(actor, team)
    _record(actor, team, "members_reordered", before={"positions": before}, after={"positions": {str(item): index for index, item in enumerate(requested, start=1)}})
    return list(TeamMembership.objects.filter(team=team, removed_at__isnull=True).select_related("athlete").order_by("position"))


@transaction.atomic
def publish_team(*, actor, team):
    team = RegionalTeam.objects.select_for_update().get(pk=team.pk)
    if team.status == RegionalTeam.Status.PUBLISHED:
        return team
    if not team.memberships.filter(removed_at__isnull=True).exists():
        raise ValidationError("A team must have at least one active member")
    before = {"status": team.status}
    team.status = RegionalTeam.Status.PUBLISHED
    team.save(update_fields=("status", "updated_at"))
    _record(actor, team, "published", before=before, after={"status": team.status})
    return team


def candidate_rows(team):
    # Include all athlete accounts so federation can manually select an eligible athlete without a rating.
    from apps.accounts.models import User
    from apps.qualifications.models import SportRankHistory

    users = User.objects.filter(role_assignments__role=UserRole.Role.ATHLETE).distinct().order_by("full_name", "pk")
    selected = set(team.memberships.filter(removed_at__isnull=True).values_list("athlete_id", flat=True))
    ratings = list(AthleteRating.objects.filter(season=team.season, discipline=team.discipline).select_related("athlete").order_by("-rating_score", "athlete__full_name", "athlete_id"))
    rating_map = {rating.athlete_id: (index, rating) for index, rating in enumerate(ratings, 1)}
    rows = []
    for athlete in users:
        snap = eligibility_snapshot(athlete=athlete, team=team)
        position, rating = rating_map.get(athlete.pk, (None, None))
        rank = SportRankHistory.objects.filter(athlete=athlete, discipline=team.discipline, assigned_on__lte=timezone.localdate(), valid_until__gte=timezone.localdate()).order_by("-assigned_on", "-pk").first()
        rows.append({"id": athlete.pk, "full_name": athlete.full_name, "email": athlete.email, "sport_rank": rank.get_rank_display() if rank else None, "eligible": snap["eligible"], "selected": athlete.pk in selected, "eligibility": snap, "rating": {"score": str(rating.rating_score), "base_score": str(rating.base_score), "prize_count": rating.prize_count, "position": position} if rating else None})
    return sorted(rows, key=lambda row: (not row["eligible"], -(float(row["rating"]["score"]) if row["rating"] else 0), row["full_name"]))
