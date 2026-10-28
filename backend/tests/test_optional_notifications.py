from django.core import mail
from django.test import override_settings

from apps.extensions.models import Notification
from apps.extensions.notifications import deliver_notifications, notify

from .optional_helpers import OptionalCase


class NotificationsTests(OptionalCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_outbox_is_private_idempotent_and_delivers_email(self):
        self.assertTrue(Notification.objects.filter(recipient=self.athlete).exists())
        notify(self.athlete, "test-once", "Приватное уведомление")
        notify(self.athlete, "test-once", "Не дублировать")
        self.assertEqual(Notification.objects.filter(event_key="test-once").count(), 1)
        self.assertGreater(deliver_notifications(), 0)
        self.assertGreater(len(mail.outbox), 0)
        self.assertEqual(deliver_notifications(), 0)
        self.login(self.other, "athlete")
        self.assertEqual(self.client.get("/api/v1/notifications/").data, [])
