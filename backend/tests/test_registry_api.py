from datetime import date
from io import BytesIO

from django.test import TestCase
from openpyxl import load_workbook
from rest_framework.test import APIClient

from apps.accounts.models import AthleteProfile, User, UserRole
from apps.catalogs.models import Discipline, Organization
from apps.competitions.models import AgeGroup
from apps.registry.models import (
    DisciplinePeriod,
    MunicipalityPeriod,
    OrganizationPeriod,
    ParticipationPeriod,
)


class RegistryApiTests(TestCase):
    def setUp(self):
        self.federation = User.objects.create_user(email="f@example.test", full_name="Federation")
        UserRole.objects.create(user=self.federation, role="federation")
        self.athlete = User.objects.create_user(email="a@example.test", full_name="Fictional Athlete", date_of_birth=date(2000, 1, 1))
        UserRole.objects.create(user=self.athlete, role="athlete")
        self.first = Organization.objects.create(code="first-api", name="Первая")
        self.second = Organization.objects.create(code="second-api", name="Вторая")
        AthleteProfile.objects.create(user=self.athlete, organization=self.second)
        a = Discipline.objects.create(code="api-a", name="Первая дисциплина")
        b = Discipline.objects.create(code="api-b", name="Вторая дисциплина")
        AgeGroup.objects.create(name="Взрослые тест", min_age=18, max_age=40)
        ParticipationPeriod.objects.create(athlete=self.athlete, starts_on=date(2024, 1, 1))
        OrganizationPeriod.objects.create(athlete=self.athlete, organization=self.first, starts_on=date(2024, 1, 1), ends_on=date(2024, 12, 31))
        OrganizationPeriod.objects.create(athlete=self.athlete, organization=self.second, starts_on=date(2025, 1, 1))
        MunicipalityPeriod.objects.create(athlete=self.athlete, municipality="Оренбург", starts_on=date(2024, 1, 1))
        for item in (a, b):
            DisciplinePeriod.objects.create(athlete=self.athlete, discipline=item, starts_on=date(2024, 1, 1))
        self.client = APIClient()
        self.client.force_authenticate(self.federation)
        session = self.client.session
        session["active_role"] = "federation"
        session.save()

    def test_unique_and_historical_breakdowns_and_xlsx(self):
        url = "/api/v1/analytics/participation/?start_year=2024&end_year=2025"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["unique_athletes"] for row in response.data], [1, 1])
        self.assertEqual(len(response.data[0]["breakdowns"]["disciplines"]), 2)
        self.assertEqual(response.data[0]["breakdowns"]["organizations"][0]["name"], "Первая")
        self.assertEqual(response.data[1]["breakdowns"]["organizations"][0]["name"], "Вторая")
        book = load_workbook(BytesIO(self.client.get(url.replace("participation/?", "participation/export/?")).content), data_only=True)
        self.assertEqual(book["Итоги"]["B4"].value, response.data[0]["unique_athletes"])
        self.assertEqual(book["Организации"]["B2"].value, "Первая")
        self.assertEqual(book["Организации"]["B3"].value, "Вторая")
        filtered = self.client.get(url + f"&organization={self.first.pk}")
        self.assertEqual([row["unique_athletes"] for row in filtered.data], [1, 0])

    def test_federation_registry_and_role_denial(self):
        for path in ("athletes", "coaches", "judges", "organizations"):
            self.assertEqual(self.client.get(f"/api/v1/{path}/").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/athletes/?search=Fictional").data["count"], 1)
        self.client.force_authenticate(self.athlete)
        session = self.client.session
        session["active_role"] = "athlete"
        session.save()
        self.assertEqual(self.client.get("/api/v1/athletes/").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/analytics/participation/export/?start_year=2024&end_year=2025").status_code, 403)

    def test_filters_must_overlap_at_the_same_time(self):
        before = Discipline.objects.create(code="before-transfer", name="До перевода")
        DisciplinePeriod.objects.create(athlete=self.athlete, discipline=before, starts_on=date(2024, 1, 1), ends_on=date(2024, 6, 30))
        OrganizationPeriod.objects.filter(athlete=self.athlete, organization=self.first).update(ends_on=date(2024, 6, 30))
        OrganizationPeriod.objects.filter(athlete=self.athlete, organization=self.second).update(starts_on=date(2024, 7, 1))
        result = self.client.get(f"/api/v1/analytics/participation/?start_year=2024&end_year=2025&organization={self.second.pk}&discipline={before.pk}")
        self.assertEqual([row["unique_athletes"] for row in result.data], [0, 0])

    def test_invalid_query_and_organization_code_are_rejected(self):
        self.assertEqual(self.client.get("/api/v1/analytics/participation/?start_year=2025&end_year=2025").status_code, 400)
        response = self.client.patch(f"/api/v1/organizations/{self.first.pk}/", {"code": "changed"}, format="json")
        self.assertEqual(response.status_code, 400)
