from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class AgeGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    min_age = models.PositiveSmallIntegerField()
    max_age = models.PositiveSmallIntegerField()

    def clean(self):
        if self.min_age > self.max_age:
            raise ValidationError("Minimum age cannot exceed maximum age")


class CalendarEntry(models.Model):
    class Source(models.TextChoices):
        EKP = "ekp", "Единый календарный план"
        REGIONAL = "regional", "Региональный календарь"

    source = models.CharField(max_length=16, choices=Source.choices)
    entry_number = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    year = models.PositiveSmallIntegerField()
    reference_url = models.URLField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source", "entry_number", "year"], name="unique_calendar_entry")]


class ProtocolTemplate(models.Model):
    discipline = models.ForeignKey("catalogs.Discipline", on_delete=models.PROTECT, related_name="protocol_templates")
    version = models.PositiveIntegerField()
    name = models.CharField(max_length=150)
    competition_type = models.CharField(max_length=100, blank=True)
    rule_version = models.CharField(max_length=100, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    # Each metric: {key, label, type: number|string, required: boolean}.
    metric_fields = models.JSONField(default=list)
    # Columns are known keys (athlete, age_group, status, place, score) or metric keys.
    columns = models.JSONField(default=list)
    sections = models.JSONField(default=list)
    signature_roles = models.JSONField(default=list)
    sort = models.JSONField(default=dict)
    source_url = models.URLField(blank=True)
    source_verified = models.BooleanField(default=False)
    source_note = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["discipline", "version"], name="unique_discipline_template_version")]
        ordering = ("discipline", "-version")


class Competition(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликовано"
        CLOSED = "closed", "Завершено"

    title = models.CharField(max_length=250)
    discipline = models.ForeignKey("catalogs.Discipline", on_delete=models.PROTECT)
    age_groups = models.ManyToManyField(AgeGroup, related_name="competitions")
    level = models.CharField(max_length=100)
    competition_type = models.CharField(max_length=100)
    format = models.CharField(max_length=16, choices=[("online", "Онлайн"), ("in_person", "Очное"), ("hybrid", "Гибридное")])
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    registration_deadline = models.DateTimeField()
    registration_open = models.BooleanField(default=True)
    age_reference_date = models.DateField(null=True, blank=True)
    allow_ties = models.BooleanField(default=False)
    location = models.CharField(max_length=250)
    regulations = models.TextField()
    calendar_entry = models.ForeignKey(CalendarEntry, on_delete=models.PROTECT, null=True, blank=True)
    template = models.ForeignKey(ProtocolTemplate, on_delete=models.PROTECT)
    state = models.CharField(max_length=16, choices=State.choices, default=State.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


class CompetitionType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)


class CompetitionStage(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name="stages")
    order = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=150)
    format = models.CharField(max_length=16, choices=Competition._meta.get_field("format").choices)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["competition", "order"], name="unique_competition_stage_order")]
        ordering = ("order",)


class CoachAthleteLink(models.Model):
    coach = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coached_links")
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coach_links")
    discipline = models.ForeignKey("catalogs.Discipline", on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=[("pending", "Ожидает"), ("confirmed", "Подтверждено"), ("rejected", "Отклонено"), ("suspended", "Приостановлена"), ("ended", "Завершена")], default="pending")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["coach", "athlete", "discipline"], name="unique_coach_athlete_discipline")]


class Application(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "На рассмотрении"
        APPROVED = "approved", "Одобрена"
        REJECTED = "rejected", "Отклонена"

    competition = models.ForeignKey(Competition, on_delete=models.PROTECT, related_name="applications")
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="competition_applications")
    age_group = models.ForeignKey(AgeGroup, on_delete=models.PROTECT)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="submitted_applications")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    decision_reason = models.TextField(blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="decided_applications")
    submitted_at = models.DateTimeField(default=timezone.now)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["competition", "athlete"], name="unique_competition_athlete_application")]


class JudgeAssignment(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.PROTECT, related_name="judge_assignments")
    judge = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="judge_assignments")
    role_label = models.CharField(max_length=100)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assigned_judges")
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["competition", "judge"], name="unique_competition_judge")]


class Result(models.Model):
    class Status(models.TextChoices):
        CLASSIFIED = "classified", "Классифицирован"
        NO_SHOW = "no_show", "Не явился"
        UNCLASSIFIED = "unclassified", "Без результата"
        DISQUALIFIED = "disqualified", "Дисквалифицирован"

    application = models.OneToOneField(Application, on_delete=models.PROTECT, related_name="result")
    status = models.CharField(max_length=20, choices=Status.choices)
    place = models.PositiveSmallIntegerField(null=True, blank=True)
    score = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    metrics = models.JSONField(default=dict)
    validated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="validated_results")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="entered_results")
    updated_at = models.DateTimeField(auto_now=True)


class ProtocolPublication(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.PROTECT, related_name="protocols")
    version = models.PositiveIntegerField()
    template = models.ForeignKey(ProtocolTemplate, on_delete=models.PROTECT)
    snapshot = models.JSONField()
    correction_reason = models.TextField(blank=True)
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    published_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["competition", "version"], name="unique_competition_protocol_version")]
        ordering = ("-version",)


class AuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    active_role = models.CharField(max_length=16, blank=True, default="")
    competition = models.ForeignKey(Competition, null=True, blank=True, on_delete=models.PROTECT)
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=80)
    target_id = models.PositiveBigIntegerField()
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-created_at",)
