"""Create reserved, fictional accounts for local demonstrations only."""

from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Guardian, PersonalDataConsent, User, UserRole

DEMO_PASSWORD = "DemoOnly2026!"
CONSENT_VERSION = "v1-demo-2026-10-27"
DEMO_USERS = (
    ("demo.federation@example.test", "Демо Администратор", date(1990, 1, 1), ("federation", "athlete")),
    ("demo.athlete@example.test", "Демо Спортсмен", date(2000, 2, 2), ("athlete",)),
    ("demo.coach@example.test", "Демо Тренер", date(1985, 3, 3), ("coach",)),
    ("demo.judge@example.test", "Демо Судья", date(1980, 4, 4), ("judge",)),
    ("demo.junior@example.test", "Демо Юниор", date(2012, 5, 5), ("athlete",)),
)


class Command(BaseCommand):
    help = "Seed fictional local demo accounts and roles without resetting existing passwords"

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo is available only with DJANGO_DEBUG=1")

        with transaction.atomic():
            for email, full_name, born, roles in DEMO_USERS:
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={"full_name": full_name, "date_of_birth": born},
                )
                if created:
                    user.set_password(DEMO_PASSWORD)
                    user.save(update_fields=["password"])

                for role in roles:
                    UserRole.objects.get_or_create(user=user, role=role)

                guardian = None
                if email == "demo.junior@example.test":
                    guardian, _ = Guardian.objects.get_or_create(
                        minor=user,
                        full_name="Демо Представитель",
                        relationship="родитель",
                        defaults={"confirmation_status": "pending_verification"},
                    )
                PersonalDataConsent.objects.get_or_create(
                    user=user,
                    text_version=CONSENT_VERSION,
                    confirmation_method="demo_seed",
                    defaults={"guardian": guardian},
                )

        self.stdout.write(self.style.SUCCESS("Seeded 5 fictional demo accounts; existing passwords preserved"))
