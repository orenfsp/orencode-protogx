import hashlib
import hmac
import http.client
import ipaddress
import json
import secrets
import socket
import ssl
from datetime import timedelta
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.competitions.models import Application, Competition, Result
from apps.competitions.serializers import ResultSerializer
from apps.competitions.services import audit, require_role, validate_result_data

from .common import validated
from .models import (
    IntegrationClient,
    IntegrationIdentity,
    ResultImport,
    WebhookAttempt,
    WebhookDelivery,
)

SCOPES = ["events:read", "results:import", "webhooks:receive"]


def canonical(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


class Conflict(APIException):
    status_code = 409
    default_detail = "Ключ идемпотентности или исходные данные конфликтуют"


def client_active(client):
    return (
        not client.revoked_at
        and client.expires_at > timezone.now()
        and client.owner.is_active
        and client.owner.role_assignments.filter(role="federation").exists()
    )


class IntegrationAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise AuthenticationFailed("Необходим integration bearer token")
        raw = header[7:]
        if len(raw) > 200:
            raise AuthenticationFailed("Недействительный токен")
        client = (
            IntegrationClient.objects.filter(
                token_digest=hashlib.sha256(raw.encode()).hexdigest()
            )
            .select_related("owner")
            .first()
        )
        if not client or not client_active(client):
            raise AuthenticationFailed("Токен отозван или истёк")
        return client.owner, client

    def authenticate_header(self, request):
        return "Bearer"


def integration_scope(request, scope, competition=None):
    client = request.auth
    if scope not in client.scopes or (
        competition and not client.competitions.filter(pk=competition.pk).exists()
    ):
        raise PermissionDenied("Scope или доступ к событию отсутствует")
    return client


def encryption():
    key = getattr(settings, "INTEGRATION_ENCRYPTION_KEY", "")
    if not key:
        raise ValidationError(
            "Для вебхуков настройте INTEGRATION_ENCRYPTION_KEY (Fernet)"
        )
    return Fernet(key.encode())


def webhook_destination(url, *, resolve=False):
    parsed = urlsplit(url)
    hosts = getattr(settings, "FSP_WEBHOOK_HOSTS", [])
    demo = settings.DEBUG and getattr(settings, "FSP_WEBHOOK_ALLOW_LOOPBACK", False)
    if (
        parsed.username is not None
        or parsed.password is not None
        or "#" in url
        or parsed.hostname not in hosts
        or (
            parsed.scheme != "https"
            and not (
                demo
                and parsed.scheme == "http"
                and parsed.hostname in ["127.0.0.1", "localhost"]
            )
        )
    ):
        raise ValidationError("Webhook URL должен быть HTTPS на явно разрешённом хосте")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if not resolve:
            return parsed, None, port
        addresses = {
            info[4][0]
            for info in socket.getaddrinfo(
                parsed.hostname, port, type=socket.SOCK_STREAM
            )
        }
    except (ValueError, OSError) as exc:
        raise ValidationError("Некорректный адрес вебхука") from exc
    if not addresses or any(
        not ipaddress.ip_address(ip).is_global
        and not (demo and ipaddress.ip_address(ip).is_loopback)
        for ip in addresses
    ):
        raise ValidationError("Внутренние и специальные адреса запрещены")
    return parsed, sorted(addresses)[0], port


def send_webhook(url, body, headers):
    parsed, address, port = webhook_destination(url, resolve=True)
    if parsed.scheme == "https":
        conn = http.client.HTTPSConnection(
            parsed.hostname, port, timeout=5, context=ssl.create_default_context()
        )
    else:
        conn = http.client.HTTPConnection(parsed.hostname, port, timeout=5)
    # Pin the validated address; TLS still verifies the original hostname/SNI.
    conn._create_connection = lambda *args, **kwargs: socket.create_connection(
        (address, port), timeout=5
    )
    try:
        conn.request(
            "POST",
            parsed.path + ("?" + parsed.query if parsed.query else "") or "/",
            body=body,
            headers=headers,
        )
        response = conn.getresponse()
        response.read(4096)
        return response.status  # No redirects, proxy env or unbounded response reads.
    finally:
        conn.close()


def enqueue_webhooks(event):
    if (
        event.action
        not in ["competition.published", "application.decided", "protocol.published"]
        or not event.competition_id
    ):
        return
    if (
        event.action == "application.decided"
        and event.after.get("status") != "approved"
    ):
        return
    for client in IntegrationClient.objects.filter(
        competitions__pk=event.competition_id,
        revoked_at=None,
        expires_at__gt=timezone.now(),
    ).distinct():
        if (
            client.webhook_url
            and "webhooks:receive" in client.scopes
            and client_active(client)
        ):
            WebhookDelivery.objects.get_or_create(
                client=client,
                event=event,
                defaults={
                    "payload": {
                        "event": event.action,
                        "event_id": event.pk,
                        "competition_id": event.competition_id,
                        "resource_type": event.target_type,
                        "resource_id": event.target_id,
                    }
                },
            )


def deliver_webhooks(limit=100):
    sent = 0
    for pk in (
        WebhookDelivery.objects.filter(
            status="pending", next_attempt_at__lte=timezone.now()
        )
        .order_by("pk")
        .values_list("pk", flat=True)[:limit]
    ):
        with transaction.atomic():
            row = (
                WebhookDelivery.objects.select_for_update()
                .select_related("client__owner")
                .get(pk=pk)
            )
            if row.status != "pending":
                continue
            row.attempts += 1
            code = None
            outcome = "disabled"
            if client_active(row.client):
                try:
                    secret = encryption().decrypt(
                        row.client.signing_secret_encrypted.encode()
                    )
                    body = canonical(row.payload)
                    stamp = str(int(timezone.now().timestamp()))
                    signature = hmac.new(
                        secret,
                        stamp.encode()
                        + b"."
                        + str(row.public_id).encode()
                        + b"."
                        + body,
                        hashlib.sha256,
                    ).hexdigest()
                    code = send_webhook(
                        row.client.webhook_url,
                        body,
                        {
                            "Content-Type": "application/json",
                            "X-FSP-Delivery": str(row.public_id),
                            "X-FSP-Timestamp": stamp,
                            "X-FSP-Signature": "sha256=" + signature,
                        },
                    )
                    outcome = "delivered" if 200 <= code < 300 else "http_error"
                except Exception:
                    outcome = "delivery_error"
            row.status = (
                "sent"
                if outcome == "delivered"
                else "failed"
                if row.attempts >= 5 or outcome == "disabled"
                else "pending"
            )
            row.next_attempt_at = timezone.now() + timedelta(
                seconds=2**row.attempts * 30
            )
            row.save()
            WebhookAttempt.objects.create(
                delivery=row, status_code=code, outcome=outcome
            )
            sent += int(row.status == "sent")
    return sent


class ClientInput(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    scopes = serializers.ListField(
        child=serializers.ChoiceField(choices=SCOPES), allow_empty=False
    )
    competitions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Competition.objects.all(), allow_empty=False
    )
    expires_at = serializers.DateTimeField()
    webhook_url = serializers.URLField(required=False, allow_blank=True, default="")


class IdentityInput(serializers.ModelSerializer):
    class Meta:
        model = IntegrationIdentity
        fields = ["client", "external_id", "athlete"]


class ExternalResultInput(serializers.Serializer):
    external_athlete_id = serializers.CharField(max_length=200)
    application_id = serializers.IntegerField(min_value=1)
    status = serializers.ChoiceField(choices=Result.Status.values)
    place = serializers.IntegerField(
        min_value=1, max_value=32767, allow_null=True, required=False, default=None
    )
    score = serializers.DecimalField(
        max_digits=12, decimal_places=3, allow_null=True, required=False, default=None
    )
    metrics = serializers.DictField(required=False, default=dict)


class ImportInput(serializers.Serializer):
    competition = serializers.PrimaryKeyRelatedField(queryset=Competition.objects.all())
    idempotency_key = serializers.CharField(max_length=100)
    rows = ExternalResultInput(many=True, allow_empty=False, max_length=500)


def current_results(rows):
    output = []
    for row in rows:
        result = Result.objects.filter(application_id=row["application_id"]).first()
        output.append(
            {
                "application_id": row["application_id"],
                "result": None
                if not result
                else {
                    "status": result.status,
                    "place": result.place,
                    "score": str(result.score) if result.score is not None else None,
                    "metrics": result.metrics,
                    "updated_by_id": result.updated_by_id,
                    "validated_by_id": result.validated_by_id,
                },
            }
        )
    return output


class ExternalEventsView(APIView):
    authentication_classes = [IntegrationAuthentication]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        client = integration_scope(request, "events:read")
        audit(client.owner, "integration.events_read", client)
        return Response(
            {
                "items": [
                    {"id": c.pk, "title": c.title, "state": c.state}
                    for c in client.competitions.exclude(state="draft")
                ]
            }
        )


class ExternalImportView(APIView):
    authentication_classes = [IntegrationAuthentication]

    @extend_schema(request=ImportInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        integration_scope(request, "results:import")
        data = validated(ImportInput, request.data)
        client = integration_scope(request, "results:import", data["competition"])
        if data["competition"].state != "published":
            raise ValidationError(
                "Импорт допускается только для опубликованного соревнования"
            )
        # Serialize idempotency keys for the client and stage a snapshot, never publish.
        IntegrationClient.objects.select_for_update().get(pk=client.pk)
        rows = json.loads(canonical(data["rows"]))
        body_digest = digest({"competition": data["competition"].pk, "rows": rows})
        existing = ResultImport.objects.filter(
            client=client, idempotency_key=data["idempotency_key"]
        ).first()
        if existing:
            if existing.digest != body_digest:
                raise Conflict()
            return Response({"id": existing.pk, "status": existing.status})
        if len({r["application_id"] for r in rows}) != len(rows):
            raise ValidationError("Повтор участника в пакете")
        for row in rows:
            identity = IntegrationIdentity.objects.filter(
                client=client, external_id=row["external_athlete_id"]
            ).first()
            application = Application.objects.filter(
                pk=row["application_id"],
                competition=data["competition"],
                status="approved",
            ).first()
            if (
                not identity
                or not application
                or identity.athlete_id != application.athlete_id
            ):
                raise ValidationError("Не сопоставлен спортсмен или одобренная заявка")
            validate_result_data(
                application, row["status"], row["place"], row["score"], row["metrics"]
            )
        batch = ResultImport.objects.create(
            client=client,
            competition=data["competition"],
            idempotency_key=data["idempotency_key"],
            digest=body_digest,
            rows=rows,
            before=current_results(rows),
        )
        audit(
            client.owner,
            "integration.results_staged",
            batch,
            competition=batch.competition,
            after={"rows": len(rows), "digest": body_digest},
        )
        return Response({"id": batch.pk, "status": batch.status}, status=201)


class ImportDecisionInput(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "reject", "rollback"])
    reason = serializers.CharField(max_length=2000)


class ImportDecisionView(APIView):
    @extend_schema(request=ImportDecisionInput, responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self, request, pk):
        require_role(request, "federation")
        initial = get_object_or_404(ResultImport, pk=pk)
        Competition.objects.select_for_update().get(pk=initial.competition_id)
        batch = ResultImport.objects.select_for_update().get(pk=pk)
        data = validated(ImportDecisionInput, request.data)
        # Core validation locks Result directly (without the competition lock).
        # Lock existing rows before comparing/overwriting the staged snapshot.
        list(
            Result.objects.select_for_update()
            .filter(application_id__in=[row["application_id"] for row in batch.rows])
            .order_by("pk")
        )
        current = current_results(batch.rows)
        if data["action"] == "rollback":
            if (
                batch.status != "accepted"
                or digest(current) != batch.accepted_digest
                or any(r["result"] and r["result"]["validated_by_id"] for r in current)
            ):
                raise Conflict(
                    "Принятые результаты уже изменены или проверены; используйте официальное исправление протокола"
                )
            for before in batch.before:
                if before["result"] is None:
                    Result.objects.filter(
                        application_id=before["application_id"]
                    ).delete()
                else:
                    Result.objects.filter(
                        application_id=before["application_id"]
                    ).update(**before["result"])
            batch.status = "rolled_back"
        elif batch.status != "staged":
            raise ValidationError("Пакет уже рассмотрен")
        elif data["action"] == "reject":
            batch.status = "rejected"
        else:
            if batch.competition.state != "published":
                raise ValidationError("Соревнование не допускает ввод результатов")
            if digest(current) != digest(batch.before):
                raise Conflict("Исходные результаты изменились после загрузки")
            for row in batch.rows:
                application = Application.objects.get(
                    pk=row["application_id"], competition=batch.competition
                )
                serializer = ResultSerializer(
                    data={
                        "application": application.pk,
                        **{k: row[k] for k in ["status", "place", "score", "metrics"]},
                    }
                )
                serializer.is_valid(raise_exception=True)
                clean = serializer.validated_data
                validate_result_data(
                    application,
                    clean["status"],
                    clean.get("place"),
                    clean.get("score"),
                    clean.get("metrics", {}),
                )
                Result.objects.update_or_create(
                    application=application,
                    defaults={
                        "status": clean["status"],
                        "place": clean.get("place"),
                        "score": clean.get("score"),
                        "metrics": clean.get("metrics", {}),
                        "updated_by": request.user,
                        "validated_by": None,
                    },
                )
            batch.status = "accepted"
            batch.accepted_digest = digest(current_results(batch.rows))
        batch.decided_by = request.user
        batch.save()
        audit(
            request.user,
            "integration.import_decided",
            batch,
            competition=batch.competition,
            after={"status": batch.status, "reason": data["reason"]},
        )
        return Response({"id": batch.pk, "status": batch.status})


class IntegrationsView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        require_role(request, "federation")
        clients = IntegrationClient.objects.all()
        return Response(
            {
                "items": [
                    {
                        "id": c.pk,
                        "kind": "Клиент",
                        "name": c.name,
                        "status": "revoked"
                        if c.revoked_at
                        else "active"
                        if client_active(c)
                        else "expired",
                        "details": f"{', '.join(c.scopes)} · до {c.expires_at}",
                    }
                    for c in clients
                ]
                + [
                    {
                        "id": f"import-{b.pk}",
                        "kind": "Импорт",
                        "name": f"Пакет №{b.pk}",
                        "status": b.status,
                        "details": f"Событие {b.competition_id} · {len(b.rows)} результатов",
                    }
                    for b in ResultImport.objects.all()
                ]
                + [
                    {
                        "id": f"webhook-{d.pk}",
                        "kind": "Webhook",
                        "name": str(d.public_id),
                        "status": d.status,
                        "details": f"Попыток: {d.attempts}; исходы: {list(d.history.values_list('outcome', flat=True))}",
                    }
                    for d in WebhookDelivery.objects.all()
                ],
                "notice": "Интеграционные токены имеют scope, срок и список событий. Импорт сначала рассматривается федерацией, затем требует обычной проверки результатов и публикации протокола. Вебхуки доставляются отдельной командой с подписью и дедупликацией.",
                "options": {
                    "competitions": [
                        {"value": c.pk, "label": c.title}
                        for c in Competition.objects.all()
                    ],
                    "clients": [{"value": c.pk, "label": c.name} for c in clients],
                    "imports": [
                        {"value": b.pk, "label": f"Пакет №{b.pk}: {b.status}"}
                        for b in ResultImport.objects.all()
                    ],
                },
            }
        )

    @extend_schema(request=ClientInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation")
        data = validated(ClientInput, request.data)
        if (
            not timezone.now()
            < data["expires_at"]
            <= timezone.now() + timedelta(days=90)
        ):
            raise ValidationError("Срок токена должен быть в пределах 90 дней")
        secret = ""
        encrypted = ""
        if data["webhook_url"]:
            webhook_destination(data["webhook_url"])
            secret = secrets.token_urlsafe(32)
            encrypted = encryption().encrypt(secret.encode()).decode()
        token = secrets.token_urlsafe(32)
        competitions = data.pop("competitions")
        client = IntegrationClient.objects.create(
            **data,
            owner=request.user,
            token_digest=hashlib.sha256(token.encode()).hexdigest(),
            signing_secret_encrypted=encrypted,
        )
        client.competitions.set(competitions)
        audit(
            request.user,
            "integration.client_created",
            client,
            after={"scopes": client.scopes, "events": [c.pk for c in competitions]},
        )
        response = Response(
            {"id": client.pk, "token": token, "webhook_secret": secret}, status=201
        )
        response["Cache-Control"] = "no-store"
        return response


class RevokeIntegrationView(APIView):
    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self, request, pk):
        require_role(request, "federation")
        client = get_object_or_404(IntegrationClient, pk=pk)
        client.revoked_at = timezone.now()
        client.save(update_fields=["revoked_at"])
        audit(request.user, "integration.client_revoked", client)
        return Response({"status": "revoked"})


class IntegrationIdentityView(APIView):
    @extend_schema(request=IdentityInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation")
        serializer = IdentityInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        if (
            not serializer.validated_data["athlete"]
            .role_assignments.filter(role="athlete")
            .exists()
        ):
            raise ValidationError("Требуется существующий спортсмен")
        row = serializer.save()
        audit(request.user, "integration.identity_mapped", row)
        return Response({"id": row.pk}, status=201)
