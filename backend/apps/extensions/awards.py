import hashlib
import json
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User, has_current_consent
from apps.competitions.models import ProtocolPublication
from apps.competitions.services import audit, require_role
from apps.ratings.services import active_restriction

from .common import private_response, validated
from .documents import render_document
from .models import AwardPetition, AwardRate, AwardScheme
from .notifications import notify


class AwardRateInput(serializers.ModelSerializer):
    class Meta:
        model = AwardRate
        fields = ["level", "place", "amount"]

    def validate(self, data):
        if data["place"] < 1 or data["amount"] <= 0:
            raise serializers.ValidationError(
                "Место и сумма должны быть положительными"
            )
        return data


class AwardSchemeInput(serializers.ModelSerializer):
    rates = AwardRateInput(many=True, allow_empty=False)

    class Meta:
        model = AwardScheme
        fields = [
            "year",
            "version",
            "name",
            "aggregation",
            "source_url",
            "source_version",
            "deadline",
            "rates",
        ]

    def validate(self, data):
        if (
            not 1900 <= data["year"] <= 2199
            or data["deadline"].year < data["year"]
            or len({(r["level"], r["place"]) for r in data["rates"]})
            != len(data["rates"])
        ):
            raise serializers.ValidationError("Проверьте год, дедлайн и дубли ставок")
        return data


class PrepareInput(serializers.Serializer):
    scheme = serializers.PrimaryKeyRelatedField(queryset=AwardScheme.objects.all())


class PetitionActionInput(serializers.Serializer):
    status = serializers.ChoiceField(choices=["sent", "awarded"])
    expected_revision = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=2000)


def award_candidates(scheme):
    rates = {(r.level, r.place): r.amount for r in scheme.rates.all()}
    latest = {}
    for p in (
        ProtocolPublication.objects.filter(competition__starts_at__year=scheme.year)
        .select_related("competition")
        .order_by("competition_id", "-version")
    ):
        latest.setdefault(p.competition_id, p)
    candidates = {}
    for publication in latest.values():
        for row in publication.snapshot["rows"]:
            amount = rates.get((publication.competition.level, row.get("place")))
            athlete = User.objects.filter(
                pk=row.get("athlete_id"), is_active=True
            ).first()
            if (
                row.get("status") != "classified"
                or not amount
                or not athlete
                or not has_current_consent(athlete)
                or active_restriction(
                    athlete.pk, publication.competition.starts_at.date()
                )
            ):
                continue
            data = candidates.setdefault(
                athlete.pk,
                {
                    "athlete": athlete.pk,
                    "name": athlete.full_name,
                    "results": [],
                    "total": Decimal("0"),
                },
            )
            data["results"].append(
                {
                    "publication": publication.pk,
                    "version": publication.version,
                    "competition": publication.competition.title,
                    "place": row["place"],
                    "amount": str(amount),
                }
            )
            data["total"] = (
                data["total"] + amount
                if scheme.aggregation == "sum"
                else max(data["total"], amount)
            )
    output = [
        {**c, "total": str(c["total"].quantize(Decimal("0.01")))}
        for _, c in sorted(candidates.items())
    ]
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "scheme": scheme.pk,
                "rates": [
                    [level, place, str(amount)]
                    for (level, place), amount in sorted(rates.items())
                ],
                "aggregation": scheme.aggregation,
                "candidates": output,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return output, fingerprint


def award_reminders():
    today = timezone.localdate()
    count = 0
    for scheme in AwardScheme.objects.filter(
        deadline__gte=today, deadline__lte=today + timezone.timedelta(days=30)
    ):
        for user in User.objects.filter(
            is_active=True, role_assignments__role="federation"
        ):
            notify(
                user,
                f"award-deadline:{scheme.pk}:{scheme.deadline}",
                f"Демонстрационный срок ходатайства: {scheme.deadline}",
            )
            count += 1
    return count


class AwardsView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        require_role(request, "federation")
        scheme = AwardScheme.objects.order_by("-year", "-version").first()
        candidates, fingerprint = award_candidates(scheme) if scheme else ([], "")
        petitions = AwardPetition.objects.order_by("-pk")[:100]
        items = [
            {
                "id": f"candidate-{c['athlete']}",
                "kind": "Кандидат (демо)",
                "name": c["name"],
                "amount": c["total"],
                "details": [
                    f"{r['competition']} · место {r['place']} · протокол {r['publication']} v{r['version']} · {r['amount']}"
                    for r in c["results"]
                ],
            }
            for c in candidates
        ]
        items += [
            {
                "id": p.pk,
                "kind": "Ходатайство (демо)",
                "name": f"№{p.pk} · {p.scheme.name}",
                "status": p.status,
                "revision": p.revision,
                "details": f"Срок: {p.scheme.deadline}; ревизия {p.revision}",
                "download_url": f"/api/v1/awards/{p.pk}/download/",
            }
            for p in petitions
        ]
        return Response(
            {
                "items": items,
                "candidates": candidates,
                "fingerprint": fingerprint,
                "notice": "Демонстрационный механизм отбора и расчёта. Актуальная редакция Указа №93-ук не подтверждена; суммы вымышленные и не устанавливают право на премию. Статусы не означают отправку в министерство или реальное назначение. Агрегация явно задана версией справочника.",
                "options": {
                    "schemes": [
                        {"value": s.pk, "label": f"{s.name} · {s.year} v{s.version}"}
                        for s in AwardScheme.objects.all()
                    ],
                    "petitions": [
                        {"value": p.pk, "label": f"№{p.pk} (ревизия {p.revision})"}
                        for p in petitions
                    ],
                },
            }
        )


class AwardSchemeCreateView(APIView):
    @extend_schema(request=AwardSchemeInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation")
        data = validated(AwardSchemeInput, request.data)
        rates = data.pop("rates")
        scheme = AwardScheme.objects.create(**data)
        for rate in rates:
            AwardRate.objects.create(scheme=scheme, **rate)
        audit(request.user, "award.scheme_created", scheme)
        return Response({"id": scheme.pk}, status=201)


class AwardPrepareView(APIView):
    @extend_schema(request=PrepareInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation")
        scheme = validated(PrepareInput, request.data)["scheme"]
        candidates, fingerprint = award_candidates(scheme)
        if not candidates:
            raise ValidationError("Нет кандидатов по выбранному справочнику")
        petition = AwardPetition.objects.create(
            scheme=scheme,
            snapshot={
                "candidates": candidates,
                "demonstration": not scheme.source_verified,
                "source_version": scheme.source_version,
                "source_url": scheme.source_url,
                "aggregation": scheme.aggregation,
            },
            fingerprint=fingerprint,
            created_by=request.user,
        )
        audit(
            request.user,
            "award.prepared",
            petition,
            after={"fingerprint": fingerprint, "candidates": len(candidates)},
        )
        return Response({"id": petition.pk, "status": petition.status}, status=201)


class AwardActionView(APIView):
    @extend_schema(request=PetitionActionInput, responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self, request, pk):
        require_role(request, "federation")
        data = validated(PetitionActionInput, request.data)
        petition = get_object_or_404(AwardPetition.objects.select_for_update(), pk=pk)
        if petition.revision != data["expected_revision"] or (
            petition.status,
            data["status"],
        ) not in [("prepared", "sent"), ("sent", "awarded")]:
            raise ValidationError("Недопустимый переход или устаревшая ревизия")
        _, fingerprint = award_candidates(petition.scheme)
        if fingerprint != petition.fingerprint:
            raise ValidationError(
                "Протоколы, согласия или правила изменились; подготовьте новый пакет"
            )
        previous = petition.status
        petition.status = data["status"]
        petition.revision += 1
        petition.save(update_fields=["status", "revision"])
        audit(
            request.user,
            "award.status_changed",
            petition,
            before={"status": previous},
            after={
                "status": petition.status,
                "reason": data["reason"],
                "demonstration": True,
            },
        )
        return Response(
            {"id": pk, "status": petition.status, "revision": petition.revision}
        )


class AwardDownloadView(APIView):
    @extend_schema(responses=OpenApiTypes.BINARY)
    def get(self, request, pk):
        require_role(request, "federation")
        petition = get_object_or_404(AwardPetition, pk=pk)
        file_format = request.query_params.get("file_format", "docx")
        if file_format not in ["pdf", "docx"]:
            raise ValidationError("Поддерживаются PDF и DOCX")
        rows = [
            [
                c["name"],
                c["total"],
                "; ".join(
                    f"{r['competition']} · место {r['place']} · публикация {r['publication']} v{r['version']}"
                    for r in c["results"]
                ),
            ]
            for c in petition.snapshot["candidates"]
        ]
        content = render_document(
            "Проект ходатайства на премии Губернатора (ДЕМОНСТРАЦИЯ)",
            [
                f"№{pk}; {petition.scheme.year}; справочник v{petition.scheme.version}; срок {petition.scheme.deadline}",
                f"Источник: {petition.snapshot['source_version']} {petition.snapshot['source_url']}",
                "Паспорт: ****; ИНН: ************; СНИЛС: ***-***-*** **; реквизиты: ****",
                "Приложения: перечень оснований из опубликованных протоколов. Проверка и подача выполняются вне платформы.",
            ],
            ["Спортсмен", "Сумма (демо)", "Основания"],
            rows,
            file_format,
        )
        return private_response(
            content,
            "application/pdf"
            if file_format == "pdf"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            f"award-petition-{pk}.{file_format}",
        )
