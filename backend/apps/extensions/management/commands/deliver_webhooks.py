from django.core.management.base import BaseCommand

from apps.extensions.integrations import deliver_webhooks


class Command(BaseCommand):
    help="Отправить очередь подписанных вебхуков с ограниченными повторами"
    def handle(self,*args,**options):
        self.stdout.write(f"Delivered: {deliver_webhooks()}")
