from io import BytesIO

from django.apps import apps
from django.db import transaction
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from openpyxl import Workbook
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.competitions.models import Competition
from apps.competitions.services import audit, require_role

from .common import private_response
from .models import IndicatorEvidence, TrainingOrganization
from .training import training_report


class DevelopmentFilter(serializers.Serializer):
    start_year = serializers.IntegerField(
        min_value=1900, max_value=2199, required=False
    )
    end_year = serializers.IntegerField(min_value=1901, max_value=2200, required=False)
    discipline = serializers.IntegerField(min_value=1, required=False)
    organization = serializers.IntegerField(min_value=1, required=False)

    def validate(self, data):
        end = data.get("end_year", timezone.localdate().year)
        start = data.get("start_year", end - 1)
        if start >= end or end - start > 20:
            raise serializers.ValidationError(
                "Отчёт должен охватывать 2–21 календарных лет"
            )
        return {**data, "start_year": start, "end_year": end}


class IndicatorEvidenceInput(serializers.ModelSerializer):
    class Meta:
        model = IndicatorEvidence
        fields = ["year", "indicator", "title", "document_url"]


def development_data(filters):
    start, end = filters["start_year"], filters["end_year"]
    training = training_report(
        start,
        end,
        discipline=filters.get("discipline"),
        organization=filters.get("organization"),
    )
    events = (
        Competition.objects.filter(
            state__in=["published", "closed"],
            ends_at__lte=timezone.now(),
            starts_at__year__gte=start,
            starts_at__year__lte=end,
            calendar_entry__isnull=False,
            protocols__isnull=False,
        )
        .select_related("calendar_entry")
        .distinct()
    )
    if filters.get("discipline"):
        events = events.filter(discipline_id=filters["discipline"])
    items = [
        {
            "id": f"training-{r['year']}",
            "kind": "Учебно-тренировочные группы",
            "year": r["year"],
            "value": r["unique_athletes"],
            "source": f"TrainingMembership · {training['method']}",
            "details": f"История зачислений; fingerprint {training['fingerprint']}",
        }
        for r in training["rows"]
    ]
    for c in events:
        p = c.protocols.first()
        items.append(
            {
                "id": f"event-{c.pk}",
                "kind": "Проведённое событие",
                "year": c.starts_at.year,
                "value": c.title,
                "source": f"Competition:{c.pk}; CalendarEntry:{c.calendar_entry_id}; ProtocolPublication:{p.pk}",
                "details": f"{c.level} · {c.state} · {c.calendar_entry.get_source_display()} №{c.calendar_entry.entry_number}",
            }
        )
    cards = TrainingOrganization.objects.select_related("organization").all()
    if filters.get("organization"):
        cards = cards.filter(pk=filters["organization"])
    if filters.get("discipline"):
        cards = cards.filter(disciplines__pk=filters["discipline"])
    items += [
        {
            "id": f"organization-{c.pk}",
            "kind": "Организация подготовки (на дату расчёта)",
            "year": None,
            "value": c.organization.name,
            "source": f"TrainingOrganization:{c.pk}; Organization:{c.organization_id}",
            "details": c.organization_type,
        }
        for c in cards.distinct()
    ]
    available = apps.is_installed("apps.registry")
    if available:
        from apps.registry.analytics import consistent_report_read, participation_report

        with consistent_report_read():
            report = participation_report(
                start,
                end,
                discipline=filters.get("discipline"),
                organization=TrainingOrganization.objects.get(
                    pk=filters["organization"]
                ).organization_id
                if filters.get("organization")
                else None,
            )
        items += [
            {
                "id": f"registry-{r['year']}",
                "kind": "Численность полного реестра",
                "year": r["year"],
                "value": r["unique_athletes"],
                "source": "registry:calendar-year-v1",
                "details": "Переиспользована обязательная методика без изменения",
            }
            for r in report
        ]
    items += [
        {
            "id": f"evidence-{e.pk}",
            "kind": "Подтверждающий документ",
            "year": e.year,
            "value": e.title,
            "source": f"IndicatorEvidence:{e.pk}",
            "details": f"{e.get_indicator_display()} · {e.document_url}",
        }
        for e in IndicatorEvidence.objects.filter(year__gte=start, year__lte=end)
    ]
    return {
        "items": items,
        "training_report": training,
        "registry_available": available,
        "filters": filters,
        "calculated_at": timezone.now().isoformat(),
        "notice": "Источники: история групп, карточки организаций, календарные записи и последние опубликованные протоколы. Проведённое событие: дата окончания прошла, есть план и протокол. Численность групп считается по уникальному спортсмену за год. "
        + (
            "Полный реестр: исходная методика calendar-year-v1."
            if available
            else "Полный обязательный отчёт AC-11 недоступен до интеграции PR #5. Групповые числа не выданы за весь регион."
        ),
        "options": {},
    }


class DevelopmentView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        require_role(request, "federation")
        serializer = DevelopmentFilter(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = development_data(serializer.validated_data)
        if request.query_params.get("file_format") == "xlsx":
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Показатели"
            sheet.append(["Вид", "Год", "Значение", "Источник", "Пояснение"])
            for row in data["items"]:
                sheet.append(
                    [
                        safe_cell(row.get(k))
                        for k in ["kind", "year", "value", "source", "details"]
                    ]
                )
            metadata = workbook.create_sheet("Методика")
            metadata.append(["Область", data["notice"]])
            metadata.append(["Метод", data["training_report"]["method"]])
            metadata.append(["Fingerprint", data["training_report"]["fingerprint"]])
            stream = BytesIO()
            workbook.save(stream)
            return private_response(
                stream.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "development.xlsx",
            )
        return Response(data)


def safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


class IndicatorEvidenceView(APIView):
    @extend_schema(request=IndicatorEvidenceInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation")
        serializer = IndicatorEvidenceInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = serializer.save(created_by=request.user)
        audit(
            request.user,
            "development.evidence_added",
            row,
            after={"indicator": row.indicator, "year": row.year},
        )
        return Response({"id": row.pk}, status=201)
