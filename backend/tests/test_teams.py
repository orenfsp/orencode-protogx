
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
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
        self.assertEqual([member["organization_name"] for member in response.data["members"]], ["Демонстрационная областная школа спортивного программирования и информационных технологий", "Демо клуб Орбита"])
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
        self.assertIn("Демонстрационная областная школа спортивного программирования и информационных технологий", document_xml)
        self.assertIn("Демо клуб Орбита", document_xml)
        self.assertIn("w:tblHeader", document_xml)
        self.assertIn("w:cantSplit", document_xml)
        self.assertFalse(team.decision_history.filter(action="published").exists())
        published = self.client.post(f"/api/v1/teams/{team.pk}/publish/", {}, format="json")
        self.assertEqual(published.status_code, 200)
        self.assertEqual(published.data["status"], "published")
        self.assertTrue(AuditEvent.objects.filter(action="regional_team.document_generated", target_id=team.pk).exists())

    def test_unaffiliated_member_is_rendered_in_both_docx_variants(self):
        from apps.accounts.models import AthleteProfile

        team = RegionalTeam.objects.get(name="Демо-команда Оренбург 2026")
        profile = AthleteProfile.objects.get(user__email="demo.athlete2@example.test")
        profile.organization = None
        profile.save(update_fields=["organization"])
        response = self.client.get(f"/api/v1/teams/{team.pk}/")
        self.assertIsNone(response.data["members"][0]["organization_name"])
        for kind in ("roster", "draft-order"):
            export = self.client.get(f"/api/v1/teams/{team.pk}/documents/?type={kind}&document_format=docx")
            with ZipFile(BytesIO(export.content)) as archive:
                xml = archive.read("word/document.xml").decode("utf-8")
            self.assertIn("Не указана", xml)
            self.assertIn("Демо клуб Орбита", xml)

    def test_long_organization_and_manual_order_in_documents(self):
        team = RegionalTeam.objects.get(name="Демо-команда Оренбург 2026")
        members = list(team.memberships.filter(removed_at__isnull=True).order_by("position"))
        organization = members[0].athlete.athlete_profile.organization
        organization.name = "Областная школа спортивного программирования " * 6
        organization.save(update_fields=["name"])
        response = self.client.post(f"/api/v1/teams/{team.pk}/reorder/", {"member_ids": [members[1].pk, members[0].pk]}, format="json")
        self.assertEqual(response.status_code, 200)
        for kind in ("roster", "draft-order"):
            export = self.client.get(f"/api/v1/teams/{team.pk}/documents/?type={kind}&document_format=docx")
            with ZipFile(BytesIO(export.content)) as archive:
                xml = archive.read("word/document.xml").decode("utf-8")
            self.assertIn(organization.name, xml)
            self.assertLess(xml.index("Демо Спортсмен Три"), xml.index("Демо Спортсмен Два"))
            self.assertEqual(self.client.get(f"/api/v1/teams/{team.pk}/documents/?type={kind}&document_format=pdf").status_code, 200)

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

    def test_team_and_candidate_lists_are_paginated_without_duplicates(self):
        template = RegionalTeam.objects.first()
        RegionalTeam.objects.bulk_create([
            RegionalTeam(name=f"Pagination {index}", season=template.season, discipline=template.discipline, age_group=template.age_group, created_by=self.federation)
            for index in range(51)
        ])
        athletes = User.objects.bulk_create([User(email=f"page-{index}@example.test", full_name=f"Кандидат {index:03}") for index in range(51)])
        UserRole.objects.bulk_create([UserRole(user=athlete, role="athlete") for athlete in athletes])
        for path in ("/api/v1/teams/", f"/api/v1/teams/{template.pk}/candidates/"):
            first = self.client.get(path)
            second = self.client.get(path, {"page": 2})
            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(len(first.data["results"]), 50)
            first_ids = {row["id"] for row in first.data["results"]}
            second_ids = {row["id"] for row in second.data["results"]}
            self.assertFalse(first_ids & second_ids)
            self.assertEqual(len(first_ids | second_ids), first.data["count"])
            self.assertEqual(self.client.get(path, {"page": 999}).status_code, 404)

    def test_invalid_team_filter_returns_validation_error(self):
        for field in ("season", "age_group"):
            response = self.client.get("/api/v1/teams/", {field: "invalid"})
            self.assertEqual(response.status_code, 400)
            self.assertIn(field, response.data)

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

    def test_recalculation_and_new_restriction_do_not_change_manual_roster(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.ratings.models import AthleteRestriction
        from apps.ratings.services import calculate_ratings

        team = RegionalTeam.objects.get(name="Демо-команда Оренбург 2026")
        before = list(team.memberships.filter(removed_at__isnull=True).order_by("position").values_list("athlete_id", flat=True))
        history_count = team.decision_history.count()
        athlete = User.objects.get(pk=before[0])
        today = timezone.localdate()
        AthleteRestriction.objects.create(athlete=athlete, kind="suspension", starts_at=today, ends_at=today + timedelta(days=3), created_by=self.federation, reason_private="Не раскрывать")
        calculate_ratings(season=team.season, discipline=team.discipline, actor=self.federation)
        response = self.client.get(f"/api/v1/teams/{team.pk}/")
        self.assertEqual([member["athlete"] for member in response.data["members"]], before)
        self.assertFalse(response.data["members"][0]["current_eligibility"]["eligible"])
        self.assertNotIn("Не раскрывать", str(response.data))
        self.assertEqual(team.decision_history.count(), history_count)
        self.assertNotIn(User.objects.get(email="demo.athlete@example.test").pk, before)

    def test_candidate_rating_position_and_current_sport_rank(self):
        team = RegionalTeam.objects.get(name="Демо-команда Оренбург 2026")
        response = self.client.get(f"/api/v1/teams/{team.pk}/candidates/")
        candidate = next(row for row in response.data["results"] if row["email"] == "demo.athlete@example.test")
        self.assertEqual(candidate["rating"]["position"], 1)
        self.assertEqual(candidate["sport_rank"], "III спортивный разряд")
        self.assertFalse(candidate["selected"])
