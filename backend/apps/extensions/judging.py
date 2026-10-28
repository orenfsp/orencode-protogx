from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.competitions.models import Competition, JudgeAssignment
from apps.competitions.services import audit, require_role

from .common import private_response, validated
from .documents import render_document
from .models import JudgingDocument


class JudgingInput(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["panel", "judge_work"])
    competition = serializers.PrimaryKeyRelatedField(queryset=Competition.objects.all(), required=False)
    judge = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role_assignments__role="judge"), required=False)
    start_year = serializers.IntegerField(min_value=1900, max_value=2200, required=False)
    end_year = serializers.IntegerField(min_value=1900, max_value=2200, required=False)


class JudgingDocumentsView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        role = require_role(request, "federation", "judge")
        documents = JudgingDocument.objects.all() if role == "federation" else JudgingDocument.objects.filter(owner=request.user)
        assignments = JudgeAssignment.objects.all() if role == "federation" else JudgeAssignment.objects.filter(judge=request.user)
        events = Competition.objects.filter(pk__in=assignments.values("competition_id")).order_by("title")
        judges = User.objects.filter(role_assignments__role="judge") if role == "federation" else User.objects.filter(pk=request.user.pk)
        return Response({"notice": "Формы v1 демонстрационные, без подписей. Состав берётся из назначений; отчёт включает только завершившиеся по дате события. Каждая выгрузка сохраняет снимок и аудит.", "items": [{"id": d.pk, "kind": d.get_kind_display(), "title": d.snapshot["title"], "created_at": d.created_at, "download_url": f"/api/v1/judging-documents/{d.pk}/download/"} for d in documents.order_by("-pk")[:100]], "options": {"competitions": [{"value": c.pk, "label": c.title} for c in events], "judges": [{"value": u.pk, "label": u.full_name} for u in judges]}})

    @extend_schema(request=JudgingInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        from django.utils import timezone
        role = require_role(request, "federation", "judge")
        data = validated(JudgingInput, request.data)
        owner = data.get("judge", request.user)
        if role == "judge" and owner.pk != request.user.pk:
            raise PermissionDenied("Только собственный отчёт")
        if data["kind"] == "panel":
            competition = data.get("competition")
            if not competition:
                raise ValidationError("Выберите соревнование")
            if role == "judge" and not competition.judge_assignments.filter(judge=request.user).exists():
                raise PermissionDenied("Требуется назначение на соревнование")
            rows = [[a.judge.full_name, a.role_label, a.assigned_at.date().isoformat()] for a in competition.judge_assignments.select_related("judge").order_by("pk")]
            title = f"Справка о составе судейской коллегии: {competition.title}"
            columns = ["Судья", "Должность", "Назначен"]
        else:
            start, end = data.get("start_year", timezone.localdate().year), data.get("end_year", timezone.localdate().year)
            if start > end or end - start > 20:
                raise ValidationError("Укажите интервал не более 21 года")
            assignments = JudgeAssignment.objects.filter(judge=owner, competition__starts_at__year__gte=start, competition__starts_at__year__lte=end, competition__ends_at__lte=timezone.now()).exclude(competition__state="draft").select_related("competition")
            rows = [[a.competition.title, a.competition.starts_at.date().isoformat(), a.role_label, a.competition.level] for a in assignments.order_by("competition__starts_at", "pk")]
            title = f"Отчёт о судействе: {owner.full_name}, {start}–{end}"
            columns = ["Соревнование", "Дата", "Должность", "Уровень"]
        doc = JudgingDocument.objects.create(kind=data["kind"], owner=owner, created_by=request.user, snapshot={"title": title, "columns": columns, "rows": rows, "template_version": 1, "source_verified": False})
        audit(request.user, "judging_document.generated", doc, after={"kind": doc.kind, "rows": len(rows)})
        return Response({"id": doc.pk}, status=201)


class JudgingDownloadView(APIView):
    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY, (200, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"): OpenApiTypes.BINARY})
    def get(self, request, pk):
        role = require_role(request, "federation", "judge")
        doc = get_object_or_404(JudgingDocument.objects.all() if role == "federation" else JudgingDocument.objects.filter(owner=request.user), pk=pk)
        file_format = request.query_params.get("file_format", "pdf")
        if file_format not in ("pdf", "docx"):
            raise ValidationError("Поддерживаются PDF и DOCX")
        snapshot = doc.snapshot
        content = render_document(snapshot["title"], [f"Документ № {doc.pk}; форма v{snapshot['template_version']}; сформирован {doc.created_at.date()}"], snapshot["columns"], snapshot["rows"], file_format)
        return private_response(content, "application/pdf" if file_format == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"judging-{pk}.{file_format}")
