from django.core.management.base import BaseCommand

from apps.extensions.awards import award_reminders


class Command(BaseCommand):
    help = "Создать дедуплицированные напоминания о сроках демонстрационных ходатайств"

    def handle(self, *args, **options):
        self.stdout.write(f"Reminder recipients: {award_reminders()}")
