from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """Transactional inbox and SMTP outbox; never stores guardian data or decisions."""

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    role = models.CharField(max_length=16)
    event_key = models.CharField(max_length=180)
    kind = models.CharField(max_length=80)
    title = models.CharField(max_length=200)
    body = models.TextField()
    # Recheck coach object scope on reads AND before sending queued messages.
    subject = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="notification_subjects")
    discipline = models.ForeignKey("catalogs.Discipline", null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True)
    status = models.CharField(max_length=16, default="pending", choices=[(x, x) for x in ("pending", "sent", "failed", "cancelled")])
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True)
    error_code = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ("-id",)
        constraints = [models.UniqueConstraint(fields=["event_key", "recipient", "role"], name="unique_notification_recipient_role")]
        indexes = [models.Index(fields=["status", "next_attempt_at"])]


class ReportDeadline(models.Model):
    title = models.CharField(max_length=200)
    due_on = models.DateField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
