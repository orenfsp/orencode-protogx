from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Guardian, PersonalDataConsent, User, UserRole


class DashboardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="roles@example.test", password="SafePassphrase2048!", full_name="Тест Ролей")
        for role in ("federation", "athlete", "coach", "judge"):
            UserRole.objects.create(user=self.user, role=role)
        PersonalDataConsent.objects.create(user=self.user, text_version="v1-demo-2026-10-27")
        self.client.force_login(self.user)

    def test_each_active_role_gets_its_own_data(self):
        expected = {
            "federation": "Спортсменов",
            "athlete": "Согласие",
            "coach": "Роль назначена",
            "judge": "Дисциплин в каталоге",
        }
        for role, metric in expected.items():
            with self.subTest(role=role):
                response = self.client.post("/api/v1/auth/active-role/", {"role": role}, format="json")
                self.assertEqual(response.status_code, 200)
                dashboard = self.client.get("/api/v1/auth/dashboard/")
                self.assertEqual(dashboard.status_code, 200)
                self.assertEqual(dashboard.data["role"], role)
                labels = [item["label"] for item in dashboard.data["metrics"]]
                self.assertIn(metric, labels)
                self.assertEqual(dashboard.data["guardian_status"], None)
                if role == "federation":
                    self.assertNotIn("Согласие", labels)
                else:
                    self.assertNotIn("Спортсменов", labels)

    def test_forged_or_revoked_role_cannot_read_federation_dashboard(self):
        self.client.post("/api/v1/auth/active-role/", {"role": "federation"}, format="json")
        UserRole.objects.filter(user=self.user, role="federation").delete()
        self.assertEqual(self.client.get("/api/v1/auth/dashboard/").status_code, 403)

        session = self.client.session
        session["active_role"] = "federation"
        session.save()
        self.assertEqual(self.client.get("/api/v1/auth/dashboard/?role=athlete").status_code, 403)

        session["active_role"] = "superadmin"
        session.save()
        self.assertEqual(self.client.get("/api/v1/auth/dashboard/").status_code, 403)

    def test_athlete_sees_only_own_guardian_status(self):
        self.user.date_of_birth = date(2012, 5, 5)
        self.user.save(update_fields=["date_of_birth"])
        Guardian.objects.create(minor=self.user, full_name="Тест Представитель", relationship="родитель")
        other = User.objects.create_user(email="other@example.test", password="SafePassphrase2048!", full_name="Другой Тест")
        Guardian.objects.create(minor=other, full_name="Другой Представитель", relationship="родитель", confirmation_status="verified")
        self.client.post("/api/v1/auth/active-role/", {"role": "athlete"}, format="json")
        dashboard = self.client.get("/api/v1/auth/dashboard/")
        self.assertEqual(dashboard.data["guardian_status"], "pending_verification")
        self.assertEqual(set(dashboard.data), {"role", "metrics", "guardian_status"})
        self.assertNotIn("Другой Представитель", str(dashboard.data))

    def test_anonymous_dashboard_is_denied(self):
        self.client.logout()
        self.assertIn(self.client.get("/api/v1/auth/dashboard/").status_code, (401, 403))
