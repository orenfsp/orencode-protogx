import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


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
