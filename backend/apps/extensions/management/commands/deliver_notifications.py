from django.core.management.base import BaseCommand

from apps.extensions.notifications import deliver_notifications


class Command(BaseCommand):
    help = "Отправить ограниченную пачку уведомлений через настроенный EMAIL_BACKEND"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, choices=range(1, 101), default=20)

    def handle(self, *args, **options):
        self.stdout.write(f"Delivered: {deliver_notifications(limit=options['limit'])}")
