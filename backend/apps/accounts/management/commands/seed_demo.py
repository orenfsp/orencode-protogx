"""Create a coherent, fictional development dataset without resetting existing data."""

import os
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Guardian, PersonalDataConsent, User, UserRole
from apps.catalogs.models import Discipline
from apps.competitions.models import (
    AgeGroup,
    Application,
    CoachAthleteLink,
    Competition,
    JudgeAssignment,
    ProtocolTemplate,
    Result,
)
from apps.competitions.services import audit, publish_protocol, validate_result_data
from apps.ratings.models import AthleteRestriction
from apps.ratings.services import season_for_year
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
    ("demo.athlete2@example.test", "Демо Спортсмен Два", date(1998, 6, 6), ("athlete",)),
    ("demo.athlete3@example.test", "Демо Спортсмен Три", date(1997, 7, 7), ("athlete",)),
    ("demo.junior.verified@example.test", "Демо Юниор Проверенный", date(2010, 8, 8), ("athlete",)),
)


class Command(BaseCommand):
    help = "Seed fictional local demo accounts, competitions, ratings and regional teams"

    def handle(self, *args, **options):
        if not settings.DEBUG or os.environ.get("DEMO_SEED_ENABLED", "0") != "1" or os.environ.get("DEMO_ENVIRONMENT") != "local":
            raise CommandError("seed_demo requires DJANGO_DEBUG=1, DEMO_SEED_ENABLED=1 and DEMO_ENVIRONMENT=local")
        if settings.DATABASES["default"].get("HOST", "") not in ("", "db", "localhost", "127.0.0.1", "::1"):
            raise CommandError("seed_demo refuses non-local database hosts")
        with transaction.atomic():
            users = self._seed_accounts()
            self._seed_competitions(users)
            self._seed_teams(users)
        self.stdout.write(self.style.SUCCESS("Seeded fictional demo accounts, competitions, ratings and regional teams; existing passwords preserved"))

    def _seed_accounts(self):
        users = {}
        for email, full_name, born, roles in DEMO_USERS:
            user, created = User.objects.get_or_create(email=email, defaults={"full_name": full_name, "date_of_birth": born})
            if not created and not PersonalDataConsent.objects.filter(user=user, confirmation_method="demo_seed", text_version=CONSENT_VERSION).exists():
                raise CommandError(f"Reserved demo identity already exists without a demo seed marker: {email}")
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save(update_fields=["password"])
            users[email] = user
            for role in roles:
                UserRole.objects.get_or_create(user=user, role=role)
            guardian = None
            if email in {"demo.junior@example.test", "demo.junior.verified@example.test"}:
                guardian, _ = Guardian.objects.get_or_create(
                    minor=user,
                    full_name="Демо Представитель",
                    relationship="родитель",
                    defaults={"confirmation_status": "verified" if email.endswith("verified@example.test") else "pending_verification"},
                )
            PersonalDataConsent.objects.get_or_create(
                user=user,
                text_version=CONSENT_VERSION,
                confirmation_method="demo_seed",
                defaults={"guardian": guardian},
            )
        return users

    def _seed_competitions(self, users):
        federation = users["demo.federation@example.test"]
        coach = users["demo.coach@example.test"]
        judge = users["demo.judge@example.test"]
        athlete1 = users["demo.athlete@example.test"]
        athlete2 = users["demo.athlete2@example.test"]
        athlete3 = users["demo.athlete3@example.test"]
        adult_group, _ = AgeGroup.objects.get_or_create(name="Взрослые", defaults={"min_age": 18, "max_age": 35})
        junior_group, _ = AgeGroup.objects.get_or_create(name="Юниоры 14-17", defaults={"min_age": 14, "max_age": 17})
        scenarios = (
            ("algorithmic", "Russian Championship", 2026, 4, 10, ((athlete1, 1), (athlete2, 2), (athlete3, 3))),
            ("algorithmic", "Regional", 2026, 5, 10, ((athlete1, 2), (athlete2, 1), (athlete3, 3))),
            ("product", "Interregional / district", 2026, 6, 10, ((athlete2, 1), (athlete3, 2))),
            ("algorithmic", "Regional", 2025, 5, 10, ((athlete3, 1), (athlete1, 2))),
        )
        for discipline_code, level, year, month, day, rows in scenarios:
            discipline = Discipline.objects.get(code=discipline_code)
            template = ProtocolTemplate.objects.filter(discipline=discipline).order_by("-version").first()
            starts_at = timezone.make_aware(datetime(year, month, day, 10, 0))
            competition, created = Competition.objects.get_or_create(
                title=f"Демо {level} · {discipline_code} · {year}",
                defaults={
                    "discipline": discipline,
                    "level": level,
                    "competition_type": "championship",
                    "format": "online",
                    "starts_at": starts_at,
                    "ends_at": starts_at + timedelta(days=1),
                    "registration_deadline": starts_at - timedelta(days=30),
                    "age_reference_date": starts_at.date(),
                    "location": "Оренбург · демо-каталог",
                    "regulations": "Демонстрационный регламент; источник требует проверки.",
                    "template": template,
                    "state": Competition.State.PUBLISHED,
                    "created_by": federation,
                },
            )
            if not created:
                continue
            competition.age_groups.add(adult_group)
            competition.age_groups.add(junior_group)
            JudgeAssignment.objects.get_or_create(
                competition=competition,
                judge=judge,
                defaults={"role_label": "Главный судья", "assigned_by": federation},
            )
            for position, (athlete, place) in enumerate(rows, start=1):
                application, app_created = Application.objects.get_or_create(
                    competition=competition,
                    athlete=athlete,
                    defaults={
                        "age_group": adult_group,
                        "submitted_by": athlete,
                        "status": Application.Status.APPROVED,
                        "decided_by": federation,
                        "decided_at": timezone.now(),
                    },
                )
                if app_created:
                    audit(federation, "application.submitted", application, competition=competition, after={"seed_demo": True, "athlete_id": athlete.pk})
                    audit(federation, "application.decided", application, competition=competition, after={"seed_demo": True, "status": application.status})
                result, result_created = Result.objects.get_or_create(
                    application=application,
                    defaults={
                        "status": Result.Status.CLASSIFIED,
                        "place": place,
                        "score": Decimal(str(100 - position * 7)),
                        "metrics": {},
                        "validated_by": federation,
                        "updated_by": federation,
                    },
                )
                if result_created:
                    validate_result_data(application, result.status, result.place, result.score, result.metrics)
                    audit(federation, "result.validated", result, competition=competition, after={"seed_demo": True, "validated_by": federation.pk})
            rejected, rejected_created = Application.objects.get_or_create(
                competition=competition,
                athlete=users["demo.junior.verified@example.test"],
                defaults={
                    "age_group": junior_group,
                    "submitted_by": users["demo.junior.verified@example.test"],
                    "status": Application.Status.REJECTED,
                    "decision_reason": "Демо: заявка отклонена для отдельной возрастной группы",
                    "decided_by": federation,
                    "decided_at": timezone.now(),
                },
            )
            if rejected_created:
                audit(federation, "application.decided", rejected, competition=competition, after={"seed_demo": True, "status": rejected.status})
            if not competition.protocols.exists():
                publish_protocol(competition, federation)
        AthleteRestriction.objects.get_or_create(
            athlete=athlete3,
            kind=AthleteRestriction.Kind.SUSPENSION,
            starts_at=date(2026, 12, 1),
            ends_at=date(2026, 12, 10),
            defaults={"created_by": federation, "reason_private": "Демо-период ограничения; не действует на весенние протоколы."},
        )
        CoachAthleteLink.objects.get_or_create(
            coach=coach,
            athlete=athlete1,
            discipline=Discipline.objects.get(code="algorithmic"),
            defaults={"status": "confirmed"},
        )
        CoachAthleteLink.objects.get_or_create(
            coach=coach,
            athlete=athlete2,
            discipline=Discipline.objects.get(code="algorithmic"),
            defaults={"status": "confirmed"},
        )

    def _seed_teams(self, users):
        federation = users["demo.federation@example.test"]
        athlete2 = users["demo.athlete2@example.test"]
        athlete3 = users["demo.athlete3@example.test"]
        season = season_for_year(2026)
        age_group = AgeGroup.objects.get(name="Взрослые")
        algorithmic = Discipline.objects.get(code="algorithmic")
        product = Discipline.objects.get(code="product")
        populated, created = RegionalTeam.objects.get_or_create(
            season=season,
            discipline=algorithmic,
            age_group=age_group,
            name="Демо-команда Оренбург 2026",
            defaults={"created_by": federation, "region": "Оренбургская область"},
        )
        if created:
            for athlete in (athlete2, athlete3):
                add_member(actor=federation, team=populated, athlete=athlete, note="Ручной демонстрационный выбор федерации")
        RegionalTeam.objects.get_or_create(
            season=season,
            discipline=product,
            age_group=age_group,
            name="Демо-команда Product 2026",
            defaults={"created_by": federation, "region": "Оренбургская область"},
        )
        season_2025 = season_for_year(2025)
        RegionalTeam.objects.get_or_create(
            season=season_2025,
            discipline=algorithmic,
            age_group=age_group,
            name="Демо-команда Algorithmic 2025",
            defaults={"created_by": federation, "region": "Оренбургская область"},
        )
        RegionalTeam.objects.get_or_create(
            season=season,
            discipline=algorithmic,
            age_group=age_group,
            name="Новая команда для отбора",
            defaults={"created_by": federation, "region": "Оренбургская область"},
        )
