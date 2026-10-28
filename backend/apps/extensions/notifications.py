from datetime import timedelta

from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import has_current_consent

from .models import Notification


def notify(user, event_key, title):
    return Notification.objects.get_or_create(recipient=user, event_key=event_key, defaults={"title": title})[0]


def deliver_notifications(limit=100):
    """Transactional outbox, bounded retries; SMTP may deliver twice after a crash.

    A generic message avoids sending result/evidence/identifiers outside the platform.
    No raw SMTP exception or address is stored in audit/log output.
    """
    sent = 0
    for pk in Notification.objects.filter(sent_at=None, failed=False, next_attempt_at__lte=timezone.now()).order_by("pk").values_list("pk", flat=True)[:limit]:
        with transaction.atomic():
            row = Notification.objects.select_for_update().get(pk=pk)
            if row.sent_at or row.failed:
                continue
            row.attempts += 1
            if not row.recipient.is_active or not has_current_consent(row.recipient):
                row.failed = True
            else:
                try:
                    send_mail("ФСП: новое уведомление", "В личном кабинете ФСП есть новое уведомление. Войдите на знакомый вам адрес платформы.", None, [row.recipient.email], fail_silently=False)
                    row.sent_at = timezone.now()
                    sent += 1
                except Exception:
                    row.failed = row.attempts >= 5
                    row.next_attempt_at = timezone.now() + timedelta(minutes=2 ** row.attempts)
            row.save()
    return sent


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "created_at", "read_at", "sent_at"]


class NotificationsView(APIView):
    @extend_schema(responses=NotificationSerializer(many=True))
    def get(self, request):
        response = Response(NotificationSerializer(Notification.objects.filter(recipient=request.user).order_by("-pk")[:100], many=True).data)
        response["Cache-Control"] = "private, no-store"
        return response
