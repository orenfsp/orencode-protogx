from django.db import transaction
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.competitions.models import CoachAthleteLink
from apps.competitions.services import age_on, audit, require_role
from apps.registry.models import (
    DisciplinePeriod,
    MunicipalityPeriod,
    OrganizationPeriod,
    ParticipationPeriod,
)

from .models import AthleteProfile, Guardian, PersonalDataConsent, User

CONSENT_VERSION = "v1-demo-2026-10-27"


class AntidopingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AthleteProfile
        fields = ["antidoping_completed_on", "antidoping_certificate_url"]

    def validate(self, attrs):
        when = attrs.get("antidoping_completed_on")
        url = attrs.get("antidoping_certificate_url", "")
        if bool(when) != bool(url):
            raise ValidationError("Укажите дату и ссылку на сертификат вместе")
        if when and when > timezone.localdate():
            raise ValidationError("Дата прохождения не может быть в будущем")
        if url and not url.startswith("https://"):
            raise ValidationError("Ссылка на сертификат должна использовать HTTPS")
        return attrs


class ProfileView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        require_role(request, "athlete")
        user, today = request.user, timezone.localdate()
        profile = AthleteProfile.objects.filter(user=user).first()
        def current(model):
            from django.db.models import Q
            return model.objects.filter(athlete=user, starts_on__lte=today).filter(Q(ends_on__isnull=True) | Q(ends_on__gte=today))
        organization = current(OrganizationPeriod).select_related("organization").order_by("-starts_on").first()
        municipality = current(MunicipalityPeriod).order_by("-starts_on").first()
        start = ParticipationPeriod.objects.filter(athlete=user).order_by("starts_on").first()
        return Response({"full_name": user.full_name, "date_of_birth": user.date_of_birth,
                         "organization": organization.organization.name if organization else "Без организации",
                         "municipality": municipality.municipality if municipality else "Не указан",
                         "training_started_year": start.starts_on.year if start else None,
                         "disciplines": list(current(DisciplinePeriod).values_list("discipline__name", flat=True).distinct()),
                         "coaches": list(CoachAthleteLink.objects.filter(athlete=user, status="confirmed").values("coach__full_name", "discipline__name")),
                         "guardians": list(Guardian.objects.filter(minor=user).values("full_name", "relationship", "confirmation_status")),
                         "antidoping_completed_on": profile.antidoping_completed_on if profile else None,
                         "antidoping_certificate_url": profile.antidoping_certificate_url if profile else ""})

    @extend_schema(request=AntidopingSerializer, responses=AntidopingSerializer)
    @transaction.atomic
    def patch(self, request):
        require_role(request, "athlete")
        # Lock identity to serialize profile creation and updates.
        User.objects.select_for_update().get(pk=request.user.pk)
        profile, _ = AthleteProfile.objects.get_or_create(user=request.user)
        serializer = AntidopingSerializer(profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit(request.user, "antidoping.updated", profile, after={"completed_on": str(profile.antidoping_completed_on)})
        return Response(serializer.data)


class ConsentInputSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["renew", "withdraw"])
    consent = serializers.BooleanField(default=False)
    guardian_consent = serializers.BooleanField(default=False)


class ConsentsView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        require_role(request, "federation", "athlete", "coach", "judge")
        return Response({"text_version": CONSENT_VERSION, "history": list(PersonalDataConsent.objects.filter(user=request.user).order_by("-recorded_at", "-id").values("id", "text_version", "recorded_at", "revoked_at", "confirmation_method"))})

    @extend_schema(request=ConsentInputSerializer, responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation", "athlete", "coach", "judge")
        User.objects.select_for_update().get(pk=request.user.pk)
        serializer = ConsentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        latest = PersonalDataConsent.objects.filter(user=request.user).order_by("-recorded_at", "-id").first()
        if data["action"] == "withdraw":
            if latest and latest.revoked_at is None:
                latest.revoked_at = timezone.now()
                latest.save(update_fields=["revoked_at"])
                audit(request.user, "consent.withdrawn", latest, after={"version": latest.text_version})
        else:
            if not data["consent"]:
                raise ValidationError("Подтвердите согласие на обработку персональных данных")
            guardian = None
            if request.user.date_of_birth and age_on(request.user.date_of_birth, timezone.localdate()) < 18:
                guardian = Guardian.objects.filter(minor=request.user).order_by("-id").first()
                if not guardian or not data["guardian_consent"]:
                    raise ValidationError("Требуется согласие законного представителя")
            if latest and latest.revoked_at is None:
                raise ValidationError("Согласие уже действует")
            record = PersonalDataConsent.objects.create(user=request.user, text_version=CONSENT_VERSION, guardian=guardian, confirmation_method="renewal_checkbox")
            audit(request.user, "consent.renewed", record, after={"version": CONSENT_VERSION})
        return self.get(request)
