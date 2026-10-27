from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class RegionalTeam(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Сформирован"

    season = models.ForeignKey("ratings.RatingSeason", on_delete=models.PROTECT, related_name="regional_teams")
    discipline = models.ForeignKey("catalogs.Discipline", on_delete=models.PROTECT, related_name="regional_teams")
    age_group = models.ForeignKey("competitions.AgeGroup", on_delete=models.PROTECT, related_name="regional_teams")
    name = models.CharField(max_length=200)
    region = models.CharField(max_length=120, default="Оренбургская область")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_regional_teams")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-season__year", "discipline__name", "name")
        constraints = [models.UniqueConstraint(fields=("season", "discipline", "age_group", "name"), name="unique_regional_team_identity")]


class TeamMembership(models.Model):
    team = models.ForeignKey(RegionalTeam, on_delete=models.CASCADE, related_name="memberships")
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="regional_team_memberships")
    position = models.PositiveIntegerField(default=1)
    selected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="selected_team_members")
    selected_at = models.DateTimeField(default=timezone.now)
    removed_at = models.DateTimeField(null=True, blank=True)
    removal_reason = models.TextField(blank=True)
    eligibility_snapshot = models.JSONField(default=dict)
    selection_note = models.TextField(blank=True)

    class Meta:
        ordering = ("position", "pk")
        constraints = [
            models.UniqueConstraint(fields=("team", "athlete"), condition=Q(removed_at__isnull=True), name="unique_active_team_athlete"),
            models.UniqueConstraint(fields=("team", "position"), condition=Q(removed_at__isnull=True), name="unique_active_team_position"),
        ]


class TeamDecisionHistory(models.Model):
    team = models.ForeignKey(RegionalTeam, on_delete=models.CASCADE, related_name="decision_history")
    membership = models.ForeignKey(TeamMembership, null=True, blank=True, on_delete=models.SET_NULL, related_name="decision_history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=32)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-created_at", "-pk")
