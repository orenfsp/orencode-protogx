from datetime import date

from apps.competitions.models import CoachAthleteLink
from apps.extensions.models import ProgressionRule

from .optional_helpers import OptionalCase


class ProgressionTests(OptionalCase):
    def test_private_pathway_uses_latest_publication_and_demo_rules(self):
        ProgressionRule.objects.create(
            discipline=self.discipline,
            target_rank="youth_3",
            version=1,
            effective_from=date(2020, 1, 1),
            levels=["regional"],
            maximum_place=3,
            required_results=2,
        )
        self.login(self.athlete, "athlete")
        response = self.client.get("/api/v1/progression/")
        path = next(
            p
            for p in response.data["pathways"]
            if p["discipline"] == self.discipline.pk
        )
        self.assertTrue(path["demonstration"])
        self.assertEqual(path["missing"], 1)
        self.assertEqual(path["evidence"][0]["publication"], self.publication.pk)
        self.assertNotIn(self.other.full_name, str(response.data))
        self.login(self.coach, "coach")
        self.assertEqual(self.client.get("/api/v1/progression/").data["pathways"], [])
        link = CoachAthleteLink.objects.create(
            coach=self.coach,
            athlete=self.athlete,
            discipline=self.discipline,
            status="confirmed",
        )
        self.assertEqual(
            len(self.client.get("/api/v1/progression/").data["pathways"]), 1
        )
        link.delete()
        self.assertEqual(self.client.get("/api/v1/progression/").data["pathways"], [])
