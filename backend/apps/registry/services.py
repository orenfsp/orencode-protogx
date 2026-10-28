"""Registry writes: all period writers must lock the athlete first.

Intervals use inclusive dates. Different disciplines may overlap; each other
dimension is exclusive. Missing periods mean unknown, not an inferred value.
"""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.accounts.models import AthleteProfile, User, UserRole
from apps.competitions.services import audit

from .models import (
    DisciplinePeriod,
    MunicipalityPeriod,
    OrganizationPeriod,
    ParticipationPeriod,
    TrainingStagePeriod,
)

PERIOD_MODELS = (ParticipationPeriod, DisciplinePeriod, OrganizationPeriod, MunicipalityPeriod, TrainingStagePeriod)


class StalePeriod(APIException):
    status_code = 409
    default_detail = "The period changed since it was loaded; refresh and retry"
    default_code = "stale_period"


def period_values(period):
    values = {"starts_on": period.starts_on.isoformat(), "ends_on": period.ends_on.isoformat() if period.ends_on else None}
    for field in ("discipline_id", "organization_id", "municipality", "stage"):
        if hasattr(period, field):
            values[field.removesuffix("_id")] = getattr(period, field)
    return values


@transaction.atomic
def correct_period(*, actor, model, athlete, period_id, expected, corrected, reason):
    if model not in PERIOD_MODELS:
        raise ValueError("Unsupported period model")
    athlete = User.objects.select_for_update().get(pk=athlete.pk)
    period = model.objects.select_for_update().filter(pk=period_id, athlete=athlete).first()
    if not period:
        raise ValidationError({"period": "Period not found for athlete"})
    before = period_values(period)
    if expected != before:
        raise StalePeriod()
    start, end = corrected["starts_on"], corrected.get("ends_on")
    if end is not None and end < start:
        raise ValidationError({"ends_on": "End must not precede start"})
    if athlete.date_of_birth and start < athlete.date_of_birth:
        raise ValidationError({"starts_on": "Period cannot start before the athlete's birth"})
    if model is OrganizationPeriod and ((period.ends_on is None) != (end is None)):
        raise ValidationError({"ends_on": "Use an organization transfer to change current status"})
    if model is OrganizationPeriod and end is None and start > timezone.localdate():
        raise ValidationError({"starts_on": "Current affiliation cannot start in the future"})
    overlap = model.objects.filter(athlete=athlete).exclude(pk=period.pk).filter(Q(ends_on__isnull=True) | Q(ends_on__gte=start))
    if end is not None:
        overlap = overlap.filter(starts_on__lte=end)
    if model is DisciplinePeriod:
        overlap = overlap.filter(discipline=corrected["discipline"])
    if overlap.exists():
        raise ValidationError({"starts_on": "Period overlaps an existing period"})
    for key, value in corrected.items():
        setattr(period, key, value)
    try:
        with transaction.atomic():
            period.save()
    except IntegrityError as exc:
        raise ValidationError({"starts_on": "Period conflicts with another record"}) from exc
    if model is OrganizationPeriod and end is None:
        profile = AthleteProfile.objects.select_for_update().filter(user=athlete).first()
        if not profile or profile.organization_id != before["organization"]:
            raise ValidationError({"organization": "Current profile and history are inconsistent"})
        profile.organization = period.organization
        profile.save(update_fields=["organization"])
    after = period_values(period)
    audit(actor, "registry.period_corrected", period, before=before, after={"values": after, "reason": reason})
    return period


@transaction.atomic
def add_period(*, actor, model, athlete, starts_on, ends_on=None, **dimension):
    if model not in PERIOD_MODELS:
        raise ValueError("Unsupported period model")
    athlete = User.objects.select_for_update().get(pk=athlete.pk)
    if not athlete.role_assignments.filter(role=UserRole.Role.ATHLETE).exists():
        raise ValidationError({"athlete": "Athlete role is required"})
    if ends_on is not None and ends_on < starts_on:
        raise ValidationError({"ends_on": "End must not precede start"})
    if athlete.date_of_birth and starts_on < athlete.date_of_birth:
        raise ValidationError({"starts_on": "Period cannot start before the athlete's birth"})
    overlapping = model.objects.filter(athlete=athlete).filter(Q(ends_on__isnull=True) | Q(ends_on__gte=starts_on))
    if ends_on is not None:
        overlapping = overlapping.filter(starts_on__lte=ends_on)
    if model is DisciplinePeriod:
        overlapping = overlapping.filter(discipline=dimension.get("discipline"))
    if model is OrganizationPeriod and ends_on is None:
        profile = AthleteProfile.objects.filter(user=athlete).first()
        if starts_on > timezone.localdate() or not profile or profile.organization_id != getattr(dimension.get("organization"), "pk", None):
            raise ValidationError({"organization": "Open history must match the current profile and must not begin in the future"})
    if overlapping.exists():
        raise ValidationError({"starts_on": "Period overlaps an existing period"})
    period = model.objects.create(athlete=athlete, starts_on=starts_on, ends_on=ends_on, **dimension)
    changes = {"athlete_id": athlete.pk, "starts_on": starts_on.isoformat(), "ends_on": ends_on.isoformat() if ends_on else None}
    if model is DisciplinePeriod:
        changes["discipline_id"] = period.discipline_id
    elif model is OrganizationPeriod:
        changes["organization_id"] = period.organization_id
    elif model is MunicipalityPeriod:
        changes["municipality"] = period.municipality
    elif model is TrainingStagePeriod:
        changes["stage"] = period.stage
    audit(actor, "registry.period_created", period, after=changes)
    return period


@transaction.atomic
def transfer_organization(*, actor, athlete, organization, effective_on):
    """Close a known current affiliation and create its successor atomically.

    Unknown histories are deliberately not synthesized. Future transfers need
    scheduling and are rejected until that workflow is implemented.
    """
    athlete = User.objects.select_for_update().get(pk=athlete.pk)
    if effective_on > timezone.localdate():
        raise ValidationError({"effective_on": "Future transfers are not supported"})
    profile = AthleteProfile.objects.select_for_update().filter(user=athlete).first()
    current = OrganizationPeriod.objects.select_for_update().filter(athlete=athlete, ends_on__isnull=True).first()
    if not profile or not current or profile.organization_id != current.organization_id:
        raise ValidationError({"organization": "Current affiliation history is unknown or inconsistent"})
    if current.organization_id == organization.pk:
        raise ValidationError({"organization": "Athlete already belongs to this organization"})
    if effective_on <= current.starts_on:
        raise ValidationError({"effective_on": "Transfer must follow the current affiliation start"})
    current.ends_on = effective_on - timedelta(days=1)
    current.save(update_fields=["ends_on"])
    audit(actor, "registry.organization_period_closed", current, before={"ends_on": None}, after={"ends_on": current.ends_on.isoformat()})
    old_organization = profile.organization_id
    profile.organization = organization
    profile.save(update_fields=["organization"])
    successor = add_period(actor=actor, model=OrganizationPeriod, athlete=athlete, starts_on=effective_on, organization=organization)
    audit(actor, "registry.organization_transferred", profile, before={"organization_id": old_organization}, after={"organization_id": organization.pk, "effective_on": effective_on.isoformat()})
    return successor


@transaction.atomic
def close_period(*, actor, model, athlete, period_id, ends_on):
    if model not in PERIOD_MODELS or model is OrganizationPeriod:
        raise ValidationError({"kind": "Use the transfer workflow for organizations"})
    athlete = User.objects.select_for_update().get(pk=athlete.pk)
    period = model.objects.select_for_update().filter(pk=period_id, athlete=athlete).first()
    if not period or period.ends_on is not None:
        raise ValidationError({"period": "Open period not found"})
    if ends_on < period.starts_on:
        raise ValidationError({"ends_on": "End must not precede start"})
    period.ends_on = ends_on
    period.save(update_fields=["ends_on"])
    audit(actor, "registry.period_closed", period, before={"ends_on": None}, after={"ends_on": ends_on.isoformat()})
    return period
