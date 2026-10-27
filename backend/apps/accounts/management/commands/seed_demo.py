"""Create reserved, fictional accounts and a small regional-team demo dataset."""

import os
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Guardian, PersonalDataConsent, User, UserRole
from apps.catalogs.models import Discipline
from apps.competitions.models import AgeGroup
from apps.ratings.models import RatingSeason
from apps.teams.models import RegionalTeam
from apps.teams.services import add_member

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
    help = "Seed fictional local demo accounts and regional teams without resetting existing passwords"

    def handle(self, *args, **options):
        enabled = os.environ.get("DEMO_SEED_ENABLED", "1" if settings.DEBUG else "0") == "1"
        if not settings.DEBUG or not enabled:
            raise CommandError("seed_demo requires DJANGO_DEBUG=1 and DEMO_SEED_ENABLED=1")

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

            self._seed_teams()

        self.stdout.write(self.style.SUCCESS("Seeded fictional demo accounts and regional teams; existing passwords preserved"))

    def _seed_teams(self):
        federation = User.objects.get(email="demo.federation@example.test")
        athlete = User.objects.get(email="demo.athlete@example.test")
        season, _ = RatingSeason.objects.get_or_create(year=2026, defaults={"name": "Сезон 2026"})
        age_group, _ = AgeGroup.objects.get_or_create(name="Взрослые", defaults={"min_age": 18, "max_age": 35})
        algorithmic = Discipline.objects.get(code="algorithmic")
        product = Discipline.objects.get(code="product")
        populated, _ = RegionalTeam.objects.get_or_create(
            season=season, discipline=algorithmic, age_group=age_group, name="Демо-команда Оренбург 2026",
            defaults={"created_by": federation, "region": "Оренбургская область"},
        )
        if not populated.memberships.filter(athlete=athlete, removed_at__isnull=True).exists():
            add_member(actor=federation, team=populated, athlete=athlete, note="Ручной демонстрационный выбор федерации")
        RegionalTeam.objects.get_or_create(
            season=season, discipline=product, age_group=age_group, name="Демо-команда Product 2026",
            defaults={"created_by": federation, "region": "Оренбургская область"},
        )
        RegionalTeam.objects.get_or_create(
            season=season, discipline=algorithmic, age_group=age_group, name="Новая команда для отбора",
            defaults={"created_by": federation, "region": "Оренбургская область"},
        )
