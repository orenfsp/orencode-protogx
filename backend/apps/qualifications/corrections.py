from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.competitions.services import audit, require_role

from .models import JudgeCategoryHistory, QualificationCorrection, SportRankHistory
from .services import _check_decision, has_confirmed_link


class CorrectionInput(serializers.Serializer):
    order_number = serializers.CharField(max_length=100)
    assigned_on = serializers.DateField()
    valid_until = serializers.DateField()
    reason = serializers.CharField(max_length=1000)


class CorrectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualificationCorrection
        fields = ["id", "created_at", "reason", "before", "after"]


class QualificationCorrectionsView(APIView):
    def record(self, request, kind, pk, lock=False):
        role = require_role(request, "federation", "athlete", "coach", "judge")
        if kind not in ("rank", "category"):
            from rest_framework.exceptions import NotFound
            raise NotFound()
        model = SportRankHistory if kind == "rank" else JudgeCategoryHistory
        query = model.objects.select_for_update() if lock else model.objects.all()
        record = get_object_or_404(query, pk=pk)
        if role == "federation":
            return record
        allowed = (kind == "rank" and ((role == "athlete" and record.athlete_id == request.user.pk) or (role == "coach" and has_confirmed_link(request.user, record.athlete_id, record.discipline_id)))) or (kind == "category" and role == "judge" and record.judge_id == request.user.pk)
        if not allowed:
            raise PermissionDenied("Недостаточно прав для истории исправлений")
        return record

    @extend_schema(responses=CorrectionSerializer(many=True))
    def get(self, request, kind, pk):
        record = self.record(request, kind, pk)
        return Response(CorrectionSerializer(record.corrections.order_by("id"), many=True).data)

    @extend_schema(request=CorrectionInput, responses={201: CorrectionSerializer})
    @transaction.atomic
    def post(self, request, kind, pk):
        require_role(request, "federation")
        record = self.record(request, kind, pk, lock=True)
        serializer = CorrectionInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        _check_decision("approved", "", data["order_number"], data["assigned_on"], data["valid_until"])
        before = {key: str(getattr(record, key)) for key in ("order_number", "assigned_on", "valid_until")}
        after = {key: str(data[key]) for key in before}
        revision = QualificationCorrection.objects.create(**{"rank_record" if kind == "rank" else "category_record": record}, actor=request.user, reason=data["reason"], before=before, after=after)
        for key in before:
            setattr(record, key, data[key])
        record.save(update_fields=list(before))
        audit(request.user, "qualification.corrected", record, before=before, after={**after, "revision": revision.pk, "reason": data["reason"]})
        return Response(CorrectionSerializer(revision).data, status=201)
