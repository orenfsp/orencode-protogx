import hashlib
import hmac
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from cryptography.fernet import Fernet
from django.test import override_settings
from django.utils import timezone

from apps.competitions.services import audit
from apps.extensions.integrations import deliver_webhooks
from apps.extensions.models import IntegrationClient, WebhookDelivery

from .optional_helpers import OptionalCase


class LiveWebhookTests(OptionalCase):
    def test_actual_http_signed_consumer_receives_duplicate_id_once(self):
        secret = "fictional-test-signing-secret"
        receipts = set()

        class Receiver(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                stamp = self.headers["X-FSP-Timestamp"]
                delivery = self.headers["X-FSP-Delivery"]
                expected = (
                    "sha256="
                    + hmac.new(
                        secret.encode(),
                        stamp.encode() + b"." + delivery.encode() + b"." + body,
                        hashlib.sha256,
                    ).hexdigest()
                )
                valid = abs(
                    timezone.now().timestamp() - int(stamp)
                ) < 300 and hmac.compare_digest(
                    self.headers["X-FSP-Signature"], expected
                )
                if valid:
                    receipts.add(delivery)
                self.send_response(204 if valid else 401)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Receiver)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        key = Fernet.generate_key()
        try:
            with override_settings(
                DEBUG=True,
                FSP_WEBHOOK_HOSTS=["127.0.0.1"],
                FSP_WEBHOOK_ALLOW_LOOPBACK=True,
                INTEGRATION_ENCRYPTION_KEY=key.decode(),
            ):
                client = IntegrationClient.objects.create(
                    name="Fictional local consumer",
                    owner=self.federation,
                    token_digest="f" * 64,
                    scopes=["webhooks:receive"],
                    expires_at=timezone.now() + timedelta(days=1),
                    webhook_url=f"http://127.0.0.1:{server.server_port}/webhook",
                    signing_secret_encrypted=Fernet(key)
                    .encrypt(secret.encode())
                    .decode(),
                )
                client.competitions.add(self.competition)
                audit(
                    self.federation,
                    "competition.published",
                    self.competition,
                    competition=self.competition,
                )
                self.assertEqual(deliver_webhooks(), 1)
                row = WebhookDelivery.objects.get()
                row.status = "pending"
                row.next_attempt_at = timezone.now()
                row.save()
                self.assertEqual(deliver_webhooks(), 1)
                self.assertEqual(len(receipts), 1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
