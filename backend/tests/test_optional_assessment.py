from datetime import date

from django.utils import timezone

from apps.catalogs.models import Organization
from apps.competitions.models import CoachAthleteLink
from apps.extensions.models import (
    AssessmentNorm,
    TrainingGroup,
    TrainingMembership,
    TrainingOrganization,
)

from .optional_helpers import OptionalCase


class AssessmentTests(OptionalCase):
    def setUp(self):
        super().setUp()
        card = TrainingOrganization.objects.create(organization=Organization.objects.create(code="assessment-test",name="Вымышленная школа"),organization_type="school",municipality="Демо",program="Демо")
        card.coaches.add(self.coach)
        self.group = TrainingGroup.objects.create(organization=card,discipline=self.discipline,coach=self.coach,stage="initial",name="Группа")
        self.next_group = TrainingGroup.objects.create(organization=card,discipline=self.discipline,coach=self.coach,stage="training",name="Следующий этап")
        self.membership = TrainingMembership.objects.create(athlete=self.athlete,group=self.group,discipline=self.discipline,starts_on=date(2024,1,1),recorded_by=self.federation)
        CoachAthleteLink.objects.create(coach=self.coach,athlete=self.athlete,discipline=self.discipline,status="confirmed")
        self.norm = AssessmentNorm.objects.create(key="typing",name="Печать (демо)",version=1,discipline=self.discipline,stage="initial",unit="знаков/мин",comparator="min",threshold=100,effective_from=date(2024,1,1))

    def test_latest_measurement_explanation_and_approved_transfer(self):
        self.login(self.coach,"coach")
        today = timezone.localdate().isoformat()
        attempt = self.post("assessment/attempts/",{"athlete":self.athlete.pk,"norm":self.norm.pk,"measured_on":today,"value":"110"})
        self.assertEqual(attempt.status_code,201,attempt.data)
        self.assertTrue(attempt.data["outcome"]["passed"])
        self.assertIn("100",attempt.data["outcome"]["explanation"])
        attestation = self.post("assessment/attestations/",{"membership":self.membership.pk,"assessed_on":today})
        self.assertTrue(attestation.data["eligible"])
        self.assertTrue(attestation.data["demonstration"])
        approved = self.post(f"assessment/attestations/{attestation.data['id']}/approve/",{"group":self.next_group.pk})
        self.assertEqual(approved.status_code,200,approved.data)
        self.assertEqual(TrainingMembership.objects.count(),2)
        self.assertEqual(self.post(f"assessment/attestations/{attestation.data['id']}/approve/",{"group":self.next_group.pk}).status_code,400)

    def test_missing_failed_and_revoked_link(self):
        self.login(self.coach,"coach")
        today=timezone.localdate().isoformat()
        missing=self.post("assessment/attestations/",{"membership":self.membership.pk,"assessed_on":today})
        self.assertFalse(missing.data["eligible"])
        failed=self.post("assessment/attempts/",{"athlete":self.athlete.pk,"norm":self.norm.pk,"measured_on":today,"value":"99.999"})
        self.assertFalse(failed.data["outcome"]["passed"])
        CoachAthleteLink.objects.all().delete()
        self.assertEqual(self.post("assessment/attempts/",{"athlete":self.athlete.pk,"norm":self.norm.pk,"measured_on":today,"value":"120"}).status_code,403)
        self.assertNotIn(self.athlete.full_name,str(self.client.get("/api/v1/assessment/").data))
        self.login(self.other,"athlete")
        self.assertNotIn(self.athlete.full_name,str(self.client.get("/api/v1/assessment/").data))
