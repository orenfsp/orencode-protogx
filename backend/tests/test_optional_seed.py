from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.extensions.models import (
    AssessmentAttempt,
    AwardRate,
    OIDCClientPolicy,
    TrainingGroup,
    TrainingMembership,
)


class OptionalSeedTests(TestCase):
    @override_settings(DEBUG=True)
    @patch.dict("os.environ", {"DEMO_ENVIRONMENT": "local", "DEMO_SEED_ENABLED": "1"})
    def test_seed_repeats_without_duplicate_history_or_password_reset(self):
        call_command("seed_optional", stdout=StringIO())
        before = [
            model.objects.count()
            for model in [
                AssessmentAttempt,
                AwardRate,
                OIDCClientPolicy,
                TrainingGroup,
                TrainingMembership,
            ]
        ]
        call_command("seed_optional", stdout=StringIO())
        self.assertEqual(
            before,
            [
                model.objects.count()
                for model in [
                    AssessmentAttempt,
                    AwardRate,
                    OIDCClientPolicy,
                    TrainingGroup,
                    TrainingMembership,
                ]
            ],
        )
