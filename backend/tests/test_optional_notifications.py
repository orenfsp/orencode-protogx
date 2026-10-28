from django.core import mail
from django.test import override_settings

from apps.extensions.models import Notification
from apps.extensions.notifications import deliver_notifications, notify

from .optional_helpers import OptionalCase


class NotificationsTests(OptionalCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_outbox_is_private_idempotent_and_delivers_email(self):
        self.assertFalse(Notification.objects.filter(recipient=self.athlete).exists())
        notify(self.athlete, "test-once", "Приватное уведомление")
        notify(self.athlete, "test-once", "Не дублировать")
        self.assertEqual(Notification.objects.filter(event_key="test-once").count(), 1)
        self.assertGreater(deliver_notifications(), 0)
        self.assertGreater(len(mail.outbox), 0)
        self.assertEqual(deliver_notifications(), 0)
        self.login(self.other, "athlete")
        self.assertEqual(self.client.get("/api/v1/optional-notifications/").data, [])

    def test_mandatory_and_optional_inboxes_have_distinct_routes(self):
        notify(self.athlete, "optional-only", "Optional event")
        self.login(self.athlete, "athlete")
        optional = self.client.get("/api/v1/optional-notifications/")
        mandatory = self.client.get("/api/v1/notifications/")
        self.assertEqual(optional.status_code, 200)
        self.assertEqual(mandatory.status_code, 200)
        self.assertEqual(optional.data[0]["title"], "Optional event")
        self.assertIn("sent_at", optional.data[0])
        self.assertNotIn("body", optional.data[0])
        self.assertTrue(mandatory.data)
        self.assertIn("body", mandatory.data[0])
        self.assertNotIn("Optional event", str(mandatory.data))
