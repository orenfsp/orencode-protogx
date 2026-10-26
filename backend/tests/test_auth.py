from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Guardian, PersonalDataConsent, User, UserRole


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_registration_records_consent_and_athlete_role(self):
        response = self.client.post("/api/v1/auth/register/", {"email": "fictional@example.test", "password": "SafePassphrase2048!", "full_name": "Фиктивный Спортсмен", "date_of_birth": "2000-01-01", "consent": True, "consent_version": "v1-demo-2026-10-27"}, format="json")
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="fictional@example.test")
        self.assertTrue(user.role_assignments.filter(role="athlete").exists())
        self.assertEqual(PersonalDataConsent.objects.get(user=user).text_version, "v1-demo-2026-10-27")
        self.assertEqual(response.data["user"]["active_role"], "athlete")

    def test_minor_requires_guardian_and_records_pending_verification(self):
        payload = {"email": "minor@example.test", "password": "SafePassphrase2048!", "full_name": "Фиктивный Юниор", "date_of_birth": date.today().replace(year=date.today().year - 10).isoformat(), "consent": True, "consent_version": "v1-demo-2026-10-27"}
        self.assertEqual(self.client.post("/api/v1/auth/register/", payload, format="json").status_code, 400)
        payload.update(guardian_name="Фиктивный Представитель", guardian_relationship="родитель", guardian_consent=True)
        self.assertEqual(self.client.post("/api/v1/auth/register/", payload, format="json").status_code, 201)
        self.assertEqual(Guardian.objects.get(minor__email="minor@example.test").confirmation_status, "pending_verification")

    def test_role_switch_requires_assignment(self):
        user = User.objects.create_user(email="multi@example.test", password="SafePassphrase2048!", full_name="Фиктивный Мульти")
        UserRole.objects.create(user=user, role="athlete")
        UserRole.objects.create(user=user, role="judge")
        self.client.force_login(user)
        self.assertEqual(self.client.post("/api/v1/auth/active-role/", {"role": "federation"}, format="json").status_code, 403)
        response = self.client.post("/api/v1/auth/active-role/", {"role": "judge"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["active_role"], "judge")

    def test_anonymous_me_is_denied(self):
        self.assertIn(self.client.get("/api/v1/auth/me/").status_code, (401, 403))

    def test_login_and_logout_use_session(self):
        user = User.objects.create_user(email="session@example.test", password="SafePassphrase2048!", full_name="Фиктивный Участник")
        UserRole.objects.create(user=user, role="athlete")
        login = self.client.post("/api/v1/auth/login/", {"email": user.email, "password": "SafePassphrase2048!"}, format="json")
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.get("/api/v1/auth/me/").data["active_role"], "athlete")
        self.assertEqual(self.client.post("/api/v1/auth/logout/").status_code, 204)
        self.assertIn(self.client.get("/api/v1/auth/me/").status_code, (401, 403))

    def test_csrf_required_for_registration(self):
        client = APIClient(enforce_csrf_checks=True)
        payload = {"email": "csrf@example.test", "password": "SafePassphrase2048!", "full_name": "Фиктивный Участник", "date_of_birth": "2000-01-01", "consent": True, "consent_version": "v1-demo-2026-10-27"}
        self.assertEqual(client.post("/api/v1/auth/register/", payload, format="json").status_code, 403)
        token = client.get("/api/v1/auth/csrf/").data["csrfToken"]
        response = client.post("/api/v1/auth/register/", payload, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 201)

    def test_birth_date_cannot_be_omitted(self):
        response = self.client.post("/api/v1/auth/register/", {"email": "nodob@example.test", "password": "SafePassphrase2048!", "full_name": "Фиктивный Участник", "consent": True, "consent_version": "v1-demo-2026-10-27"}, format="json")
        self.assertEqual(response.status_code, 400)
