from apps.catalogs.models import Organization
from apps.extensions.models import TrainingOrganization

from .optional_helpers import OptionalCase


class NewcomerTests(OptionalCase):
    def test_public_projection_excludes_private_cards_and_identities(self):
        card = TrainingOrganization.objects.create(
            organization=Organization.objects.create(
                code="fictional-school", name="Вымышленная школа"
            ),
            organization_type="school",
            municipality="Демо-город",
            program="Начальные занятия",
            public=False,
        )
        response = self.client.get("/api/v1/newcomer/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["items"]), 6)
        self.assertNotIn(card.organization.name, str(response.data))
        card.public = True
        card.save()
        response = self.client.get("/api/v1/newcomer/")
        self.assertIn(card.organization.name, str(response.data))
        self.assertNotIn(self.athlete.full_name, str(response.data))
        self.assertEqual(self.post("newcomer/").status_code, 405)
