from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class RatingSeason(models.Model):
    year = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-year",)

    def __str__(self):
        return self.name


class RatingRuleVersion(models.Model):
    season = models.ForeignKey(RatingSeason, on_delete=models.PROTECT, related_name="rule_versions")
    discipline = models.ForeignKey("catalogs.Discipline", on_delete=models.PROTECT, related_name="rating_rule_versions")
    version = models.PositiveIntegerField()
    effective_from = models.DateField(null=True, blank=True)
    effective_until = models.DateField(null=True, blank=True)
    coefficient_threshold = models.PositiveSmallIntegerField(default=2)
    stability_coefficient = models.DecimalField(max_digits=4, decimal_places=2, default="1.20")
    rounding_places = models.PositiveSmallIntegerField(default=2)
    rounding_mode = models.CharField(max_length=20, default="ROUND_HALF_UP")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_rating_rules")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("season_id", "discipline_id", "-version")
        constraints = [
            models.UniqueConstraint(fields=("season", "discipline", "version"), name="unique_rating_rule_version"),
            models.CheckConstraint(condition=Q(coefficient_threshold__gte=1), name="rating_threshold_positive"),
        ]

    def clean(self):
        if self.effective_from and self.effective_until and self.effective_from > self.effective_until:
            raise ValidationError("effective_from cannot exceed effective_until")


class RatingPointRule(models.Model):
    rule_version = models.ForeignKey(RatingRuleVersion, on_delete=models.PROTECT, related_name="point_rules")
    competition_level = models.CharField(max_length=100)
    place = models.PositiveSmallIntegerField()
    points = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        ordering = ("competition_level", "place")
        constraints = [
            models.UniqueConstraint(fields=("rule_version", "competition_level", "place"), name="unique_rating_point_rule"),
            models.CheckConstraint(condition=Q(place__gte=1), name="rating_place_positive"),
        ]


class AthleteRestriction(models.Model):
    class Kind(models.TextChoices):
        SUSPENSION = "suspension", "Приостановление"
        DISQUALIFICATION = "disqualification", "Дисквалификация"

    class Status(models.TextChoices):
        ACTIVE = "active", "Активно"
        REVOKED = "revoked", "Отменено"

    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="rating_restrictions")
    kind = models.CharField(max_length=24, choices=Kind.choices)
    starts_at = models.DateField()
    ends_at = models.DateField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    reason_private = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_rating_restrictions")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-starts_at", "-pk")
        constraints = [models.CheckConstraint(condition=Q(ends_at__gte=models.F("starts_at")), name="restriction_end_after_start")]

    def clean(self):
        if self.starts_at > self.ends_at:
            raise ValidationError("Restriction end must not precede start")

    def is_active_on(self, day=None):
        day = day or timezone.localdate()
        return self.status == self.Status.ACTIVE and self.starts_at <= day <= self.ends_at


class RatingContribution(models.Model):
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="rating_contributions")
    competition = models.ForeignKey("competitions.Competition", on_delete=models.PROTECT, related_name="rating_contributions")
    discipline = models.ForeignKey("catalogs.Discipline", on_delete=models.PROTECT, related_name="rating_contributions")
    season = models.ForeignKey(RatingSeason, on_delete=models.PROTECT, related_name="contributions")
    publication = models.ForeignKey("competitions.ProtocolPublication", on_delete=models.PROTECT, related_name="rating_contributions")
    rule_version = models.ForeignKey(RatingRuleVersion, on_delete=models.PROTECT, related_name="contributions")
    application_id = models.PositiveBigIntegerField()
    result_snapshot = models.JSONField(default=dict)
    placement = models.PositiveSmallIntegerField()
    age_group = models.CharField(max_length=100, blank=True)
    awarded_points = models.DecimalField(max_digits=8, decimal_places=2)
    is_current = models.BooleanField(default=True)
    superseded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-awarded_points", "competition__starts_at", "pk")
        constraints = [
            models.UniqueConstraint(fields=("athlete", "competition", "season", "discipline"), condition=Q(is_current=True), name="unique_current_rating_contribution"),
        ]


class AthleteRating(models.Model):
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ratings")
    season = models.ForeignKey(RatingSeason, on_delete=models.PROTECT, related_name="ratings")
    discipline = models.ForeignKey("catalogs.Discipline", on_delete=models.PROTECT, related_name="athlete_ratings")
    rule_version = models.ForeignKey(RatingRuleVersion, on_delete=models.PROTECT, related_name="ratings")
    base_score = models.DecimalField(max_digits=10, decimal_places=2)
    prize_count = models.PositiveIntegerField(default=0)
    coefficient = models.DecimalField(max_digits=4, decimal_places=2)
    rating_score = models.DecimalField(max_digits=10, decimal_places=2)
    calculated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-rating_score", "athlete_id")
        constraints = [models.UniqueConstraint(fields=("athlete", "season", "discipline"), name="unique_athlete_rating")]
