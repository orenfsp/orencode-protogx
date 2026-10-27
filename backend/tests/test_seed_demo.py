from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.accounts.models import Guardian, PersonalDataConsent, User, UserRole


class SeedDemoTests(TestCase):
    @override_settings(DEBUG=True)
    @patch.dict("os.environ", {"DEMO_SEED_ENABLED": "1"}, clear=False)
    def test_seed_is_idempotent_and_keeps_existing_passwords(self):
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(User.objects.filter(email__endswith="@example.test").count(), 5)
        federation = User.objects.get(email="demo.federation@example.test")
        self.assertEqual(set(federation.role_assignments.values_list("role", flat=True)), {"federation", "athlete"})
        self.assertTrue(federation.check_password("DemoOnly2026!"))
        federation.set_password("AnotherLocalPassword2026!")
        federation.save(update_fields=["password"])

        call_command("seed_demo", stdout=StringIO())
        federation.refresh_from_db()
        self.assertTrue(federation.check_password("AnotherLocalPassword2026!"))
        self.assertEqual(User.objects.filter(email__endswith="@example.test").count(), 5)
        self.assertEqual(UserRole.objects.count(), 6)
        self.assertEqual(PersonalDataConsent.objects.filter(confirmation_method="demo_seed").count(), 5)
        self.assertEqual(Guardian.objects.get(minor__email="demo.junior@example.test").confirmation_status, "pending_verification")

        from apps.teams.models import RegionalTeam, TeamDecisionHistory, TeamMembership
        self.assertEqual(RegionalTeam.objects.count(), 3)
        self.assertEqual(TeamMembership.objects.filter(removed_at__isnull=True).count(), 1)
        history_count = TeamDecisionHistory.objects.count()
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(TeamMembership.objects.filter(removed_at__isnull=True).count(), 1)
        self.assertEqual(TeamDecisionHistory.objects.count(), history_count)

    @override_settings(DEBUG=False)
    @patch.dict("os.environ", {"DEMO_SEED_ENABLED": "1"}, clear=False)
    def test_seed_refuses_non_debug_environment(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())
        self.assertFalse(User.objects.filter(email__startswith="demo.").exists())

    @override_settings(DEBUG=True)
    @patch.dict("os.environ", {"DEMO_SEED_ENABLED": "0"}, clear=False)
    def test_seed_requires_explicit_opt_in_when_disabled(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())
