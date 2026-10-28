from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from apps.accounts.models import User, UserRole
from apps.notifications.models import Notification
from apps.notifications.services import dispatch, queue


@skipUnless(connection.vendor == "postgresql", "requires PostgreSQL row locks")
class NotificationConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="fictional-concurrency@example.test", full_name="Вымышленный Тест")
        UserRole.objects.create(user=self.user, role="athlete")

    def race(self, operation):
        barrier = Barrier(2)
        def run(_):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return operation()
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(run, range(2)))

    def test_parallel_workers_send_each_row_once(self):
        for i in range(8):
            queue(f"test:{i}", "test", "Вымышленное событие", [(self.user.pk, "athlete")])
        with patch("apps.notifications.services.send_mail", return_value=1) as sender:
            self.assertEqual(sum(self.race(dispatch)), 8)
            self.assertEqual(sender.call_count, 8)
        self.assertEqual(Notification.objects.filter(status="sent", attempts=1).count(), 8)

    def test_concurrent_producers_deduplicate(self):
        self.race(lambda: queue("same", "test", "Событие", [(self.user.pk, "athlete")]))
        self.assertEqual(Notification.objects.count(), 1)
