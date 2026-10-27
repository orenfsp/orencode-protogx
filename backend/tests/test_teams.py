
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.competitions.models import AuditEvent
from apps.teams.models import RegionalTeam, TeamDecisionHistory, TeamMembership


@override_settings(DATABASE_ENGINE="sqlite", DEBUG=True)
class RegionalTeamApiTests(TestCase):
    def setUp(self):
        call_command("migrate", verbosity=0)
        with patch.dict("os.environ", {"DEMO_SEED_ENABLED": "1", "DEMO_ENVIRONMENT": "local"}, clear=False):
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

        with ZipFile(BytesIO(export.content)) as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("Демо-команда Оренбург", document_xml)
        self.assertIn("Демо Спортсмен Два", document_xml)
        self.assertFalse(team.decision_history.filter(action="published").exists())
        published = self.client.post(f"/api/v1/teams/{team.pk}/publish/", {}, format="json")
        self.assertEqual(published.status_code, 200)
        self.assertEqual(published.data["status"], "published")
        self.assertTrue(AuditEvent.objects.filter(action="regional_team.document_generated", target_id=team.pk).exists())

    def test_non_federation_cannot_read_or_download_team_data(self):
        athlete = User.objects.get(email="demo.athlete@example.test")
        self.client.force_authenticate(athlete)
        session = self.client.session
        session["active_role"] = "athlete"
        session.save()
        team = RegionalTeam.objects.first()
        self.assertEqual(self.client.get(f"/api/v1/teams/{team.pk}/").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/teams/{team.pk}/documents/?type=roster&document_format=pdf").status_code, 403)

    def test_empty_team_cannot_be_published(self):
        team = RegionalTeam.objects.get(name="Новая команда для отбора")
        response = self.client.post(f"/api/v1/teams/{team.pk}/publish/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_reorder_and_removed_members_are_not_returned(self):
        team = RegionalTeam.objects.get(name="Демо-команда Оренбург 2026")
        members = list(team.memberships.filter(removed_at__isnull=True).order_by("position"))
        self.assertEqual(self.client.post(f"/api/v1/teams/{team.pk}/publish/", {}, format="json").status_code, 200)
        response = self.client.post(f"/api/v1/teams/{team.pk}/reorder/", {"member_ids": [members[1].pk, members[0].pk]}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        team.refresh_from_db()
        self.assertEqual(team.status, "draft")
        self.assertEqual(list(team.memberships.filter(removed_at__isnull=True).order_by("position").values_list("pk", flat=True)), [members[1].pk, members[0].pk])
        self.client.post(f"/api/v1/teams/{team.pk}/members/{members[0].pk}/remove/", {}, format="json")
        response = self.client.get(f"/api/v1/teams/{team.pk}/")
        self.assertEqual([item["id"] for item in response.data["members"]], [members[1].pk])

    def test_non_federation_cannot_mutate(self):
        session = self.client.session
        session["active_role"] = "athlete"
        session.save()
        response = self.client.post("/api/v1/teams/", {"name": "Unauthorized", "season": 1, "discipline": 1, "age_group": 1}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_coach_and_judge_cannot_access_team_or_documents(self):
        team = RegionalTeam.objects.first()
        for role in ("coach", "judge"):
            user = User.objects.get(email=f"demo.{role}@example.test")
            self.client.force_authenticate(user)
            session = self.client.session
            session["active_role"] = role
            session.save()
            self.assertEqual(self.client.get(f"/api/v1/teams/{team.pk}/").status_code, 403)
            self.assertEqual(self.client.get(f"/api/v1/teams/{team.pk}/documents/?type=roster&document_format=docx").status_code, 403)
            self.assertEqual(self.client.post(f"/api/v1/teams/{team.pk}/publish/", {}, format="json").status_code, 403)

    def test_session_mutation_without_csrf_is_denied(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.federation)
        session = client.session
        session["active_role"] = "federation"
        session.save()
        team = RegionalTeam.objects.first()
        self.assertEqual(client.post(f"/api/v1/teams/{team.pk}/publish/", {}, format="json").status_code, 403)

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
