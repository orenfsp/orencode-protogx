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
