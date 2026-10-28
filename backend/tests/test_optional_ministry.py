from django.contrib.auth.models import Permission

from .optional_helpers import OptionalCase


class MinistryTests(OptionalCase):
    def test_existing_user_permission_is_read_only_and_revocable(self):
        self.login(self.other, "athlete")
        self.assertEqual(self.client.get("/api/v1/ministry/").status_code, 403)
        permission = Permission.objects.get(
            content_type__app_label="extensions", codename="view_ministry_dashboard"
        )
        self.other.user_permissions.add(permission)
        session = self.client.session
        session["active_role"] = None  # Login of a permission-only observer.
        session.save()
        response = self.client.get("/api/v1/ministry/")
        self.assertEqual(response.status_code, 200, response.data)
        from apps.competitions.models import AuditEvent
        self.assertEqual(AuditEvent.objects.get(action="ministry.viewed").active_role, "")
        self.assertTrue(response.data["registry_available"])
        self.assertEqual(len([r for r in response.data["items"] if str(r["id"]).startswith("report-")]), 2)
        self.assertNotIn(self.athlete.email, str(response.data))
        self.assertEqual(self.post("ministry/").status_code, 405)
        self.assertEqual(self.post("competitions/", {}).status_code, 403)
        self.other.user_permissions.remove(permission)
        self.assertEqual(self.client.get("/api/v1/ministry/").status_code, 403)
        self.assertEqual(
            self.client.get("/api/v1/ministry/?year=oops").status_code, 403
        )
