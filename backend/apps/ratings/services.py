from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_UP, Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import UserRole
from apps.competitions.models import Competition, ProtocolPublication
from apps.competitions.services import audit
from apps.qualifications.models import SportRank, SportRankHistory

from .models import (
    AthleteRating,
    AthleteRestriction,
    RatingContribution,
    RatingPointRule,
    RatingRuleVersion,
    RatingSeason,
)

DEFAULT_POINTS = {
    "Russian Championship": {1: Decimal("100"), 2: Decimal("80"), 3: Decimal("60")},
    "Russian Junior Championship": {1: Decimal("80"), 2: Decimal("60"), 3: Decimal("40")},
    "Interregional / district": {1: Decimal("60"), 2: Decimal("45"), 3: Decimal("30")},
    "Regional": {1: Decimal("40"), 2: Decimal("30"), 3: Decimal("20")},
}
LEVEL_ALIASES = {
    "russian championship": "Russian Championship",
    "russian_championship": "Russian Championship",
    "российский чемпионат": "Russian Championship",
    "russian junior championship": "Russian Junior Championship",
    "russian_junior_championship": "Russian Junior Championship",
    "российский юниорский чемпионат": "Russian Junior Championship",
    "interregional": "Interregional / district",
    "interregional / district": "Interregional / district",
    "interregional_district": "Interregional / district",
    "district": "Interregional / district",
    "межрегиональный": "Interregional / district",
    "окружной": "Interregional / district",
    "regional": "Regional",
    "региональный": "Regional",
}


def require_federation(request):
    role = request.session.get("active_role")
    if not request.user.is_authenticated or role != UserRole.Role.FEDERATION or not request.user.role_assignments.filter(role=role).exists():
        raise PermissionDenied("Active federation role required")


def season_for_year(year):
    season, _ = RatingSeason.objects.get_or_create(year=year, defaults={"name": f"Сезон {year}"})
    return season


def normalized_level(level):
    return LEVEL_ALIASES.get(level.strip().lower(), level)


def ensure_default_rule(season, discipline, actor=None):
    if actor is not None and not hasattr(actor, "role_assignments"):
        actor = None
    if actor is not None and not actor.role_assignments.filter(role=UserRole.Role.FEDERATION).exists():
        raise PermissionDenied("Federation author required for rating rules")
    actor = actor or discipline.rating_rule_versions.filter(created_by__role_assignments__role=UserRole.Role.FEDERATION).order_by("created_by_id").values_list("created_by", flat=True).first()
    if not actor:
        actor = discipline.competition_set.filter(created_by__role_assignments__role=UserRole.Role.FEDERATION).order_by("created_by_id").values_list("created_by", flat=True).first()
    if not actor:
        raise ValidationError("A federation author is required to create rating rules")
    actor_id = actor.pk if hasattr(actor, "pk") else actor
    rule, created = RatingRuleVersion.objects.get_or_create(
        season=season, discipline=discipline, version=1,
        defaults={"created_by_id": actor_id, "effective_from": timezone.datetime(season.year, 1, 1).date()},
    )
    if created:
        RatingPointRule.objects.bulk_create([
            RatingPointRule(rule_version=rule, competition_level=level, place=place, points=points)
            for level, table in DEFAULT_POINTS.items() for place, points in table.items()
        ])
    return rule


def active_restriction(athlete_id, day=None):
    day = day or timezone.localdate()
    return AthleteRestriction.objects.filter(
        athlete_id=athlete_id, status=AthleteRestriction.Status.ACTIVE,
        starts_at__lte=day, ends_at__gte=day,
    ).first()


def current_rank_level(athlete_id):
    order = {value: index for index, (value, _label) in enumerate(SportRank.choices)}
    rank = SportRankHistory.objects.filter(athlete_id=athlete_id, valid_until__gte=timezone.localdate()).order_by("-valid_until", "-assigned_on", "-pk").first()
    return order.get(rank.rank, -1) if rank else -1


def _latest_publications(competition_ids):
    latest = {}
    for publication in ProtocolPublication.objects.filter(competition_id__in=competition_ids).order_by("competition_id", "-version"):
        latest.setdefault(publication.competition_id, publication)
    return latest


@transaction.atomic
def calculate_ratings(*, season, discipline, actor=None):
    season = RatingSeason.objects.select_for_update().get(pk=season.pk)
    rule = RatingRuleVersion.objects.filter(season=season, discipline=discipline, is_active=True).order_by("-version").first()
    if not rule:
        rule = ensure_default_rule(season, discipline, actor)
    points = {(normalized_level(row.competition_level), row.place): row for row in RatingPointRule.objects.filter(rule_version=rule)}
    competitions = list(Competition.objects.filter(discipline=discipline, starts_at__year=season.year, state__in=(Competition.State.PUBLISHED, Competition.State.CLOSED)).select_related("discipline"))
    publications = _latest_publications([item.pk for item in competitions])
    RatingContribution.objects.filter(season=season, discipline=discipline, is_current=True).update(is_current=False, superseded_at=timezone.now())
    totals = {}
    for competition in competitions:
        publication = publications.get(competition.pk)
        if not publication:
            continue
        for row in publication.snapshot.get("rows", []):
            place = row.get("place")
            if row.get("status") != "classified" or not isinstance(place, int) or place < 1:
                continue
            point_rule = points.get((normalized_level(competition.level), place))
            if not point_rule:
                continue
            athlete_id = row.get("athlete_id")
            if not athlete_id or active_restriction(athlete_id, competition.starts_at.date()):
                continue
            athlete_totals = totals.setdefault(athlete_id, {"base": Decimal("0"), "prizes": 0, "rows": []})
            athlete_totals["base"] += Decimal(str(point_rule.points))
            athlete_totals["prizes"] += 1 if place <= 3 else 0
            athlete_totals["rows"].append((competition, publication, row, point_rule))
    AthleteRating.objects.filter(season=season, discipline=discipline).delete()
    result = []
    quant = Decimal("1").scaleb(-rule.rounding_places)
    for athlete_id, data in totals.items():
        coefficient = Decimal(str(rule.stability_coefficient)) if data["prizes"] >= rule.coefficient_threshold else Decimal("1.00")
        rounding = {"ROUND_HALF_UP": ROUND_HALF_UP, "ROUND_HALF_EVEN": ROUND_HALF_EVEN, "ROUND_DOWN": ROUND_DOWN, "ROUND_UP": ROUND_UP}.get(rule.rounding_mode)
        if rounding is None:
            raise ValidationError(f"Unsupported rounding mode: {rule.rounding_mode}")
        score = (data["base"] * coefficient).quantize(quant, rounding=rounding)
        rating = AthleteRating.objects.create(
            athlete_id=athlete_id, season=season, discipline=discipline, rule_version=rule,
            base_score=data["base"].quantize(quant), prize_count=data["prizes"], coefficient=coefficient, rating_score=score,
        )
        for competition, publication, row, point_rule in data["rows"]:
            RatingContribution.objects.create(
                athlete_id=athlete_id, competition=competition, discipline=discipline, season=season,
                publication=publication, rule_version=rule, application_id=row.get("application_id") or 0,
                result_snapshot=row, placement=row["place"], age_group=row.get("age_group", ""), awarded_points=point_rule.points,
            )
        result.append(rating)
    if actor:
        audit(actor, "ratings.calculated", rule, after={"season": season.year, "discipline": discipline.code, "count": len(result)})
    return result


def create_rule_version(*, actor, season, discipline, validated_data):
    require_actor = actor.role_assignments.filter(role=UserRole.Role.FEDERATION).exists()
    if not require_actor:
        raise PermissionDenied("Federation role required")
    point_rules = validated_data.pop("point_rules", [])
    last = RatingRuleVersion.objects.filter(season=season, discipline=discipline).order_by("-version").first()
    rule = RatingRuleVersion.objects.create(
        season=season, discipline=discipline, version=(last.version + 1 if last else 1), created_by=actor,
        **validated_data,
    )
    for item in point_rules:
        RatingPointRule.objects.create(rule_version=rule, **item)
    audit(actor, "rating_rule.created", rule, after={"season": season.year, "discipline": discipline.code, "version": rule.version})
    return rule
