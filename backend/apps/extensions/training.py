import hashlib
import json
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.catalogs.models import Discipline, Organization
from apps.competitions.services import audit, require_role

from .common import athlete_access, require_athlete_consent, validated
from .models import (
    Attendance,
    TrainingGroup,
    TrainingMembership,
    TrainingOrganization,
    TrainingSession,
)


class OrganizationInput(serializers.ModelSerializer):
    class Meta:
        model = TrainingOrganization
        fields = ["organization", "organization_type", "municipality", "license_details", "program", "disciplines", "coaches", "contact_url", "public"]


class GroupInput(serializers.ModelSerializer):
    class Meta:
        model = TrainingGroup
        fields = ["organization", "discipline", "coach", "stage", "name"]


class MembershipInput(serializers.Serializer):
    athlete = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role_assignments__role="athlete"))
    group = serializers.PrimaryKeyRelatedField(queryset=TrainingGroup.objects.all())
    starts_on = serializers.DateField()


class SessionInput(serializers.ModelSerializer):
    class Meta:
        model = TrainingSession
        fields = ["group", "date", "format", "evidence_url", "platform_log"]


class AttendanceInput(serializers.Serializer):
    session = serializers.PrimaryKeyRelatedField(queryset=TrainingSession.objects.all())
    membership = serializers.PrimaryKeyRelatedField(queryset=TrainingMembership.objects.all())
    present = serializers.BooleanField()


def manage_group(request, group):
    role = require_role(request, "federation", "coach")
    if role == "coach" and (group.coach_id != request.user.pk or not group.organization.coaches.filter(pk=request.user.pk).exists()):
        raise PermissionDenied("Только тренер этой группы")


@transaction.atomic
def enroll(*, request, athlete, group, starts_on):
    manage_group(request, group)
    athlete = User.objects.select_for_update().get(pk=athlete.pk)
    athlete_access(request, athlete, group.discipline, write=True)
    require_athlete_consent(athlete, starts_on)
    if starts_on > timezone.localdate() or starts_on < athlete.date_of_birth:
        raise ValidationError("Дата зачисления должна быть между рождением и сегодняшним днём")
    current = TrainingMembership.objects.select_for_update().filter(athlete=athlete, discipline=group.discipline, ends_on=None).first()
    if current:
        if current.group_id == group.pk or starts_on <= current.starts_on:
            raise ValidationError("Перевод должен менять группу и следовать за зачислением")
        manage_group(request, current.group)
        current.ends_on = starts_on-timedelta(days=1)
        current.save(update_fields=["ends_on"])
        audit(request.user, "training.membership_closed", current, after={"ends_on": current.ends_on.isoformat()})
    if TrainingMembership.objects.filter(athlete=athlete, discipline=group.discipline).filter(Q(ends_on=None) | Q(ends_on__gte=starts_on)).exists():
        raise ValidationError("Период пересекается с историей зачисления")
    membership = TrainingMembership.objects.create(athlete=athlete, group=group, discipline=group.discipline, starts_on=starts_on, recorded_by=request.user)
    audit(request.user, "training.enrolled", membership, after={"group": group.pk, "starts_on": starts_on.isoformat(), "previous": current.pk if current else None})
    return membership


def training_report(start_year, end_year, *, discipline=None, organization=None):
    """Inclusive periods and set union per year; coverage is explicitly training only."""
    queryset = TrainingMembership.objects.select_related("group").order_by("pk")
    if discipline:
        queryset = queryset.filter(discipline_id=discipline)
    if organization:
        queryset = queryset.filter(group__organization_id=organization)
    memberships = list(queryset)
    sources = [{"id": m.pk, "athlete": m.athlete_id, "group": m.group_id, "start": str(m.starts_on), "end": str(m.ends_on), "stage": m.group.stage, "discipline": m.discipline_id, "organization": m.group.organization_id} for m in memberships]
    rows = []
    for year in range(start_year, end_year+1):
        matching = [m for m in memberships if m.starts_on <= date(year, 12, 31) and (m.ends_on is None or m.ends_on >= date(year, 1, 1))]
        rows.append({"year": year, "unique_athletes": len({m.athlete_id for m in matching}), "membership_ids": [m.pk for m in matching]})
    fingerprint = hashlib.sha256(json.dumps({"sources": sources, "start": start_year, "end": end_year}, sort_keys=True).encode()).hexdigest()
    return {"method": "training-membership-calendar-year-v1", "coverage": "Только учебно-тренировочные группы; не полный реестр AC-11", "rows": rows, "fingerprint": fingerprint}


class TrainingView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        role = require_role(request, "federation", "coach", "athlete")
        groups = TrainingGroup.objects.select_related("organization__organization", "discipline", "coach")
        if role == "coach":
            groups = groups.filter(coach=request.user, organization__coaches=request.user)
        elif role == "athlete":
            groups = groups.filter(memberships__athlete=request.user).distinct()
        memberships = TrainingMembership.objects.filter(group__in=groups).select_related("athlete", "group")
        if role == "athlete":
            memberships = memberships.filter(athlete=request.user)
        sessions = list(TrainingSession.objects.filter(group__in=groups).select_related("group").order_by("-date", "-pk")[:100])
        athletes = User.objects.filter(role_assignments__role="athlete") if role == "federation" else User.objects.filter(coach_links__coach=request.user, coach_links__status="confirmed").distinct() if role == "coach" else User.objects.filter(pk=request.user.pk)
        items = [{"id": f"group-{g.pk}", "kind": "Группа", "name": g.name, "details": f"{g.organization.organization.name} · {g.get_stage_display()} · {g.discipline.name}", "record_id": g.pk} for g in groups]
        items += [{"id": f"membership-{m.pk}", "kind": "Зачисление", "name": m.athlete.full_name, "details": f"{m.group.name} · {m.starts_on} — {m.ends_on or 'продолжается'}", "record_id": m.pk} for m in memberships]
        for s in sessions:
            attendance = s.attendance.all() if role != "athlete" else s.attendance.filter(membership__athlete=request.user)
            details = f"{s.date} · {s.get_format_display()} · присутствие: {list(attendance.values_list('present', flat=True))}"
            if role != "athlete":
                details += f" · {s.evidence_url or s.platform_log}"
            items.append({"id": f"session-{s.pk}", "kind": "Занятие", "name": s.group.name, "details": details, "record_id": s.pk})
        return Response({"items": items, "notice": "История зачислений сохраняется. Спортсмен видит собственные отметки, записи занятий доступны тренеру и федерации. Групповой отчёт не заменяет полный AC-11 (PR #5).", "options": {"groups": [{"value": g.pk, "label": f"{g.pk}: {g.name}"} for g in groups], "athletes": [{"value": a.pk, "label": a.full_name} for a in athletes], "organizations": [{"value": o.pk, "label": o.organization.name} for o in TrainingOrganization.objects.filter(pk__in=groups.values('organization')).select_related("organization")] if role != "federation" else [{"value": o.pk, "label": o.organization.name} for o in TrainingOrganization.objects.select_related("organization")], "catalog_organizations": [{"value": o.pk, "label": o.name} for o in Organization.objects.all()] if role == "federation" else [], "disciplines": [{"value": d.pk, "label": d.name} for d in Discipline.objects.all()], "coaches": [{"value": c.pk, "label": c.full_name} for c in User.objects.filter(role_assignments__role="coach")] if role == "federation" else [], "memberships": [{"value": m.pk, "label": f"{m.pk}: {m.athlete.full_name} · {m.group.name}"} for m in memberships], "sessions": [{"value": s.pk, "label": f"{s.pk}: {s.group.name} · {s.date}"} for s in sessions]}})


class OrganizationCreateView(APIView):
    @extend_schema(request=OrganizationInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation")
        serializer = OrganizationInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        if any(not c.role_assignments.filter(role="coach").exists() for c in serializer.validated_data.get("coaches", [])):
            raise ValidationError("Назначаются только тренеры")
        card = serializer.save()
        audit(request.user, "training.organization_created", card)
        return Response({"id": card.pk}, status=201)


class GroupCreateView(APIView):
    @extend_schema(request=GroupInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation")
        data = validated(GroupInput, request.data)
        if not data["organization"].coaches.filter(pk=data["coach"].pk, role_assignments__role="coach").exists() or not data["organization"].disciplines.filter(pk=data["discipline"].pk).exists():
            raise ValidationError("Тренер и дисциплина должны входить в программу организации")
        group = TrainingGroup.objects.create(**data)
        audit(request.user, "training.group_created", group)
        return Response({"id": group.pk}, status=201)


class EnrollmentView(APIView):
    @extend_schema(request=MembershipInput, responses={201: OpenApiTypes.OBJECT})
    def post(self, request):
        return Response({"id": enroll(request=request, **validated(MembershipInput, request.data)).pk}, status=201)


class SessionCreateView(APIView):
    @extend_schema(request=SessionInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        data = validated(SessionInput, request.data)
        manage_group(request, data["group"])
        if data["date"] > timezone.localdate():
            raise ValidationError("Занятие не может быть в будущем")
        session = TrainingSession.objects.create(coach=request.user, **data)
        audit(request.user, "training.session_recorded", session, after={"date": str(session.date), "format": session.format})
        return Response({"id": session.pk}, status=201)


class AttendanceView(APIView):
    @extend_schema(request=AttendanceInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        data = validated(AttendanceInput, request.data)
        session, membership = data["session"], data["membership"]
        manage_group(request, session.group)
        if membership.group_id != session.group_id or membership.starts_on > session.date or (membership.ends_on and membership.ends_on < session.date):
            raise ValidationError("Спортсмен не числился в группе в день занятия")
        athlete_access(request, membership.athlete, session.group.discipline, write=True)
        row, _ = Attendance.objects.update_or_create(session=session, membership=membership, defaults={"present": data["present"]})
        audit(request.user, "training.attendance_recorded", row, after={"present": row.present})
        return Response({"id": row.pk}, status=201)
