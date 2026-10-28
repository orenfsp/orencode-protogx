from django.core.management.base import BaseCommand

from apps.extensions.integrations import deliver_webhooks


class Command(BaseCommand):
    help = "Отправить очередь подписанных вебхуков с ограниченными повторами"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, choices=range(1, 101), default=20)

    def handle(self, *args, **options):
        self.stdout.write(f"Delivered: {deliver_webhooks(limit=options['limit'])}")
