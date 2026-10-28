import hashlib
import hmac
from datetime import timedelta
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.competitions.models import AuditEvent, ProtocolPublication
from apps.competitions.services import audit
from apps.extensions.integrations import deliver_webhooks
from apps.extensions.models import (
    IntegrationClient,
    IntegrationIdentity,
    WebhookDelivery,
)

from .optional_helpers import OptionalCase


class IntegrationTests(OptionalCase):
    def create_client(self, scopes=None, webhook_url=""):
        self.login(self.federation, "federation")
        response = self.post(
            "integrations/",
            {
                "name": "Вымышленная платформа",
                "scopes": scopes or ["events:read", "results:import"],
                "competitions": [self.competition.pk],
                "expires_at": (timezone.now() + timedelta(days=1)).isoformat(),
                "webhook_url": webhook_url,
            },
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.external = APIClient()
        self.external.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["token"])
        return response.data

    def test_scopes_idempotent_staging_review_and_rollback(self):
        created = self.create_client()
        IntegrationIdentity.objects.create(
            client_id=created["id"],
            external_id="fictional-athlete",
            athlete=self.athlete,
        )
        payload = {
            "competition": self.competition.pk,
            "idempotency_key": "demo-1",
            "rows": [
                {
                    "external_athlete_id": "fictional-athlete",
                    "application_id": self.application.pk,
                    "status": "classified",
                    "place": 2,
                    "score": "90.000",
                    "metrics": {"solved_tasks": 2},
                }
            ],
        }
        first = self.external.post("/api/v1/external/results/", payload, format="json")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(
            self.external.post(
                "/api/v1/external/results/", payload, format="json"
            ).data["id"],
            first.data["id"],
        )
        payload["rows"][0]["place"] = 3
        self.assertEqual(
            self.external.post(
                "/api/v1/external/results/", payload, format="json"
            ).status_code,
            409,
        )
        self.assertEqual(ProtocolPublication.objects.count(), 1)
        self.assertEqual(
            self.post(
                f"integrations/imports/{first.data['id']}/decision/",
                {"action": "accept", "reason": "Сопоставление проверено"},
            ).status_code,
            200,
        )
        self.result.refresh_from_db()
        self.assertIsNone(self.result.validated_by_id)
        self.assertEqual(
            self.post(
                f"competitions/{self.competition.pk}/protocol-publish/",
                {"correction_reason": "Нельзя обойти проверку"},
            ).status_code,
            400,
        )
        self.assertEqual(
            self.post(
                f"integrations/imports/{first.data['id']}/decision/",
                {"action": "rollback", "reason": "Отмена до проверки"},
            ).status_code,
            200,
        )
        self.result.refresh_from_db()
        self.assertEqual(self.result.place, 1)
        self.assertEqual(
            self.post(f"integrations/{created['id']}/revoke/").status_code, 200
        )
        self.assertEqual(self.external.get("/api/v1/external/events/").status_code, 401)

    def test_read_token_cannot_import_and_identity_must_match(self):
        self.create_client(["events:read"])
        self.assertEqual(self.external.get("/api/v1/external/events/").status_code, 200)
        self.assertEqual(
            self.external.post(
                "/api/v1/external/results/",
                {
                    "competition": self.competition.pk,
                    "idempotency_key": "x",
                    "rows": [
                        {
                            "external_athlete_id": "missing",
                            "application_id": self.application.pk,
                            "status": "no_show",
                        }
                    ],
                },
                format="json",
            ).status_code,
            403,
        )

    def test_signed_webhooks_retry_and_deduplication(self):
        key = Fernet.generate_key().decode()
        with override_settings(
            INTEGRATION_ENCRYPTION_KEY=key, FSP_WEBHOOK_HOSTS=["consumer.example.test"]
        ):
            created = self.create_client(
                ["webhooks:receive"], "https://consumer.example.test/webhook"
            )
            client = IntegrationClient.objects.get(pk=created["id"])
            self.assertNotIn(created["webhook_secret"], client.signing_secret_encrypted)
            audit(
                self.federation,
                "competition.published",
                self.competition,
                competition=self.competition,
            )
            self.assertEqual(WebhookDelivery.objects.count(), 1)
            captured = []

            def send(url, body, headers):
                message = (
                    headers["X-FSP-Timestamp"].encode()
                    + b"."
                    + headers["X-FSP-Delivery"].encode()
                    + b"."
                    + body
                )
                expected = hmac.new(
                    created["webhook_secret"].encode(), message, hashlib.sha256
                ).hexdigest()
                self.assertEqual(headers["X-FSP-Signature"], "sha256=" + expected)
                self.assertNotIn(self.athlete.email, body.decode())
                captured.append(headers["X-FSP-Delivery"])
                return 503 if len(captured) == 1 else 204

            with patch("apps.extensions.integrations.send_webhook", side_effect=send):
                self.assertEqual(deliver_webhooks(), 0)
                row = WebhookDelivery.objects.get()
                row.next_attempt_at = timezone.now()
                row.save()
                self.assertEqual(deliver_webhooks(), 1)
                self.assertEqual(captured[0], captured[1])
                self.assertEqual(deliver_webhooks(), 0)
            self.assertEqual(WebhookDelivery.objects.get().history.count(), 2)
            self.assertNotIn(
                created["token"], str(list(AuditEvent.objects.values("after")))
            )
