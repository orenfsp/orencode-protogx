from datetime import date

from apps.catalogs.models import Organization
from apps.competitions.models import CoachAthleteLink
from apps.extensions.models import (
    TrainingGroup,
    TrainingMembership,
    TrainingOrganization,
)
from apps.extensions.training import training_report

from .optional_helpers import OptionalCase


class TrainingTests(OptionalCase):
    def setUp(self):
        super().setUp()
        self.card = TrainingOrganization.objects.create(organization=Organization.objects.create(code="training-test", name="Вымышленная спортшкола"), organization_type="school", municipality="Демо", program="Демонстрация")
        self.card.coaches.add(self.coach)
        self.card.disciplines.add(self.discipline)
        self.group = TrainingGroup.objects.create(organization=self.card, discipline=self.discipline, coach=self.coach, stage="initial", name="Начальная группа")
        self.next_group = TrainingGroup.objects.create(organization=self.card, discipline=self.discipline, coach=self.coach, stage="training", name="Следующая группа")
        CoachAthleteLink.objects.create(coach=self.coach, athlete=self.athlete, discipline=self.discipline, status="confirmed")

    def test_effective_transfer_attendance_privacy_and_deduplicated_report(self):
        self.login(self.coach, "coach")
        first = self.post("training/enroll/", {"athlete": self.athlete.pk, "group": self.group.pk, "starts_on": "2024-01-01"})
        self.assertEqual(first.status_code, 201, first.data)
        second = self.post("training/enroll/", {"athlete": self.athlete.pk, "group": self.next_group.pk, "starts_on": "2025-06-01"})
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(TrainingMembership.objects.get(pk=first.data["id"]).ends_on, date(2025,5,31))
        self.assertEqual([r["unique_athletes"] for r in training_report(2024,2025)["rows"]], [1,1])
        session = self.post("training/sessions/", {"group": self.group.pk, "date": "2025-05-01", "format": "online", "platform_log": "PRIVATE-LOG"})
        self.assertEqual(session.status_code, 201, session.data)
        self.assertEqual(self.post("training/attendance/", {"session":session.data["id"],"membership":first.data["id"],"present":True}).status_code,201)
        self.assertEqual(self.post("training/attendance/", {"session":session.data["id"],"membership":second.data["id"],"present":True}).status_code,400)
        self.login(self.athlete, "athlete")
        self.assertNotIn("PRIVATE-LOG", str(self.client.get("/api/v1/training/").data))
        self.login(self.other, "athlete")
        self.assertEqual(self.client.get("/api/v1/training/").data["items"], [])

    def test_coach_link_revocation_and_overlapping_transfer(self):
        self.login(self.coach, "coach")
        CoachAthleteLink.objects.all().delete()
        self.assertEqual(self.post("training/enroll/", {"athlete":self.athlete.pk,"group":self.group.pk,"starts_on":"2025-01-01"}).status_code,403)
        self.login(self.federation, "federation")
        self.assertEqual(self.post("training/enroll/", {"athlete":self.athlete.pk,"group":self.group.pk,"starts_on":"2025-01-01"}).status_code,201)
        self.assertEqual(self.post("training/enroll/", {"athlete":self.athlete.pk,"group":self.next_group.pk,"starts_on":"2024-01-01"}).status_code,400)
