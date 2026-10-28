import time

from django.core.management.base import BaseCommand

from apps.extensions.awards import award_reminders
from apps.extensions.notifications import deliver_notifications
from apps.notifications.services import dispatch, schedule_deadlines


class Command(BaseCommand):
    help = "Поставить напоминания в очередь и отправить email; --loop для постоянного worker."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true")

    def handle(self, *args, **options):
        while True:
            schedule_deadlines()
            award_reminders()
            deliver_notifications()
            self.stdout.write(f"Обработано уведомлений: {dispatch()}")
            if not options["loop"]:
                return
            time.sleep(30)
