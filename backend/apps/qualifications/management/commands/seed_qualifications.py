"""Демонстрационные правила подсказки по разрядам (AC-09). Не нормативные данные.

Пороги условные и помечены source_verified=False: до сверки с первоисточником ЕВСК
они дают лишь предварительную подсказку федерации. Повторный запуск ничего не дублирует.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalogs.models import Discipline
from apps.qualifications.models import QualificationRule

DEMO_THRESHOLDS = (
    ("Региональное", 3, "adult_3"),
    ("Межрегиональное", 3, "adult_2"),
    ("Всероссийское", 3, "adult_1"),
)
NOTE = "Демо-порог для проверки механики. Не сверено с ЕВСК и не является нормативным требованием."


class Command(BaseCommand):
    help = "Seed unverified demo qualification rules for every active discipline (DJANGO_DEBUG=1 only)"

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_qualifications is available only with DJANGO_DEBUG=1")
        created = 0
        with transaction.atomic():
            for discipline in Discipline.objects.filter(is_active=True):
                for level, max_place, rank in DEMO_THRESHOLDS:
                    _, was_created = QualificationRule.objects.get_or_create(
                        discipline=discipline, rank=rank, competition_level=level, rule_version="demo-1",
                        defaults={"max_place": max_place, "source_verified": False, "source_note": NOTE},
                    )
                    created += was_created
        self.stdout.write(self.style.SUCCESS(f"Demo qualification rules created: {created}"))
