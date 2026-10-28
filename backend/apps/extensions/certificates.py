from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import has_current_consent
from apps.competitions.exporters import STATUS
from apps.competitions.models import Application, ProtocolPublication
from apps.competitions.services import age_on, audit, require_role

from .common import private_response, require_athlete_consent, validated
from .documents import render_document
from .models import ParticipationCertificate


class CertificateInput(serializers.Serializer):
    application = serializers.PrimaryKeyRelatedField(queryset=Application.objects.all())
    public_name = serializers.BooleanField(default=False)


def certificate_status(certificate):
    if (
        certificate.revoked_at
        or not has_current_consent(certificate.athlete)
        or not certificate.athlete.is_active
    ):
        return "revoked"
    try:
        require_athlete_consent(certificate.athlete, timezone.localdate())
    except ValidationError:
        return "revoked"
    if (
        certificate.application.status != "approved"
        or certificate.publication.competition.protocols.first().pk
        != certificate.publication_id
    ):
        return "superseded"
    return "valid"


def certificate_item(certificate):
    return {
        "id": certificate.pk,
        "number": f"ФСП-{certificate.public_id}",
        "competition": certificate.snapshot["competition"],
        "status": certificate_status(certificate),
        "issued_at": certificate.issued_at,
        "download_url": f"/api/v1/certificates/{certificate.pk}/download/",
        "verify_url": f"/verify?code={certificate.public_id}",
    }


class CertificatesView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        require_role(request, "athlete")
        items = ParticipationCertificate.objects.filter(
            athlete=request.user
        ).select_related("athlete", "application", "publication__competition")
        applications = (
            Application.objects.filter(
                athlete=request.user,
                status="approved",
                competition__protocols__isnull=False,
            )
            .select_related("competition")
            .distinct()
        )
        response = Response(
            {
                "items": [certificate_item(c) for c in items],
                "options": {
                    "applications": [
                        {"value": a.pk, "label": a.competition.title}
                        for a in applications
                    ],
                    "certificates": [
                        {"value": c.pk, "label": f"ФСП-{c.public_id}"}
                        for c in items
                        if not c.revoked_at
                    ],
                },
                "notice": "Справка берётся из последней опубликованной версии. Публичная проверка по умолчанию скрывает ФИО. Исправление протокола делает прежнюю справку неактуальной.",
            }
        )
        response["Cache-Control"] = "private, no-store"
        return response

    @extend_schema(request=CertificateInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        require_role(request, "athlete")
        data = validated(CertificateInput, request.data)
        application = get_object_or_404(
            Application,
            pk=data["application"].pk,
            athlete=request.user,
            status="approved",
        )
        # Serialize issuance against the same competition lock used by publication.
        competition = (
            type(application.competition)
            .objects.select_for_update()
            .get(pk=application.competition_id)
        )
        require_athlete_consent(request.user, timezone.localdate())
        if (
            data["public_name"]
            and age_on(request.user.date_of_birth, timezone.localdate()) < 18
        ):
            raise ValidationError(
                "ФИО несовершеннолетнего в публичной проверке не раскрывается; выпустите приватную справку"
            )
        publication = ProtocolPublication.objects.filter(
            competition=competition
        ).first()
        row = (
            next(
                (
                    r
                    for r in publication.snapshot["rows"]
                    if r["application_id"] == application.pk
                ),
                None,
            )
            if publication
            else None
        )
        if not row or row["status"] not in (
            "classified",
            "unclassified",
            "disqualified",
        ):
            raise ValidationError("Нет опубликованного подтверждения участия")
        certificate, created = ParticipationCertificate.objects.get_or_create(
            athlete=request.user,
            application=application,
            publication=publication,
            defaults={
                "public_name": data["public_name"],
                "snapshot": {
                    "athlete": request.user.full_name,
                    "competition": publication.snapshot["competition_title"],
                    "date": competition.starts_at.date().isoformat(),
                    "row": row,
                    "version": publication.version,
                },
            },
        )
        if created:
            audit(
                request.user,
                "certificate.issued",
                certificate,
                competition=competition,
                after={
                    "version": publication.version,
                    "public_name": certificate.public_name,
                },
            )
        return Response(certificate_item(certificate), status=201 if created else 200)


class CertificateDownloadView(APIView):
    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    def get(self, request, pk):
        require_role(request, "athlete")
        certificate = get_object_or_404(
            ParticipationCertificate, pk=pk, athlete=request.user
        )
        if certificate_status(certificate) != "valid":
            raise ValidationError("Справка отозвана или версия протокола заменена")
        snapshot = certificate.snapshot
        content = render_document(
            "Справка об участии",
            [
                f"Номер: ФСП-{certificate.public_id}",
                f"Спортсмен: {snapshot['athlete']}",
                f"Дата: {snapshot['date']}; протокол v{snapshot['version']}",
            ],
            ["Соревнование", "Статус", "Место", "Баллы"],
            [
                [
                    snapshot["competition"],
                    STATUS.get(snapshot["row"]["status"], snapshot["row"]["status"]),
                    snapshot["row"]["place"],
                    snapshot["row"]["score"],
                ]
            ],
            qr_url=f"{settings.FSP_PUBLIC_URL}/verify?code={certificate.public_id}",
        )
        return private_response(
            content, "application/pdf", f"certificate-{certificate.public_id}.pdf"
        )


class CertificateRevokeView(APIView):
    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self, request, pk):
        role = require_role(request, "athlete", "federation")
        queryset = ParticipationCertificate.objects.select_for_update()
        certificate = get_object_or_404(
            queryset if role == "federation" else queryset.filter(athlete=request.user),
            pk=pk,
        )
        if not certificate.revoked_at:
            certificate.revoked_at = timezone.now()
            certificate.save(update_fields=["revoked_at"])
            audit(request.user, "certificate.revoked", certificate)
        return Response({"status": "revoked"})


class VerifyThrottle(AnonRateThrottle):
    rate = "30/min"


class CertificateVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [VerifyThrottle]

    @extend_schema(responses=OpenApiTypes.OBJECT, auth=[])
    def get(self, request, public_id):
        certificate = get_object_or_404(ParticipationCertificate, public_id=public_id)
        status = certificate_status(certificate)
        output = {"status": status, "number": f"ФСП-{certificate.public_id}"}
        if status == "valid":
            output.update(
                competition=certificate.snapshot["competition"],
                date=certificate.snapshot["date"],
                version=certificate.snapshot["version"],
            )
            if certificate.public_name:
                output["athlete"] = certificate.snapshot["athlete"]
        response = Response(output)
        response["Cache-Control"] = "no-store"
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response
