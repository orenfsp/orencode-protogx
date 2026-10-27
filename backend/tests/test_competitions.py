from datetime import date, timedelta
from io import BytesIO

from django.test import TestCase
from django.utils import timezone
from docx import Document
from rest_framework.test import APIClient

from apps.accounts.models import Guardian, PersonalDataConsent, User, UserRole
from apps.catalogs.models import Discipline
from apps.competitions.models import (
    AgeGroup,
    AuditEvent,
    Competition,
    ProtocolPublication,
    ProtocolTemplate,
)


class CompetitionWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.federation = self.user("federation", "federation", date(1980, 1, 1))
        self.athlete = self.user("athlete", "athlete", date(2000, 1, 1))
        self.second = self.user("second", "athlete", date(2001, 1, 1))
        self.coach = self.user("coach", "coach", date(1980, 1, 1))
        self.judge = self.user("judge", "judge", date(1980, 1, 1))
        for athlete in (self.athlete, self.second):
            PersonalDataConsent.objects.create(user=athlete, text_version="test-v1")
        self.group = AgeGroup.objects.get(name="Демо: 18+")
        self.algorithmic = Discipline.objects.get(code="algorithmic")
        self.product = Discipline.objects.get(code="product")
        self.algorithmic_template = ProtocolTemplate.objects.get(discipline=self.algorithmic, version=1)
        self.product_template = ProtocolTemplate.objects.get(discipline=self.product, version=1)

    def user(self, slug, role, born):
        user = User.objects.create_user(email=f"{slug}@example.test", password="SafePassphrase2048!", full_name=f"Тест {slug}", date_of_birth=born)
        UserRole.objects.create(user=user, role=role)
        return user

    def as_role(self, user, role):
        self.client.force_login(user)
        response = self.client.post("/api/v1/auth/active-role/", {"role": role}, format="json")
        self.assertEqual(response.status_code, 200, response.data)

    def competition(self, discipline=None, template=None):
        discipline = discipline or self.algorithmic
        template = template or self.algorithmic_template
        now = timezone.now()
        self.as_role(self.federation, "federation")
        response = self.client.post("/api/v1/competitions/", {
            "title": "Тестовое соревнование", "discipline": discipline.pk, "template": template.pk,
            "age_groups": [self.group.pk], "level": "демо", "competition_type": "турнир",
            "format": "online", "starts_at": (now + timedelta(days=10)).isoformat(),
            "ends_at": (now + timedelta(days=11)).isoformat(),
            "registration_deadline": (now + timedelta(days=5)).isoformat(),
            "age_reference_date": (now + timedelta(days=10)).date().isoformat(),
            "location": "Тестовая площадка", "regulations": "Тестовый регламент",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data["id"]
        self.assertEqual(response.data["state"], "draft")
        response = self.client.post(f"/api/v1/competitions/{pk}/publish/")
        self.assertEqual(response.status_code, 200, response.data)
        return pk

    def apply(self, competition, athlete):
        self.as_role(athlete, "athlete")
        return self.client.post("/api/v1/applications/", {"competition": competition, "athlete": athlete.pk, "age_group": self.group.pk}, format="json")

    def approve(self, application):
        self.as_role(self.federation, "federation")
        response = self.client.post(f"/api/v1/applications/{application}/decision/", {"status": "approved"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)

    def test_full_workflow_versioned_protocol_and_history(self):
        competition = self.competition()
        first = self.apply(competition, self.athlete)
        second = self.apply(competition, self.second)
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)
        self.approve(first.data["id"])
        self.approve(second.data["id"])
        self.as_role(self.federation, "federation")
        assignment = self.client.post("/api/v1/judge-assignments/", {"competition": competition, "judge": self.judge.pk, "role_label": "Судья"}, format="json")
        self.assertEqual(assignment.status_code, 201, assignment.data)
        self.as_role(self.judge, "judge")
        own = self.client.get("/api/v1/judge-assignments/")
        self.assertEqual([row["judge"] for row in own.data], [self.judge.pk])
        entered = self.client.post("/api/v1/results/", {"application": first.data["id"], "status": "classified", "place": 1, "score": "100.000", "metrics": {"solved_tasks": 3}}, format="json")
        self.assertEqual(entered.status_code, 201, entered.data)
        self.as_role(self.federation, "federation")
        self.assertEqual(self.client.post(f"/api/v1/results/{entered.data['id']}/validate/").status_code, 200)
        preview = self.client.get(f"/api/v1/competitions/{competition}/protocol-preview/")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(len(preview.data["rows"]), 2)
        self.assertEqual({row["status"] for row in preview.data["rows"]}, {"classified", "pending_result"})
        self.assertIn("solved_tasks", [column["key"] for column in preview.data["columns"]])
        published = self.client.post(f"/api/v1/competitions/{competition}/protocol-publish/")
        self.assertEqual(published.status_code, 201, published.data)
        self.assertEqual(published.data["version"], 1)
        pdf = self.client.get(f"/api/v1/competitions/{competition}/protocols/1/download/?file_format=pdf")
        self.assertEqual(pdf.status_code, 200, (published.data, pdf.content[:500]))
        self.assertEqual(pdf.content[:4], b"%PDF")
        docx = self.client.get(f"/api/v1/competitions/{competition}/protocols/1/download/?file_format=docx")
        self.assertEqual(docx.status_code, 200)
        document = Document(BytesIO(docx.content))
        document_text = " ".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
        self.assertIn(self.athlete.full_name, document_text)
        self.assertIn(self.second.full_name, document_text)
        self.assertIn("Результат не внесён", document_text)
        immutable = ProtocolPublication.objects.get(pk=published.data["id"]).snapshot
        self.as_role(self.athlete, "athlete")
        history = self.client.get("/api/v1/history/")
        self.assertEqual(len(history.data), 1)
        self.assertEqual(history.data[0]["row"]["place"], 1)
        self.assertNotIn(self.second.full_name, str(history.data))
        self.assertEqual(self.client.get(f"/api/v1/competitions/{competition}/protocols/1/download/?file_format=pdf").status_code, 403)
        self.as_role(self.judge, "judge")
        correction = self.client.post("/api/v1/results/", {"application": first.data["id"], "status": "classified", "place": 2, "score": "90.000", "metrics": {"solved_tasks": 2}}, format="json")
        self.assertEqual(correction.status_code, 200, correction.data)
        self.as_role(self.federation, "federation")
        self.assertEqual(self.client.post(f"/api/v1/results/{entered.data['id']}/validate/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/v1/competitions/{competition}/protocol-publish/").status_code, 400)
        published2 = self.client.post(f"/api/v1/competitions/{competition}/protocol-publish/", {"correction_reason": "Исправлен результат после проверки"}, format="json")
        self.assertEqual(published2.status_code, 201, published2.data)
        self.assertEqual(published2.data["version"], 2)
        self.assertEqual(published2.data["correction_reason"], "Исправлен результат после проверки")
        self.assertEqual(ProtocolPublication.objects.get(pk=published.data["id"]).snapshot, immutable)
        previous = self.client.get(f"/api/v1/competitions/{competition}/protocols/1/download/?file_format=docx")
        self.assertEqual(previous.content, docx.content)
        self.as_role(self.athlete, "athlete")
        self.assertEqual(self.client.get("/api/v1/history/").data[0]["row"]["place"], 2)
        self.assertTrue(AuditEvent.objects.filter(action="protocol.published", competition_id=competition).count() == 2)

    def test_pdf_export_wraps_long_participant_name(self):
        self.athlete.full_name = "А" * 150
        self.athlete.save(update_fields=["full_name"])
        competition = self.competition()
        application = self.apply(competition, self.athlete)
        self.assertEqual(application.status_code, 201, application.data)
        self.approve(application.data["id"])
        self.as_role(self.federation, "federation")
        self.assertEqual(self.client.post(f"/api/v1/competitions/{competition}/protocol-publish/").status_code, 201)
        pdf = self.client.get(f"/api/v1/competitions/{competition}/protocols/1/download/?file_format=pdf")
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_permissions_consent_deadline_and_coach_link(self):
        competition = self.competition()
        self.as_role(self.athlete, "athlete")
        self.assertEqual(self.client.post("/api/v1/competitions/", {}, format="json").status_code, 403)
        first = self.apply(competition, self.athlete)
        self.assertEqual(first.status_code, 201)
        self.as_role(self.federation, "federation")
        self.assertEqual(self.client.patch(f"/api/v1/competitions/{competition}/", {"discipline": self.product.pk}, format="json").status_code, 400)
        self.assertEqual(self.apply(competition, self.athlete).status_code, 400)
        self.as_role(self.coach, "coach")
        forbidden = self.client.post("/api/v1/applications/", {"competition": competition, "athlete": self.second.pk, "age_group": self.group.pk}, format="json")
        self.assertEqual(forbidden.status_code, 403)
        link = self.client.post("/api/v1/coach-links/", {"athlete_email": self.second.email, "discipline": self.algorithmic.pk}, format="json")
        self.assertEqual(link.status_code, 202, link.data)
        self.assertNotIn(self.second.full_name, str(link.data))
        link_id = self.second.coach_links.get(coach=self.coach, discipline=self.algorithmic).pk
        pending = self.client.get("/api/v1/coach-links/")
        self.assertEqual(pending.data[0]["athlete"], None)
        self.assertNotIn(self.second.full_name, str(pending.data))
        self.as_role(self.second, "athlete")
        self.assertEqual(self.client.post(f"/api/v1/coach-links/{link_id}/decision/", {"status": "confirmed"}, format="json").status_code, 200)
        self.as_role(self.coach, "coach")
        allowed = self.client.post("/api/v1/applications/", {"competition": competition, "athlete": self.second.pk, "age_group": self.group.pk}, format="json")
        self.assertEqual(allowed.status_code, 201, allowed.data)
        late = self.competition()
        Competition.objects.filter(pk=late).update(registration_deadline=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.apply(late, self.athlete).status_code, 400)
        minor = self.user("minor", "athlete", date(2012, 1, 1))
        PersonalDataConsent.objects.create(user=minor, text_version="test-v1")
        junior = AgeGroup.objects.get(name="Демо: 12–17 лет")
        Competition.objects.get(pk=competition).age_groups.add(junior)
        self.as_role(minor, "athlete")
        request = {"competition": competition, "athlete": minor.pk, "age_group": junior.pk}
        self.assertEqual(self.client.post("/api/v1/applications/", request, format="json").status_code, 400)
        Guardian.objects.create(minor=minor, full_name="Тест Представитель", relationship="родитель", confirmation_status="verified")
        self.assertEqual(self.client.post("/api/v1/applications/", request, format="json").status_code, 201)

    def test_two_discipline_templates_and_result_metrics(self):
        competition = self.competition(self.product, self.product_template)
        application = self.apply(competition, self.athlete)
        self.assertEqual(application.status_code, 201)
        self.approve(application.data["id"])
        self.as_role(self.federation, "federation")
        wrong = self.client.post("/api/v1/results/", {"application": application.data["id"], "status": "classified", "place": 1, "metrics": {"solved_tasks": 5}}, format="json")
        self.assertEqual(wrong.status_code, 400)
        valid = self.client.post("/api/v1/results/", {"application": application.data["id"], "status": "classified", "place": 1, "metrics": {"project_note": "Тестовое описание"}}, format="json")
        self.assertEqual(valid.status_code, 201, valid.data)
        preview = self.client.get(f"/api/v1/competitions/{competition}/protocol-preview/")
        self.assertIn("project_note", [column["key"] for column in preview.data["columns"]])
        self.assertNotIn("solved_tasks", [column["key"] for column in preview.data["columns"]])
        self.assertEqual(preview.data["sections"], ["header", "participants", "judges", "signatures"])
        self.assertEqual(preview.data["sort"], {"key": "place", "direction": "asc"})
        no_show = self.client.post("/api/v1/results/", {"application": application.data["id"], "status": "no_show", "place": 1, "metrics": {}}, format="json")
        self.assertEqual(no_show.status_code, 400)

    def test_publication_requires_current_consent(self):
        competition = self.competition()
        application = self.apply(competition, self.athlete)
        self.approve(application.data["id"])
        PersonalDataConsent.objects.filter(user=self.athlete).delete()
        response = self.client.post(f"/api/v1/competitions/{competition}/protocol-publish/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ProtocolPublication.objects.filter(competition_id=competition).count(), 0)

    def test_judge_and_protocol_object_scope(self):
        competition = self.competition()
        application = self.apply(competition, self.athlete)
        self.approve(application.data["id"])
        self.as_role(self.judge, "judge")
        self.assertEqual(self.client.get("/api/v1/applications/").data, [])
        forbidden = self.client.post("/api/v1/results/", {"application": application.data["id"], "status": "classified", "place": 1, "metrics": {}}, format="json")
        self.assertEqual(forbidden.status_code, 403)
        self.as_role(self.athlete, "athlete")
        self.assertEqual(self.client.get(f"/api/v1/competitions/{competition}/protocol-preview/").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/competitions/{competition}/protocols/").status_code, 403)

    def test_duplicate_place_requires_configured_tie_rule(self):
        competition = self.competition()
        first = self.apply(competition, self.athlete)
        second = self.apply(competition, self.second)
        self.approve(first.data["id"])
        self.approve(second.data["id"])
        self.as_role(self.federation, "federation")
        payload = {"status": "classified", "place": 1, "metrics": {}}
        self.assertEqual(self.client.post("/api/v1/results/", {"application": first.data["id"], **payload}, format="json").status_code, 201)
        self.assertEqual(self.client.post("/api/v1/results/", {"application": second.data["id"], **payload}, format="json").status_code, 400)
        Competition.objects.filter(pk=competition).update(allow_ties=True)
        self.assertEqual(self.client.post("/api/v1/results/", {"application": second.data["id"], **payload}, format="json").status_code, 201)

    def test_federation_creates_template_version_with_validated_configuration(self):
        self.as_role(self.federation, "federation")
        payload = {
            "discipline": self.product.pk, "name": "Тестовая версия с критерием защиты",
            "metric_fields": [{"key": "defense_note", "label": "Оценка защиты", "type": "string", "required": True}],
            "columns": ["athlete", "status", "defense_note"],
            "sections": ["header", "participants", "judges", "signatures"],
            "signature_roles": ["Главный судья", "Секретарь"],
            "sort": {"key": "athlete", "direction": "asc"},
            "source_url": "https://example.test/protocol-source",
            "source_note": "Тестовый источник требует проверки",
            "competition_type": "Кубок",
            "rule_version": "тест-1",
            "effective_from": timezone.now().date().isoformat(),
        }
        response = self.client.post("/api/v1/templates/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["version"], 2)
        self.assertFalse(response.data["source_verified"])
        bad = {**payload, "columns": ["athlete", "status"]}
        self.assertEqual(self.client.post("/api/v1/templates/", bad, format="json").status_code, 400)
        competition = self.competition(self.product, self.product_template)
        self.assertEqual(self.client.patch(f"/api/v1/competitions/{competition}/", {"template": response.data["id"]}, format="json").status_code, 400)
        matched = self.client.patch(f"/api/v1/competitions/{competition}/", {"template": response.data["id"], "competition_type": "Кубок"}, format="json")
        self.assertEqual(matched.status_code, 200, matched.data)
        future = self.client.post("/api/v1/templates/", {**payload, "name": "Будущая версия", "effective_from": (timezone.now() + timedelta(days=30)).date().isoformat()}, format="json")
        self.assertEqual(future.status_code, 201, future.data)
        self.assertEqual(self.client.patch(f"/api/v1/competitions/{competition}/", {"template": future.data["id"]}, format="json").status_code, 400)

    def test_age_reference_date_controls_eligibility(self):
        athlete = self.user("young", "athlete", date(timezone.now().year - 17, 1, 1))
        PersonalDataConsent.objects.create(user=athlete, text_version="test-v1")
        junior = AgeGroup.objects.get(name="Демо: 12–17 лет")
        competition = self.competition()
        current = Competition.objects.get(pk=competition)
        current.age_groups.add(junior)
        self.as_role(self.federation, "federation")
        response = self.client.patch(f"/api/v1/competitions/{competition}/", {"age_reference_date": date(timezone.now().year, 1, 1).isoformat()}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.as_role(athlete, "athlete")
        request = {"competition": competition, "athlete": athlete.pk, "age_group": self.group.pk}
        self.assertEqual(self.client.post("/api/v1/applications/", request, format="json").status_code, 400)
        Guardian.objects.create(minor=athlete, full_name="Тест Представитель", relationship="родитель", confirmation_status="verified")
        request["age_group"] = junior.pk
        self.assertEqual(self.client.post("/api/v1/applications/", request, format="json").status_code, 201)
