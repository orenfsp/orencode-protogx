from django.core.management.base import BaseCommand

from apps.extensions.notifications import deliver_notifications


class Command(BaseCommand):
    help = "Отправить ограниченную пачку уведомлений через настроенный EMAIL_BACKEND"

    def handle(self, *args, **options):
        self.stdout.write(f"Delivered: {deliver_notifications()}")
