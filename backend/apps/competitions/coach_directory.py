from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import (
    PersonalDataConsent,
    User,
    UserRole,
    has_current_consent,
)
from apps.catalogs.models import Discipline

from .models import AuditEvent, CoachAthleteLink
from .services import age_on, audit, require_role


def discoverable_athletes(coach, search):
    # Search exposes minimal adult registry data only. Minors are discoverable
    # only by an already confirmed coach; initial requests still support known email.
    latest = PersonalDataConsent.objects.filter(user_id=OuterRef("pk")).order_by("-recorded_at", "-pk")
    candidates = User.objects.filter(is_active=True, role_assignments__role="athlete", full_name__icontains=search).annotate(
        consent_id=Subquery(latest.values("id")[:1]), revoked=Subquery(latest.values("revoked_at")[:1]),
    ).filter(consent_id__isnull=False, revoked__isnull=True).order_by("full_name", "pk")
    linked = set(CoachAthleteLink.objects.filter(coach=coach, status="confirmed").values_list("athlete_id", flat=True))
    rows = []
    for person in candidates.iterator():
        if person.date_of_birth and (age_on(person.date_of_birth, timezone.localdate()) >= 18 or person.pk in linked):
            rows.append(person)
        if len(rows) == 20:
            break
    return rows


class AthleteChoiceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()


class DirectoryRequestSerializer(serializers.Serializer):
    athlete = serializers.IntegerField(min_value=1)
    discipline = serializers.PrimaryKeyRelatedField(queryset=Discipline.objects.filter(is_active=True))
    search = serializers.CharField(min_length=3, max_length=100)


class DirectoryAcceptedSerializer(serializers.Serializer):
    detail = serializers.CharField()


class CoachDirectoryView(APIView):
    class DirectoryThrottle(UserRateThrottle):
        rate = "20/min"
        scope = "coach_directory"

    throttle_classes = [DirectoryThrottle]
    @extend_schema(parameters=[OpenApiParameter("search", str, required=True)], responses=AthleteChoiceSerializer(many=True))
    def get(self, request):
        require_role(request, "coach")
        search = request.query_params.get("search", "").strip()
        if not 3 <= len(search) <= 100:
            raise ValidationError("Введите от 3 до 100 символов имени спортсмена")
        return Response(AthleteChoiceSerializer(discoverable_athletes(request.user, search), many=True).data)

    @extend_schema(request=DirectoryRequestSerializer, responses={202: DirectoryAcceptedSerializer})
    @transaction.atomic
    def post(self, request):
        require_role(request, "coach")
        serializer = DirectoryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # Revoking a role and creating a link serialize on the existing role row.
        get_object_or_404(UserRole.objects.select_for_update(), user=request.user, role="coach")
        require_role(request, "coach")
        # Recheck the same limited directory and lock identity before creating a link.
        visible = {person.pk for person in discoverable_athletes(request.user, data["search"].strip())}
        if data["athlete"] not in visible:
            raise PermissionDenied("Спортсмен недоступен для запроса из реестра")
        athlete = get_object_or_404(User.objects.select_for_update(), pk=data["athlete"], is_active=True)
        if not has_current_consent(athlete):
            raise PermissionDenied("Спортсмен недоступен для запроса из реестра")
        if not athlete.date_of_birth or (age_on(athlete.date_of_birth, timezone.localdate()) < 18 and not CoachAthleteLink.objects.filter(coach=request.user, athlete=athlete, status="confirmed").exists()):
            raise PermissionDenied("Спортсмен недоступен для запроса из реестра")
        link, created = CoachAthleteLink.objects.get_or_create(coach=request.user, athlete=athlete, discipline=data["discipline"])
        if created:
            audit(request.user, "coach_link.requested", link, after={"discipline_id": link.discipline_id})
        return Response({"detail": "Запрос сохранён. Ожидается подтверждение спортсменом."}, status=202)


class LinkHistorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    action = serializers.CharField()
    active_role = serializers.CharField()
    before = serializers.DictField()
    after = serializers.DictField()


class LinkHistoryView(APIView):
    @extend_schema(responses=LinkHistorySerializer(many=True))
    def get(self, request, pk):
        role = require_role(request, "athlete", "coach")
        scope = {"athlete": request.user} if role == "athlete" else {"coach": request.user}
        link = get_object_or_404(CoachAthleteLink, pk=pk, **scope)
        events = AuditEvent.objects.filter(target_type="coachathletelink", target_id=link.pk, action__startswith="coach_link.").order_by("created_at", "pk")
        return Response(LinkHistorySerializer(events, many=True).data)
