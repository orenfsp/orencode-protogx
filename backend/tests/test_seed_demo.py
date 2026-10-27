from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import Guardian, PersonalDataConsent, User, UserRole
from apps.competitions.models import Application, Competition, ProtocolPublication
from apps.qualifications.models import SportRankHistory
from apps.ratings.models import AthleteRating, RatingContribution


class SeedDemoTests(TestCase):
    @override_settings(DEBUG=True)
    @patch.dict("os.environ", {"DEMO_SEED_ENABLED": "1", "DEMO_ENVIRONMENT": "local"}, clear=False)
    def test_seed_is_idempotent_and_keeps_existing_passwords(self):
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(User.objects.filter(email__endswith="@example.test").count(), 8)
        federation = User.objects.get(email="demo.federation@example.test")
        self.assertEqual(set(federation.role_assignments.values_list("role", flat=True)), {"federation", "athlete"})
        self.assertTrue(federation.check_password("DemoOnly2026!"))
        federation.set_password("AnotherLocalPassword2026!")
        federation.save(update_fields=["password"])

        call_command("seed_demo", stdout=StringIO())
        federation.refresh_from_db()
        self.assertTrue(federation.check_password("AnotherLocalPassword2026!"))
        self.assertEqual(User.objects.filter(email__endswith="@example.test").count(), 8)
        self.assertEqual(UserRole.objects.count(), 9)
        self.assertEqual(PersonalDataConsent.objects.filter(confirmation_method="demo_seed").count(), 8)
        self.assertEqual(Guardian.objects.get(minor__email="demo.junior@example.test").confirmation_status, "pending_verification")
        self.assertEqual(Guardian.objects.get(minor__email="demo.junior.verified@example.test").confirmation_status, "verified")

        from apps.teams.models import RegionalTeam, TeamDecisionHistory, TeamMembership
        self.assertEqual(RegionalTeam.objects.count(), 4)
        self.assertEqual(TeamMembership.objects.filter(removed_at__isnull=True).count(), 3)
        populated = RegionalTeam.objects.get(name="Демо-команда Оренбург 2026")
        self.assertFalse(populated.memberships.filter(athlete__email="demo.athlete@example.test", removed_at__isnull=True).exists())
        self.assertEqual(Competition.objects.filter(title__startswith="Демо ").count(), 4)
        self.assertEqual(ProtocolPublication.objects.filter(competition__title__startswith="Демо ").count(), 4)
        self.assertGreaterEqual(Application.objects.filter(competition__title__startswith="Демо ", status="rejected").count(), 4)
        self.assertGreaterEqual(AthleteRating.objects.count(), 5)
        self.assertGreaterEqual(RatingContribution.objects.filter(is_current=True).count(), 5)
        self.assertTrue(AthleteRating.objects.filter(athlete__email="demo.athlete@example.test", coefficient="1.20").exists())
        self.assertTrue(RatingContribution.objects.filter(athlete__email="demo.athlete@example.test", publication__isnull=False, is_current=True).exists())
        self.assertEqual(SportRankHistory.objects.count(), 2)
        self.assertEqual(Competition.objects.filter(title__startswith="Демо: Приём заявок", registration_deadline__gt=timezone.now()).count(), 1)
        self.assertEqual(Competition.objects.filter(title__startswith="Демо: Приём заявок", registration_deadline__lte=timezone.now()).count(), 1)
        self.assertEqual(RegionalTeam.objects.filter(memberships__removed_at__isnull=True, memberships__athlete__isnull=False).distinct().count(), 2)
        history_count = TeamDecisionHistory.objects.count()
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(TeamMembership.objects.filter(removed_at__isnull=True).count(), 3)
        self.assertEqual(TeamDecisionHistory.objects.count(), history_count)

    @override_settings(DEBUG=True)
    @patch.dict("os.environ", {"DEMO_SEED_ENABLED": "1", "DEMO_ENVIRONMENT": "local"}, clear=False)
    def test_seed_does_not_restore_removed_member(self):
        from apps.teams.models import RegionalTeam
        from apps.teams.services import remove_member

        call_command("seed_demo", stdout=StringIO())
        team = RegionalTeam.objects.get(name="Демо-команда Оренбург 2026")
        member = team.memberships.filter(removed_at__isnull=True).first()
        remove_member(actor=User.objects.get(email="demo.federation@example.test"), membership=member)
        call_command("seed_demo", stdout=StringIO())
        self.assertFalse(team.memberships.filter(athlete_id=member.athlete_id, removed_at__isnull=True).exists())

    @override_settings(DEBUG=False)
    @patch.dict("os.environ", {"DEMO_SEED_ENABLED": "1", "DEMO_ENVIRONMENT": "local"}, clear=False)
    def test_seed_refuses_non_debug_environment(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())
        self.assertFalse(User.objects.filter(email__startswith="demo.").exists())

    @override_settings(DEBUG=True)
    @patch.dict("os.environ", {"DEMO_SEED_ENABLED": "0"}, clear=False)
    def test_seed_requires_explicit_opt_in_when_disabled(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())

    @override_settings(DEBUG=True)
    @patch.dict("os.environ", {"DEMO_SEED_ENABLED": "1", "DEMO_ENVIRONMENT": "staging"}, clear=False)
    def test_seed_refuses_staging_marker(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())
        self.assertFalse(User.objects.filter(email__startswith="demo.").exists())
