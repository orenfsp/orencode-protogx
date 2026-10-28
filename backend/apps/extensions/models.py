import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.qualifications.models import SportRank


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    event_key = models.CharField(max_length=160)
    title = models.CharField(max_length=250)
    created_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True)
    sent_at = models.DateTimeField(null=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    failed = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["recipient", "event_key"], name="extension_notification_once")]


class ParticipationCertificate(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    application = models.ForeignKey("competitions.Application", on_delete=models.PROTECT)
    publication = models.ForeignKey("competitions.ProtocolPublication", on_delete=models.PROTECT)
    issued_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True)
    public_name = models.BooleanField(default=False)
    snapshot = models.JSONField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["athlete", "application", "publication"], name="extension_certificate_version_once")]


class JudgingDocument(models.Model):
    kind = models.CharField(max_length=20, choices=[("panel", "Состав коллегии"), ("judge_work", "Отчёт о судействе")])
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="generated_judging_documents")
    snapshot = models.JSONField()
    created_at = models.DateTimeField(default=timezone.now)


class TrainingOrganization(models.Model):
    organization = models.OneToOneField("catalogs.Organization", on_delete=models.PROTECT, related_name="training_card")
    organization_type = models.CharField(max_length=100)
    municipality = models.CharField(max_length=200)
    license_details = models.CharField(max_length=500, blank=True)
    program = models.TextField()
    disciplines = models.ManyToManyField("catalogs.Discipline")
    coaches = models.ManyToManyField(settings.AUTH_USER_MODEL, limit_choices_to={"role_assignments__role": "coach"})
    contact_url = models.URLField(blank=True)
    public = models.BooleanField(default=False)

    class Meta:
        permissions = [("view_ministry_dashboard", "Read ministry reports, calendar and published teams")]


class TrainingStage(models.TextChoices):
    INITIAL = "initial", "Начальная подготовка"
    TRAINING = "training", "Учебно-тренировочный этап"
    MASTERY = "mastery", "Совершенствование спортивного мастерства"
    HIGHEST = "highest", "Высшее спортивное мастерство"


class TrainingGroup(models.Model):
    organization = models.ForeignKey(TrainingOrganization, on_delete=models.PROTECT)
    discipline = models.ForeignKey("catalogs.Discipline", on_delete=models.PROTECT)
    coach = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    stage = models.CharField(max_length=16, choices=TrainingStage.choices)
    name = models.CharField(max_length=200)


class TrainingMembership(models.Model):
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    group = models.ForeignKey(TrainingGroup, on_delete=models.PROTECT, related_name="memberships")
    discipline = models.ForeignKey("catalogs.Discipline", on_delete=models.PROTECT)
    starts_on = models.DateField()
    ends_on = models.DateField(null=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_training_memberships")

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(ends_on__isnull=True) | models.Q(ends_on__gte=models.F("starts_on")), name="extension_membership_dates"), models.UniqueConstraint(fields=["athlete", "discipline"], condition=models.Q(ends_on__isnull=True), name="extension_active_training_discipline")]


class TrainingSession(models.Model):
    group = models.ForeignKey(TrainingGroup, on_delete=models.PROTECT, related_name="sessions")
    coach = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    date = models.DateField()
    format = models.CharField(max_length=16, choices=[("in_person", "Очно"), ("online", "Онлайн")])
    evidence_url = models.URLField(blank=True)
    platform_log = models.TextField(blank=True)


class Attendance(models.Model):
    session = models.ForeignKey(TrainingSession, on_delete=models.PROTECT, related_name="attendance")
    membership = models.ForeignKey(TrainingMembership, on_delete=models.PROTECT)
    present = models.BooleanField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["session", "membership"], name="extension_attendance_once")]


class AssessmentNorm(models.Model):
    key = models.SlugField(max_length=80)
    name = models.CharField(max_length=200)
    version = models.PositiveIntegerField()
    discipline = models.ForeignKey("catalogs.Discipline", on_delete=models.PROTECT)
    stage = models.CharField(max_length=16, choices=TrainingStage.choices)
    sex = models.CharField(max_length=8, choices=[("all", "Без различия"), ("female", "Женский"), ("male", "Мужской")], default="all")
    unit = models.CharField(max_length=80)
    comparator = models.CharField(max_length=3, choices=[("min", "Не менее"), ("max", "Не более")])
    threshold = models.DecimalField(max_digits=12, decimal_places=3)
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)
    source_url = models.URLField(blank=True)
    source_version = models.CharField(max_length=200, default="fictional-demo")
    verified_on = models.DateField(null=True, blank=True)
    source_verified = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["key", "version", "discipline", "stage", "sex"], name="extension_norm_version")]


class AssessmentAttempt(models.Model):
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    norm = models.ForeignKey(AssessmentNorm, on_delete=models.PROTECT)
    measured_on = models.DateField()
    value = models.DecimalField(max_digits=12, decimal_places=3)
    evidence = models.URLField(blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_attempts")
    outcome = models.JSONField()
    created_at = models.DateTimeField(default=timezone.now)


class Attestation(models.Model):
    membership = models.ForeignKey(TrainingMembership, on_delete=models.PROTECT)
    assessed_on = models.DateField()
    sex = models.CharField(max_length=8, default="all")
    snapshot = models.JSONField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="approved_attestations")
    transfer = models.OneToOneField(TrainingMembership, null=True, on_delete=models.PROTECT, related_name="attestation_transfer")


class ProgressionRule(models.Model):
    discipline = models.ForeignKey("catalogs.Discipline", on_delete=models.PROTECT)
    target_rank = models.CharField(max_length=16, choices=SportRank.choices)
    version = models.PositiveIntegerField()
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)
    levels = models.JSONField()
    maximum_place = models.PositiveSmallIntegerField()
    required_results = models.PositiveSmallIntegerField(default=1)
    source_url = models.URLField(blank=True)
    source_version = models.CharField(max_length=200, default="fictional-demo")
    source_verified = models.BooleanField(default=False)
    verified_on = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["discipline", "target_rank", "version"], name="extension_progression_version")]


class IndicatorEvidence(models.Model):
    year = models.PositiveSmallIntegerField()
    indicator = models.CharField(max_length=20, choices=[("participation", "Численность"), ("organizations", "Организации"), ("events", "Соревнования")])
    title = models.CharField(max_length=250)
    document_url = models.URLField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)


class ReviewPolicy(models.Model):
    competition = models.OneToOneField("competitions.Competition", on_delete=models.PROTECT)
    appeal_deadline = models.DateTimeField(null=True, blank=True)
    source_url = models.URLField()
    rule_note = models.TextField()
    allow_disqualification = models.BooleanField(default=False)
    allow_technical_loss = models.BooleanField(default=False)


class ReviewCase(models.Model):
    kind = models.CharField(max_length=16, choices=[("appeal", "Апелляция"), ("incident", "Нарушение")])
    application = models.ForeignKey("competitions.Application", on_delete=models.PROTECT)
    publication = models.ForeignKey("competitions.ProtocolPublication", null=True, on_delete=models.PROTECT)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    statement = models.TextField()
    status = models.CharField(max_length=20, default="submitted", choices=[("submitted", "Подано"), ("reviewing", "Рассматривается"), ("needs_materials", "Нужны материалы"), ("accepted", "Удовлетворено"), ("rejected", "Отклонено")])
    revision = models.PositiveIntegerField(default=1)
    decision = models.TextField(blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="decided_review_cases")
    correction_publication = models.ForeignKey("competitions.ProtocolPublication", null=True, on_delete=models.PROTECT, related_name="review_corrections")
    created_at = models.DateTimeField(default=timezone.now)


class ReviewEvidence(models.Model):
    case = models.ForeignKey(ReviewCase, on_delete=models.PROTECT, related_name="evidence")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    description = models.CharField(max_length=500)
    url = models.URLField(blank=True)
    content = models.BinaryField(null=True)
    content_type = models.CharField(max_length=50, blank=True)
    sha256 = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(default=timezone.now)


class ReviewHistory(models.Model):
    case = models.ForeignKey(ReviewCase, on_delete=models.PROTECT, related_name="history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=40)
    reason = models.TextField()
    state = models.CharField(max_length=20)
    created_at = models.DateTimeField(default=timezone.now)


class AwardScheme(models.Model):
    year = models.PositiveSmallIntegerField()
    version = models.PositiveIntegerField()
    name = models.CharField(max_length=200)
    aggregation = models.CharField(max_length=20, choices=[("sum", "Сумма результатов"), ("best", "Лучший результат")], default="best")
    source_url = models.URLField(blank=True)
    source_version = models.CharField(max_length=200, default="fictional-demo")
    source_verified = models.BooleanField(default=False)
    verified_on = models.DateField(null=True, blank=True)
    deadline = models.DateField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["year", "version"], name="extension_award_scheme_version")]


class AwardRate(models.Model):
    scheme = models.ForeignKey(AwardScheme, on_delete=models.PROTECT, related_name="rates")
    level = models.CharField(max_length=100)
    place = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["scheme", "level", "place"], name="extension_award_rate_once")]


class AwardPetition(models.Model):
    scheme = models.ForeignKey(AwardScheme, on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=[("prepared", "Подготовлено"), ("sent", "Направлено (демо)"), ("awarded", "Назначено (демо)")], default="prepared")
    snapshot = models.JSONField()
    fingerprint = models.CharField(max_length=64)
    revision = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)


class IntegrationClient(models.Model):
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    token_digest = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=list)
    competitions = models.ManyToManyField("competitions.Competition")
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True)
    webhook_url = models.URLField(blank=True)
    signing_secret_encrypted = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)


class IntegrationIdentity(models.Model):
    client = models.ForeignKey(IntegrationClient, on_delete=models.PROTECT)
    external_id = models.CharField(max_length=200)
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["client", "external_id"], name="extension_external_identity_once")]


class WebhookDelivery(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True)
    client = models.ForeignKey(IntegrationClient, on_delete=models.PROTECT)
    event = models.ForeignKey("competitions.AuditEvent", on_delete=models.PROTECT)
    payload = models.JSONField()
    status = models.CharField(max_length=16, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["client", "event"], name="extension_webhook_event_once")]


class WebhookAttempt(models.Model):
    delivery = models.ForeignKey(WebhookDelivery, on_delete=models.PROTECT, related_name="history")
    attempted_at = models.DateTimeField(default=timezone.now)
    status_code = models.PositiveSmallIntegerField(null=True)
    outcome = models.CharField(max_length=40)


class ResultImport(models.Model):
    client = models.ForeignKey(IntegrationClient, on_delete=models.PROTECT)
    competition = models.ForeignKey("competitions.Competition", on_delete=models.PROTECT)
    idempotency_key = models.CharField(max_length=100)
    digest = models.CharField(max_length=64)
    status = models.CharField(max_length=16, default="staged")
    rows = models.JSONField()
    before = models.JSONField(default=list)
    accepted_digest = models.CharField(max_length=64, blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["client", "idempotency_key"], name="extension_import_idempotency")]


class OIDCClientPolicy(models.Model):
    application = models.OneToOneField("oauth2_provider.Application", on_delete=models.PROTECT)
    scopes = models.JSONField(default=list)
    enabled = models.BooleanField(default=True)


class OIDCSharingConsent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    application = models.ForeignKey("oauth2_provider.Application", on_delete=models.PROTECT)
    scopes = models.JSONField()
    recorded_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True)
