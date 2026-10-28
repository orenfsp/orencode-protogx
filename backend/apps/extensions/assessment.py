from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.competitions.models import CoachAthleteLink
from apps.competitions.services import audit, require_role

from .common import athlete_access, require_athlete_consent, validated
from .models import (
    AssessmentAttempt,
    AssessmentNorm,
    Attestation,
    TrainingGroup,
    TrainingMembership,
    TrainingStage,
)
from .notifications import notify
from .training import enroll, manage_group


class NormInput(serializers.ModelSerializer):
    class Meta:
        model = AssessmentNorm
        fields = ["key", "name", "version", "discipline", "stage", "sex", "unit", "comparator", "threshold", "effective_from", "effective_until", "source_url", "source_version"]

    def validate(self, data):
        if data.get("effective_until") and data["effective_until"] < data["effective_from"]:
            raise serializers.ValidationError("Конец действия раньше начала")
        if data["threshold"] < 0:
            raise serializers.ValidationError("Порог не может быть отрицательным")
        return data


class AttemptInput(serializers.Serializer):
    athlete = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role_assignments__role="athlete"))
    norm = serializers.PrimaryKeyRelatedField(queryset=AssessmentNorm.objects.all())
    measured_on = serializers.DateField()
    value = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0)
    evidence = serializers.URLField(required=False, allow_blank=True, default="")


class AttestationInput(serializers.Serializer):
    membership = serializers.PrimaryKeyRelatedField(queryset=TrainingMembership.objects.all())
    assessed_on = serializers.DateField()
    sex = serializers.ChoiceField(choices=["all", "female", "male"], default="all")


class TransferInput(serializers.Serializer):
    group = serializers.PrimaryKeyRelatedField(queryset=TrainingGroup.objects.all())


def applicable_norms(group, on, sex):
    norms = AssessmentNorm.objects.filter(discipline=group.discipline, stage=group.stage, effective_from__lte=on, sex__in=["all", sex]).filter(Q(effective_until=None) | Q(effective_until__gte=on)).order_by("key", "-version", "-effective_from", "-pk")
    latest = {}
    for norm in norms:
        if norm.key not in latest or (latest[norm.key].sex == "all" and norm.sex == sex and sex != "all"):
            latest[norm.key] = norm
    return list(latest.values())


def assessment_snapshot(membership, on, sex):
    norms = applicable_norms(membership.group, on, sex)
    rows = []
    for norm in norms:
        attempt = AssessmentAttempt.objects.filter(athlete=membership.athlete, norm=norm, measured_on__gte=membership.starts_on, measured_on__lte=on).order_by("-measured_on", "-pk").first()
        rows.append({"norm": norm.pk, "name": norm.name, "version": norm.version, "attempt": attempt.pk if attempt else None, "passed": bool(attempt and attempt.outcome["passed"]), "explanation": attempt.outcome["explanation"] if attempt else "Измерение отсутствует", "demonstration": not norm.source_verified})
    return {"requirements": rows, "eligible": bool(rows) and all(r["passed"] for r in rows), "demonstration": not rows or any(r["demonstration"] for r in rows), "regulatory_blocker": "Актуальные первичные ФССП и поправки не подтверждены; это предварительный результат"}


class AssessmentView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        role = require_role(request, "federation", "coach", "athlete")
        athletes = User.objects.filter(role_assignments__role="athlete") if role == "federation" else User.objects.filter(coach_links__coach=request.user, coach_links__status="confirmed").distinct() if role == "coach" else User.objects.filter(pk=request.user.pk)
        attempts = AssessmentAttempt.objects.filter(athlete__in=athletes).select_related("norm", "athlete")
        if role == "coach":
            attempts = attempts.filter(Exists(CoachAthleteLink.objects.filter(coach=request.user, athlete_id=OuterRef("athlete_id"), discipline_id=OuterRef("norm__discipline_id"), status="confirmed")))
        memberships = TrainingMembership.objects.filter(athlete__in=athletes, ends_on=None).select_related("athlete", "group")
        if role == "coach":
            memberships = memberships.filter(group__coach=request.user)
        attestations = Attestation.objects.filter(membership__in=memberships)
        items = [{"id": f"attempt-{a.pk}", "kind": "Измерение", "name": a.athlete.full_name, "details": f"{a.norm.name} · {a.measured_on} · {a.outcome['explanation']}"} for a in attempts.order_by("-pk")[:100]]
        items += [{"id": f"attestation-{a.pk}", "kind": "Аттестация", "name": a.membership.athlete.full_name, "details": f"№{a.pk} · {a.assessed_on} · {'Предварительно выполнено' if a.snapshot['eligible'] else 'Не выполнено'} · {'Перевод записан' if a.transfer_id else 'Ожидает решения'} · ДЕМОНСТРАЦИЯ"} for a in attestations]
        items += [{"id": f"norm-{n.pk}", "kind": "Норматив", "name": n.name, "details": f"v{n.version} · {n.get_stage_display()} · {n.get_comparator_display()} {n.threshold} {n.unit} · {n.effective_from} · {n.source_version}"} for n in AssessmentNorm.objects.all()]
        from apps.catalogs.models import Discipline
        return Response({"items": items, "notice": "Демонстрационная аттестация. Пороги не подтверждены актуальным приказом №445 и не дают юридического права на перевод. Измерения и версии сохраняются, окончательное решение записывает уполномоченный тренер/федерация.", "options": {"athletes": [{"value": a.pk, "label": a.full_name} for a in athletes], "norms": [{"value": n.pk, "label": f"{n.name} v{n.version}"} for n in AssessmentNorm.objects.all()], "memberships": [{"value": m.pk, "label": f"{m.athlete.full_name} · {m.group.name}"} for m in memberships], "attestations": [{"value": a.pk, "label": f"№{a.pk} · {a.membership.athlete.full_name}"} for a in attestations], "groups": [{"value": g.pk, "label": g.name} for g in TrainingGroup.objects.all() if role == "federation" or g.coach_id == request.user.pk], "disciplines": [{"value": d.pk, "label": d.name} for d in Discipline.objects.all()]}})


class NormCreateView(APIView):
    @extend_schema(request=NormInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation")
        serializer = NormInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        norm = serializer.save(source_verified=False)
        audit(request.user, "assessment.norm_version_created", norm)
        return Response({"id": norm.pk}, status=201)


class AttemptCreateView(APIView):
    @extend_schema(request=AttemptInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        data = validated(AttemptInput, request.data)
        norm, athlete, on = data["norm"], data["athlete"], data["measured_on"]
        athlete_access(request, athlete, norm.discipline, write=True)
        require_athlete_consent(athlete, on)
        if on > timezone.localdate() or on < norm.effective_from or (norm.effective_until and on > norm.effective_until):
            raise ValidationError("На дату измерения норматив не действует")
        passed = data["value"] >= norm.threshold if norm.comparator == "min" else data["value"] <= norm.threshold
        explanation = f"{data['value']} {norm.unit}; требуется {norm.get_comparator_display().lower()} {norm.threshold}; {'выполнено' if passed else 'не выполнено'}"
        attempt = AssessmentAttempt.objects.create(**data, recorded_by=request.user, outcome={"passed": passed, "threshold": str(norm.threshold), "comparator": norm.comparator, "explanation": explanation, "demonstration": not norm.source_verified})
        audit(request.user, "assessment.attempt_recorded", attempt, after={"passed": passed, "norm": norm.pk})
        notify(athlete, f"attempt:{attempt.pk}", "Записано измерение норматива")
        return Response({"id": attempt.pk, "outcome": attempt.outcome}, status=201)


class AttestationCreateView(APIView):
    @extend_schema(request=AttestationInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        data = validated(AttestationInput, request.data)
        membership = data["membership"]
        manage_group(request, membership.group)
        athlete_access(request, membership.athlete, membership.discipline, write=True)
        if data["assessed_on"] > timezone.localdate() or data["assessed_on"] < membership.starts_on or (membership.ends_on and data["assessed_on"] > membership.ends_on):
            raise ValidationError("Аттестация вне периода зачисления")
        record = Attestation.objects.create(**data, snapshot=assessment_snapshot(membership, data["assessed_on"], data["sex"]), created_by=request.user)
        audit(request.user, "assessment.attestation_recorded", record, after=record.snapshot)
        return Response({"id": record.pk, **record.snapshot}, status=201)


class AttestationApproveView(APIView):
    @extend_schema(request=TransferInput, responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self, request, pk):
        record = get_object_or_404(Attestation.objects.select_for_update(), pk=pk)
        manage_group(request, record.membership.group)
        group = validated(TransferInput, request.data)["group"]
        stages = list(TrainingStage.values)
        old = record.membership.group
        if record.transfer_id or record.membership.ends_on or stages.index(old.stage)+1 >= len(stages) or group.stage != stages[stages.index(old.stage)+1] or group.discipline_id != old.discipline_id:
            raise ValidationError("Нельзя выполнить этот перевод")
        fresh = assessment_snapshot(record.membership, record.assessed_on, record.sex)
        if fresh != record.snapshot or not fresh["eligible"]:
            raise ValidationError("Требования не выполнены или появились новые данные; проведите новую аттестацию")
        transfer = enroll(request=request, athlete=record.membership.athlete, group=group, starts_on=timezone.localdate())
        record.transfer, record.approved_by = transfer, request.user
        record.save(update_fields=["transfer", "approved_by"])
        audit(request.user, "assessment.transfer_approved", record, after={"transfer": transfer.pk, "demonstration": fresh["demonstration"]})
        notify(transfer.athlete, f"attestation:{record.pk}:approved", "Записан перевод после аттестации (демонстрация)")
        return Response({"id": record.pk, "transfer": transfer.pk, "demonstration": fresh["demonstration"]})
