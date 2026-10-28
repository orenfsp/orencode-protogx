from datetime import date, timedelta
from smtplib import SMTPException
from unittest.mock import patch

from django.core import mail
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.competitions.models import AuditEvent, CoachAthleteLink
from apps.notifications.models import Notification, ReportDeadline
from apps.notifications.services import dispatch, queue, schedule_deadlines
from apps.qualifications.services import create_category_application
from tests import test_competitions as competition_tests


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class NotificationTests(TestCase):
    setUp = competition_tests.CompetitionWorkflowTests.setUp
    user = competition_tests.CompetitionWorkflowTests.user
    as_role = competition_tests.CompetitionWorkflowTests.as_role
    competition = competition_tests.CompetitionWorkflowTests.competition
    apply = competition_tests.CompetitionWorkflowTests.apply
    approve = competition_tests.CompetitionWorkflowTests.approve

    def notice(self, **kwargs):
        return Notification.objects.create(recipient=self.athlete, role="athlete", event_key="test", kind="test", title="Новое событие", body="Откройте кабинет", **kwargs)

    def test_workflow_persists_events_and_sends_once(self):
        competition = self.competition()
        application = self.apply(competition, self.athlete)
        self.approve(application.data["id"])
        response = self.client.post(f"/api/v1/competitions/{competition}/protocol-publish/")
        self.assertEqual(response.status_code, 201, response.data)
        kinds = set(Notification.objects.filter(recipient=self.athlete).values_list("kind", flat=True))
        self.assertTrue({"competition.published", "application.submitted", "application.decided", "protocol.published"} <= kinds)
        count = Notification.objects.count()
        self.assertEqual(dispatch(), count)
        self.assertEqual(len(mail.outbox), count)
        self.assertEqual(dispatch(), 0)
        self.assertEqual(Notification.objects.filter(status="sent").count(), count)
        for email in mail.outbox:
            self.assertNotIn(self.athlete.full_name, email.body)
            self.assertEqual(len(email.to), 1)

    def test_read_scope_idor_and_idempotency(self):
        item = self.notice()
        self.as_role(self.second, "athlete")
        self.assertEqual(self.client.get("/api/v1/notifications/").data, [])
        self.assertEqual(self.client.post(f"/api/v1/notifications/{item.pk}/read/").status_code, 404)
        self.as_role(self.athlete, "athlete")
        first = self.client.post(f"/api/v1/notifications/{item.pk}/read/")
        second = self.client.post(f"/api/v1/notifications/{item.pk}/read/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["read_at"], second.data["read_at"])

    def test_assigned_but_inactive_role_cannot_read(self):
        item = self.notice()
        UserRole.objects.create(user=self.athlete, role="judge")
        self.as_role(self.athlete, "judge")
        self.assertEqual(self.client.get("/api/v1/notifications/").data, [])
        self.assertEqual(self.client.post(f"/api/v1/notifications/{item.pk}/read/").status_code, 404)
        UserRole.objects.filter(user=self.athlete, role="judge").delete()
        self.assertEqual(self.client.get("/api/v1/notifications/").status_code, 403)

    def test_revoked_role_and_link_cancel_delivery(self):
        item = self.notice()
        UserRole.objects.filter(user=self.athlete).delete()
        dispatch()
        item.refresh_from_db()
        self.assertEqual(item.status, "cancelled")
        link = CoachAthleteLink.objects.create(coach=self.coach, athlete=self.second, discipline=self.algorithmic, status="confirmed")
        queue("coach-test", "test", "Событие", [(self.coach.pk, "coach")], subject=self.second, discipline=self.algorithmic)
        link.status = "rejected"
        link.save()
        self.as_role(self.coach, "coach")
        self.assertEqual(self.client.get("/api/v1/notifications/").data, [])
        dispatch()
        self.assertEqual(Notification.objects.get(event_key="coach-test").status, "cancelled")
        self.assertEqual(len(mail.outbox), 0)

    def test_retry_exponential_backoff_and_final_failure(self):
        item = self.notice()
        with patch("apps.notifications.services.send_mail", side_effect=SMTPException("private provider details")):
            for attempt in range(1, 6):
                Notification.objects.filter(pk=item.pk).update(next_attempt_at=timezone.now() - timedelta(seconds=1))
                self.assertEqual(dispatch(), 1)
                item.refresh_from_db()
                self.assertEqual(item.attempts, attempt)
                self.assertEqual(item.error_code, "SMTPException")
                self.assertNotIn("private", item.error_code)
                self.assertEqual(item.status, "failed" if attempt == 5 else "pending")
                self.assertEqual(dispatch(), 0)

    def test_retry_success_clears_error(self):
        item = self.notice()
        with patch("apps.notifications.services.send_mail", side_effect=SMTPException):
            dispatch()
        Notification.objects.filter(pk=item.pk).update(next_attempt_at=timezone.now() - timedelta(seconds=1))
        dispatch()
        item.refresh_from_db()
        self.assertEqual((item.status, item.attempts, item.error_code), ("sent", 2, ""))

    def test_domain_and_outbox_rollback_together(self):
        before = Notification.objects.count()
        with self.assertRaises(RuntimeError), transaction.atomic():
            self.competition()
            self.assertGreater(Notification.objects.count(), before)
            raise RuntimeError("rollback")
        self.assertEqual(Notification.objects.count(), before)
        self.assertFalse(AuditEvent.objects.filter(action="competition.published").exists())

    def test_category_submitted_notifies_judge_and_federation(self):
        create_category_application(self.judge, {"requested_category": "third", "request_type": "assign"})
        self.assertEqual(set(Notification.objects.values_list("recipient_id", "role")), {(self.judge.pk, "judge"), (self.federation.pk, "federation")})

    def test_scheduler_replay_report_and_february_deadline(self):
        today = date(2027, 1, 15)
        ReportDeadline.objects.create(title="Демо отчёт", due_on=today + timedelta(days=5), created_by=self.federation)
        schedule_deadlines(today)
        count = Notification.objects.count()
        schedule_deadlines(today)
        self.assertEqual(Notification.objects.count(), count)
        self.assertEqual(set(Notification.objects.values_list("kind", flat=True)), {"deadline.premium", "deadline.report"})
        self.assertFalse(Notification.objects.exclude(role="federation").exists())

    def test_registration_reminder_and_report_permissions(self):
        self.competition()
        schedule_deadlines()
        self.assertTrue(Notification.objects.filter(kind="deadline.registration", recipient=self.athlete).exists())
        self.as_role(self.athlete, "athlete")
        self.assertEqual(self.client.get("/api/v1/report-deadlines/").status_code, 403)
        self.as_role(self.federation, "federation")
        response = self.client.post("/api/v1/report-deadlines/", {"title": "Отчёт", "due_on": "2027-02-01"})
        self.assertEqual(response.status_code, 201)
