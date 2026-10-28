from django.conf import settings
from django.db import models
from django.db.models import F, Q


class StaffProfile(models.Model):
    """Registry metadata for existing coach/judge roles; identity stays on User."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="registry_staff_profiles")
    role = models.CharField(max_length=16, choices=[("coach", "Coach"), ("judge", "Judge")])
    organization = models.ForeignKey("catalogs.Organization", null=True, blank=True, on_delete=models.PROTECT)
    disciplines = models.ManyToManyField("catalogs.Discipline", blank=True, related_name="registry_staff_profiles")

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "role"), name="registry_staff_user_role_unique"), models.CheckConstraint(condition=Q(role__in=["coach", "judge"]), name="registry_staff_role_valid")]


class Period(models.Model):
    """Inclusive effective dates; a null end means the period is open."""

    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    starts_on = models.DateField()
    ends_on = models.DateField(null=True, blank=True)

    class Meta:
        abstract = True
        indexes = [models.Index(fields=["athlete", "starts_on", "ends_on"])]
        constraints = [models.CheckConstraint(condition=Q(ends_on__isnull=True) | Q(ends_on__gte=F("starts_on")), name="%(class)s_valid_dates")]


class ParticipationPeriod(Period):
    pass


class DisciplinePeriod(Period):
    discipline = models.ForeignKey("catalogs.Discipline", on_delete=models.PROTECT)


class OrganizationPeriod(Period):
    organization = models.ForeignKey("catalogs.Organization", on_delete=models.PROTECT)


class MunicipalityPeriod(Period):
    municipality = models.CharField(max_length=200)


class TrainingStagePeriod(Period):
    stage = models.CharField(max_length=200)
