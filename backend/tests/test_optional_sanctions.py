from datetime import timedelta

from apps.catalogs.models import Discipline
from apps.competitions.models import Application, Competition, ProtocolTemplate, Result
from apps.competitions.services import publish_protocol
from apps.extensions.models import ReviewCase, ReviewPolicy
from apps.ratings.models import AthleteRating, AthleteRestriction, RatingContribution

from .optional_helpers import OptionalCase


class SanctionTests(OptionalCase):
    def incident_under_review(self):
        self.login(self.judge, "judge")
        report = self.post(
            "reviews/",
            {
                "kind": "incident",
                "application": self.application.pk,
                "statement": "Вымышленный рапорт",
            },
        )
        self.assertEqual(report.status_code, 201, report.data)
        self.login(self.federation, "federation")
        self.assertEqual(
            self.post(
                f"reviews/{report.data['id']}/action/",
                {
                    "action": "start",
                    "expected_revision": 1,
                    "reason": "Рапорт принят к проверке",
                },
            ).status_code,
            200,
        )
        return report.data["id"]

    def test_disqualification_requires_policy_and_rights_and_recalculates_other_discipline(
        self,
    ):
        product = Discipline.objects.get(code="product")
        event = Competition.objects.get(pk=self.competition.pk)
        event.pk = None
        event.title = "Вымышленный второй результат"
        event.discipline = product
        event.template = ProtocolTemplate.objects.get(discipline=product, version=1)
        event.save()
        event.age_groups.add(self.age_group)
        application = Application.objects.create(
            competition=event,
            athlete=self.athlete,
            submitted_by=self.athlete,
            age_group=self.age_group,
            status="approved",
        )
        Result.objects.create(
            application=application,
            status="classified",
            place=1,
            score=100,
            metrics={
                f["key"]: "Демо" if f["type"] == "string" else 1
                for f in event.template.metric_fields
            },
            updated_by=self.federation,
            validated_by=self.federation,
        )
        publish_protocol(event, self.federation)
        self.assertEqual(
            RatingContribution.objects.filter(
                athlete=self.athlete, is_current=True
            ).count(),
            2,
        )
        pk = self.incident_under_review()
        on = self.competition.starts_at.date()
        payload = {
            "action": "accept",
            "expected_revision": 2,
            "reason": "Демонстрационное решение по рапорту",
            "sanction": "disqualification",
            "starts_on": str(on),
            "ends_on": str(on + timedelta(days=2)),
            "appeal_rights": "ДЕМО: порядок пересмотра установлен вымышленным регламентом",
        }
        self.assertEqual(self.post(f"reviews/{pk}/action/", payload).status_code, 400)
        ReviewPolicy.objects.create(
            competition=self.competition,
            source_url="https://example.test/fictional-sanction-policy",
            rule_note="Вымышленный регламент для теста",
            allow_disqualification=True,
        )
        self.assertEqual(
            self.post(
                f"reviews/{pk}/action/", {**payload, "appeal_rights": ""}
            ).status_code,
            400,
        )
        self.assertEqual(AthleteRestriction.objects.count(), 0)
        accepted = self.post(f"reviews/{pk}/action/", payload)
        self.assertEqual(accepted.status_code, 200, accepted.data)
        case = ReviewCase.objects.get(pk=pk)
        self.assertEqual(case.restriction.starts_at, on)
        self.assertEqual(case.appeal_rights, payload["appeal_rights"])
        self.assertEqual(
            case.correction_publication.snapshot["rows"][0]["status"], "disqualified"
        )
        self.assertFalse(
            RatingContribution.objects.filter(
                athlete=self.athlete, is_current=True
            ).exists()
        )
        self.assertFalse(AthleteRating.objects.filter(athlete=self.athlete).exists())
        self.login(self.athlete, "athlete")
        self.assertEqual(
            self.post(
                f"reviews/{pk}/evidence/",
                {
                    "description": "Позднее изменение",
                    "url": "https://example.test/late",
                },
            ).status_code,
            400,
        )

    def test_technical_loss_preserves_core_result_types_and_has_effective_date(self):
        pk = self.incident_under_review()
        ReviewPolicy.objects.create(
            competition=self.competition,
            source_url="https://example.test/fictional-technical-policy",
            rule_note="Вымышленный регламент",
            allow_technical_loss=True,
        )
        response = self.post(
            f"reviews/{pk}/action/",
            {
                "action": "accept",
                "expected_revision": 2,
                "reason": "Техническое поражение по вымышленному регламенту",
                "sanction": "technical_loss",
                "appeal_rights": "ДЕМО: запрос пересмотра в федерацию",
            },
        )
        self.assertEqual(response.status_code, 200, response.data)
        case = ReviewCase.objects.get(pk=pk)
        self.assertEqual(case.sanction, "technical_loss")
        self.assertEqual(case.sanction_effective_on, self.competition.starts_at.date())
        self.assertIsNone(case.restriction_id)
        self.result.refresh_from_db()
        self.assertEqual(self.result.status, "unclassified")
        self.assertIsNone(self.result.place)
        self.assertEqual(self.result.metrics, {})
