
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.teams.models import RegionalTeam, TeamDecisionHistory, TeamMembership


@override_settings(DATABASE_ENGINE="sqlite", DEBUG=True)
class RegionalTeamApiTests(TestCase):
    def setUp(self):
        call_command("migrate", verbosity=0)
        call_command("seed_demo", verbosity=0)
        self.client = APIClient()
        self.federation = User.objects.get(email="demo.federation@example.test")
        self.client.force_authenticate(self.federation)
        session = self.client.session
        session["active_role"] = "federation"
        session.save()

    def test_federation_can_list_and_add_remove_reorder_and_export(self):
        team = RegionalTeam.objects.get(name="Демо-команда Оренбург 2026")
        response = self.client.get(f"/api/v1/teams/{team.pk}/")
        self.assertEqual(response.status_code, 200)
        junior = User.objects.get(email="demo.junior@example.test")
        # The junior has pending guardian verification and cannot be selected.
        response = self.client.post(f"/api/v1/teams/{team.pk}/members/", {"athlete": junior.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(RegionalTeam.objects.filter(pk=team.pk).exists())
        export = self.client.get(f"/api/v1/teams/{team.pk}/documents/?type=roster&document_format=docx")
        self.assertEqual(export.status_code, 200, export.content)
        self.assertIn("wordprocessingml.document", export["Content-Type"])
        self.assertGreater(len(export.content), 1000)
        pdf = self.client.get(f"/api/v1/teams/{team.pk}/documents/?type=draft-order&document_format=pdf")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")

    def test_non_federation_cannot_mutate(self):
        session = self.client.session
        session["active_role"] = "athlete"
        session.save()
        response = self.client.post("/api/v1/teams/", {"name": "Unauthorized", "season": 1, "discipline": 1, "age_group": 1}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_manual_membership_is_unique_and_audited(self):
        team = RegionalTeam.objects.get(name="Новая команда для отбора")
        athlete = User.objects.get(email="demo.athlete@example.test")
        first = self.client.post(f"/api/v1/teams/{team.pk}/members/", {"athlete": athlete.pk}, format="json")
        self.assertEqual(first.status_code, 201)
        second = self.client.post(f"/api/v1/teams/{team.pk}/members/", {"athlete": athlete.pk}, format="json")
        self.assertEqual(second.status_code, 400)
        membership = TeamMembership.objects.get(team=team, athlete=athlete, removed_at__isnull=True)
        self.assertTrue(TeamDecisionHistory.objects.filter(team=team, action="member_added", membership=membership).exists())
        removed = self.client.post(f"/api/v1/teams/{team.pk}/members/{membership.pk}/remove/", {"reason": "Демонстрационная замена"}, format="json")
        self.assertEqual(removed.status_code, 200)
        self.assertIsNotNone(TeamMembership.objects.get(pk=membership.pk).removed_at)
