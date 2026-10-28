from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import Guardian, has_current_consent

from .models import (
    Application,
    AuditEvent,
    CoachAthleteLink,
    ProtocolPublication,
    Result,
)


def require_role(request, *roles):
    role = request.session.get("active_role")
    if role not in roles or not request.user.role_assignments.filter(role=role).exists():
        raise PermissionDenied("Active assigned role required")
    return role


@transaction.atomic
def audit(actor, action, target, *, competition=None, before=None, after=None):
    from apps.accounts.audit_context import active_role
    AuditEvent.objects.create(
        actor=actor, action=action, target_type=target._meta.model_name, target_id=target.pk,
        active_role=active_role.get(),
        competition=competition, before=before or {}, after=after or {},
    )
    from apps.notifications.services import domain_event
    domain_event(action, target)


def age_on(born: date, when: date) -> int:
    return when.year - born.year - ((when.month, when.day) < (born.month, born.day))


def check_application_eligibility(competition, athlete, age_group, submitted_by):
    if competition.state != "published":
        raise ValidationError("Competition is not published")
    if not competition.registration_open:
        raise ValidationError("Приём заявок закрыт федерацией")
    if timezone.now() >= competition.registration_deadline:
        raise ValidationError("Registration deadline has passed")
    if not athlete.role_assignments.filter(role="athlete").exists():
        raise ValidationError("Applicant must have athlete role")
    if not competition.age_groups.filter(pk=age_group.pk).exists():
        raise ValidationError("Age group is not offered")
    if not athlete.date_of_birth:
        raise ValidationError("Athlete date of birth is required")
    age = age_on(athlete.date_of_birth, competition.age_reference_date or competition.starts_at.date())
    if not age_group.min_age <= age <= age_group.max_age:
        raise ValidationError("Athlete is outside age group")
    if not has_current_consent(athlete):
        raise ValidationError("Personal data consent is required")
    if age < 18 and not Guardian.objects.filter(minor=athlete, confirmation_status="verified").exists():
        raise ValidationError("Verified guardian consent is required")
    if submitted_by.pk != athlete.pk and not CoachAthleteLink.objects.filter(
        coach=submitted_by, athlete=athlete, discipline=competition.discipline, status="confirmed"
    ).exists():
        raise PermissionDenied("Confirmed coach link is required")
    if Application.objects.filter(competition=competition, athlete=athlete).exists():
        raise ValidationError("Application already exists")


BASE_COLUMNS = {"athlete", "age_group", "status", "place", "score"}


def validate_template_definition(metric_fields, columns, sections=None, signature_roles=None, sort=None):
    if not isinstance(metric_fields, list) or not isinstance(columns, list) or not columns:
        raise ValidationError("Template fields and columns must be lists")
    keys = set()
    for field in metric_fields:
        if not isinstance(field, dict) or set(field) != {"key", "label", "type", "required"}:
            raise ValidationError("Each metric needs key, label, type and required")
        key = field["key"]
        if not isinstance(key, str) or not key.isidentifier() or key in BASE_COLUMNS or key in keys:
            raise ValidationError("Metric keys must be unique identifiers")
        if field["type"] not in ("number", "string") or not isinstance(field["label"], str) or not field["label"] or not isinstance(field["required"], bool):
            raise ValidationError("Invalid metric definition")
        keys.add(key)
    if any(not isinstance(column, str) or column not in BASE_COLUMNS | keys for column in columns):
        raise ValidationError("Unknown protocol column")
    if "athlete" not in columns or "status" not in columns or len(columns) != len(set(columns)):
        raise ValidationError("Protocol needs athlete and status columns without duplicates")
    if any(field["required"] and field["key"] not in columns for field in metric_fields):
        raise ValidationError("Required metrics must appear in protocol columns")
    if sections is not None and (not isinstance(sections, list) or "header" not in sections or "participants" not in sections or len(set(sections)) != len(sections) or any(item not in {"header", "participants", "judges", "signatures"} for item in sections)):
        raise ValidationError("Template sections must include header and participants")
    if signature_roles is not None and (not isinstance(signature_roles, list) or any(not isinstance(role, str) or not role.strip() or len(role) > 100 for role in signature_roles)):
        raise ValidationError("Invalid signature roles")
    if sort is not None and (not isinstance(sort, dict) or set(sort) != {"key", "direction"} or sort["key"] not in columns or sort["direction"] not in {"asc", "desc"}):
        raise ValidationError("Sort must choose a displayed column and direction")


def validate_result_data(application, status, place, score, metrics):
    if application.status != "approved":
        raise ValidationError("Only approved applications can have results")
    if status != Result.Status.CLASSIFIED:
        if place is not None or score is not None or metrics:
            raise ValidationError("Unclassified result cannot carry place, score or metrics")
        return
    if place is None and score is None:
        raise ValidationError("A classified result needs place or score")
    if place is not None and not application.competition.allow_ties and Result.objects.filter(
        application__competition=application.competition, application__status="approved",
        status=Result.Status.CLASSIFIED, place=place,
    ).exclude(application=application).exists():
        raise ValidationError("Place is already assigned; enable ties in competition rules to share a place")
    if not isinstance(metrics, dict):
        raise ValidationError("Metrics must be an object")
    fields = {item["key"]: item for item in application.competition.template.metric_fields}
    if set(metrics) - set(fields):
        raise ValidationError("Unknown metric field")
    for key, field in fields.items():
        value = metrics.get(key)
        if field["required"] and value is None:
            raise ValidationError(f"Metric {key} is required")
        if value is not None and (isinstance(value, bool) or (field["type"] == "number" and not isinstance(value, (int, float))) or (field["type"] == "string" and not isinstance(value, str))):
            raise ValidationError(f"Invalid value for metric {key}")


def protocol_snapshot(competition):
    template = competition.template
    applications = Application.objects.filter(competition=competition, status="approved").select_related("athlete", "age_group").order_by("athlete__full_name", "pk")
    rows = []
    for application in applications:
        result = Result.objects.filter(application=application).first()
        row = {
            "application_id": application.pk, "athlete_id": application.athlete_id,
            "athlete": application.athlete.full_name, "age_group": application.age_group.name,
            "status": result.status if result else "pending_result",
            "place": result.place if result and result.validated_by_id else None,
            "score": str(result.score) if result and result.validated_by_id and result.score is not None else None,
        }
        for field in template.metric_fields:
            row[field["key"]] = result.metrics.get(field["key"]) if result and result.validated_by_id else None
        rows.append(row)
    sort = template.sort or {"key": "place", "direction": "asc"}
    key = sort["key"]
    rows = sorted((row for row in rows if row.get(key) is not None), key=lambda row: row[key], reverse=sort["direction"] == "desc") + [row for row in rows if row.get(key) is None]
    labels = {"athlete": "Спортсмен", "age_group": "Возрастная группа", "status": "Статус", "place": "Место", "score": "Баллы"}
    labels.update({field["key"]: field["label"] for field in template.metric_fields})
    judges = list(competition.judge_assignments.select_related("judge").values("judge__full_name", "role_label"))
    return {
        "competition_id": competition.pk, "competition_title": competition.title,
        "discipline": competition.discipline.name, "template_id": template.pk,
        "template_version": template.version, "source_verified": template.source_verified,
        "source_note": template.source_note, "source_url": template.source_url,
        "sections": template.sections, "signature_roles": template.signature_roles, "sort": sort,
        "metadata": {"level": competition.level, "competition_type": competition.competition_type, "format": competition.format, "starts_at": competition.starts_at.isoformat(), "ends_at": competition.ends_at.isoformat(), "age_reference_date": (competition.age_reference_date or competition.starts_at.date()).isoformat(), "location": competition.location, "calendar_entry": competition.calendar_entry.entry_number if competition.calendar_entry else None, "stages": [{"order": stage.order, "name": stage.name, "format": stage.format, "starts_at": stage.starts_at.isoformat(), "ends_at": stage.ends_at.isoformat()} for stage in competition.stages.all()]},
        "judges": [{"name": item["judge__full_name"], "role": item["role_label"]} for item in judges],
        "columns": [{"key": key, "label": labels[key]} for key in template.columns],
        "rows": rows,
    }


@transaction.atomic
def publish_protocol(competition, actor, correction_reason=""):
    competition = type(competition).objects.select_for_update().get(pk=competition.pk)
    if competition.state != "published":
        raise ValidationError("Competition must be published")
    applications = list(Application.objects.select_for_update().filter(competition=competition).select_related("athlete"))
    if any(application.status == "pending" for application in applications):
        raise ValidationError("Moderate all applications before publishing protocol")
    results = list(Result.objects.select_for_update().filter(application__competition=competition, application__status="approved"))
    if any(result.validated_by_id is None for result in results):
        raise ValidationError("Validate entered results before publication")
    for application in applications:
        if application.status != "approved":
            continue
        athlete = application.athlete
        if not has_current_consent(athlete):
            raise ValidationError("Every approved athlete needs current personal data consent")
        if age_on(athlete.date_of_birth, competition.age_reference_date or competition.starts_at.date()) < 18 and not Guardian.objects.filter(minor=athlete, confirmation_status="verified").exists():
            raise ValidationError("Every approved minor needs verified guardian consent")
    snapshot = protocol_snapshot(competition)
    version = (competition.protocols.first().version if competition.protocols.exists() else 0) + 1
    if version > 1 and not correction_reason.strip():
        raise ValidationError("A correction reason is required for a new protocol version")
    publication = ProtocolPublication.objects.create(
        competition=competition, version=version, template=competition.template,
        snapshot=snapshot, published_by=actor, correction_reason=correction_reason.strip(),
    )
    audit(actor, "protocol.published", publication, competition=competition, after={"version": version, "correction_reason": publication.correction_reason})
    # Ratings consume the newly published immutable snapshot immediately. Import
    # lazily to keep the competitions app independent at module import time.
    from apps.ratings.services import calculate_ratings, season_for_year
    calculate_ratings(season=season_for_year(competition.starts_at.year), discipline=competition.discipline, actor=actor)
    return publication
