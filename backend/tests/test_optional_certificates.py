from apps.competitions.services import publish_protocol
from apps.extensions.models import ParticipationCertificate

from .optional_helpers import OptionalCase


class CertificateTests(OptionalCase):
    def test_issue_verify_privacy_correction_and_object_access(self):
        self.login(self.athlete, "athlete")
        issued = self.post("certificates/", {"application": self.application.pk})
        self.assertEqual(issued.status_code, 201, issued.data)
        self.assertEqual(self.post("certificates/", {"application": self.application.pk}).status_code, 200)
        certificate = ParticipationCertificate.objects.get()
        self.assertEqual(self.client.get(issued.data["download_url"]).content[:4], b"%PDF")
        self.client.logout()
        public = self.client.get(f"/api/v1/certificates/verify/{certificate.public_id}/")
        self.assertEqual(public.data["status"], "valid")
        self.assertNotIn(self.athlete.full_name, str(public.data))
        self.assertNotIn("row", public.data)
        self.login(self.other, "athlete")
        self.assertEqual(self.client.get(issued.data["download_url"]).status_code, 404)
        self.assertEqual(self.post(f"certificates/{certificate.pk}/revoke/").status_code, 404)
        publish_protocol(self.competition, self.federation, "Проверка исправления")
        self.assertEqual(self.client.get(f"/api/v1/certificates/verify/{certificate.public_id}/").data["status"], "superseded")

    def test_revocation_and_role_revocation(self):
        self.login(self.athlete, "athlete")
        issued = self.post("certificates/", {"application": self.application.pk})
        self.assertEqual(self.post(f"certificates/{issued.data['id']}/revoke/").status_code, 200)
        self.assertEqual(self.client.get(issued.data["download_url"]).status_code, 400)
        self.athlete.role_assignments.all().delete()
        self.assertEqual(self.client.get("/api/v1/certificates/").status_code, 403)
