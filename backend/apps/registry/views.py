from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiParameter,
    PolymorphicProxySerializer,
    extend_schema,
)
from rest_framework import filters, generics, serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import (
    AthleteProfile,
    Guardian,
    User,
    UserRole,
    has_current_consent,
)
from apps.catalogs.models import Discipline, Organization
from apps.competitions.models import (
    AgeGroup,
    AuditEvent,
    CoachAthleteLink,
    JudgeAssignment,
)
from apps.competitions.services import age_on, audit
from apps.qualifications.models import JudgeCategoryHistory, SportRankHistory
from apps.qualifications.services import (
    category_level,
    most_significant,
    rank_level,
    validity_state,
)
from apps.teams.services import require_federation

from .analytics import consistent_report_read, participation_report, report_fingerprint
from .exporters import export_participation
from .models import (
    DisciplinePeriod,
    MunicipalityPeriod,
    OrganizationPeriod,
    ParticipationPeriod,
    StaffProfile,
    TrainingStagePeriod,
)
from .serializers import (
    AnnualReportSerializer,
    ClosePeriodSerializer,
    DisciplinePeriodSerializer,
    MunicipalityPeriodSerializer,
    OrganizationFilterSerializer,
    OrganizationPeriodSerializer,
    OrganizationSerializer,
    ParticipationSerializer,
    PeriodAuditSerializer,
    PeriodCorrectionSerializer,
    PersonFilterSerializer,
    PersonSerializer,
    PersonUpdateSerializer,
    ProfileCreateSerializer,
    RegistryOptionsSerializer,
    RegistryPersonContextSerializer,
    ReportQuerySerializer,
    StaffProfileSerializer,
    TrainingStagePeriodSerializer,
    TransferSerializer,
)
from .services import add_period, close_period, correct_period, transfer_organization


class RegistryPagination(PageNumberPagination):
    page_size = 50


class FederationMixin:
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        require_federation(request)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


class RegistryOptions(FederationMixin, APIView):
    serializer_class = RegistryOptionsSerializer

    @extend_schema(responses=RegistryOptionsSerializer)
    def get(self, request):
        municipalities = set(MunicipalityPeriod.objects.exclude(municipality="").values_list("municipality", flat=True))
        municipalities.update(Organization.objects.exclude(municipality="").values_list("municipality", flat=True))
        return Response({"organizations": list(Organization.objects.order_by("name", "pk").values("id", "name")), "disciplines": list(Discipline.objects.order_by("name", "pk").values("id", "name")), "age_groups": list(AgeGroup.objects.order_by("name", "pk").values("id", "name")), "municipalities": sorted(municipalities)})


class PeopleList(FederationMixin, generics.ListAPIView):
    serializer_class = PersonSerializer
    pagination_class = RegistryPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["full_name"]
    role = None

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "registry_role": self.role}

    def get_queryset(self):
        query = PersonFilterSerializer(data=self.request.query_params.dict())
        query.is_valid(raise_exception=True)
        values = query.validated_data
        qs = User.objects.filter(role_assignments__role=self.role).select_related("athlete_profile__organization").prefetch_related("registry_staff_profiles__organization")
        if "active" in values:
            qs = qs.filter(is_active=values["active"])
        if "organization" in values:
            if self.role == UserRole.Role.ATHLETE:
                qs = qs.filter(athlete_profile__organization_id=values["organization"])
            else:
                qs = qs.filter(registry_staff_profiles__role=self.role, registry_staff_profiles__organization_id=values["organization"])
        today = timezone.localdate()
        if "discipline" in values:
            if self.role == UserRole.Role.ATHLETE:
                ids = DisciplinePeriod.objects.filter(discipline_id=values["discipline"], starts_on__lte=today).filter(Q(ends_on__isnull=True) | Q(ends_on__gte=today)).values("athlete_id")
                qs = qs.filter(pk__in=ids)
            elif self.role == UserRole.Role.COACH:
                qs = qs.filter(Q(coached_links__discipline_id=values["discipline"], coached_links__status="confirmed") | Q(registry_staff_profiles__role=self.role, registry_staff_profiles__disciplines__id=values["discipline"]))
            else:
                qs = qs.filter(Q(judge_assignments__competition__discipline_id=values["discipline"]) | Q(registry_staff_profiles__role=self.role, registry_staff_profiles__disciplines__id=values["discipline"]))
        if "municipality" in values:
            if self.role == UserRole.Role.ATHLETE:
                ids = MunicipalityPeriod.objects.filter(municipality=values["municipality"], starts_on__lte=today).filter(Q(ends_on__isnull=True) | Q(ends_on__gte=today)).values("athlete_id")
                qs = qs.filter(pk__in=ids)
            else:
                qs = qs.filter(registry_staff_profiles__role=self.role, registry_staff_profiles__organization__municipality=values["municipality"])
        return qs.distinct().order_by("full_name", "pk")

    @extend_schema(parameters=[OpenApiParameter("active", bool), OpenApiParameter("organization", int), OpenApiParameter("discipline", int), OpenApiParameter("municipality", str)])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AthletesList(PeopleList):
    role = UserRole.Role.ATHLETE


class CoachesList(PeopleList):
    role = UserRole.Role.COACH


class JudgesList(PeopleList):
    role = UserRole.Role.JUDGE


class EligibleUsers(FederationMixin, generics.ListAPIView):
    serializer_class = PersonSerializer
    pagination_class = RegistryPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["full_name"]

    @extend_schema(parameters=[OpenApiParameter("role", str, required=True)])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        role = self.request.query_params.get("role")
        if role not in ("athlete", "coach", "judge"):
            raise serializers.ValidationError({"role": "Choose athlete, coach or judge"})
        users = User.objects.filter(is_active=True, role_assignments__role=role)
        if role == "athlete":
            users = users.filter(athlete_profile__isnull=True)
        else:
            users = users.exclude(pk__in=StaffProfile.objects.filter(role=role).values("user_id"))
        return users.select_related("athlete_profile__organization").order_by("full_name", "pk")


class CreateRegistryProfile(FederationMixin, APIView):
    serializer_class = ProfileCreateSerializer

    @extend_schema(request=ProfileCreateSerializer, responses={201: PersonSerializer})
    @transaction.atomic
    def post(self, request, role):
        if role not in ("athlete", "coach", "judge"):
            raise serializers.ValidationError({"role": "Unknown registry role"})
        serializer = ProfileCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.select_for_update().get(pk=serializer.validated_data["user"].pk)
        if not user.is_active or not user.role_assignments.filter(role=role).exists():
            raise serializers.ValidationError({"user": "An active user with the assigned role is required"})
        if not has_current_consent(user):
            raise serializers.ValidationError({"user": "Current personal-data consent is required"})
        if not user.date_of_birth or user.date_of_birth > timezone.localdate():
            raise serializers.ValidationError({"user": "A valid date of birth is required"})
        if age_on(user.date_of_birth, timezone.localdate()) < 18:
            consent = user.consents.order_by("-recorded_at", "-pk").first()
            if not consent or not consent.guardian_id or not Guardian.objects.filter(pk=consent.guardian_id, minor=user, confirmation_status="verified").exists():
                raise serializers.ValidationError({"user": "Verified guardian consent is required"})
        if role == "athlete":
            if AthleteProfile.objects.filter(user=user).exists():
                raise serializers.ValidationError({"user": "Profile already exists"})
            profile = AthleteProfile.objects.create(user=user, organization=serializer.validated_data.get("organization"))
        else:
            if StaffProfile.objects.filter(user=user, role=role).exists():
                raise serializers.ValidationError({"user": "Profile already exists"})
            profile = StaffProfile.objects.create(user=user, role=role, organization=serializer.validated_data.get("organization"))
        audit(request.user, "registry.profile_created", profile, after={"user_id": user.pk, "role": role, "organization_id": profile.organization_id})
        return Response(PersonSerializer(user, context={"registry_role": role}).data, status=201)


class RegistryPersonContext(FederationMixin, APIView):
    serializer_class = RegistryPersonContextSerializer

    @extend_schema(responses=RegistryPersonContextSerializer)
    def get(self, request, role, pk):
        if role not in ("athlete", "coach", "judge"):
            raise serializers.ValidationError({"role": "Unknown registry role"})
        user = get_object_or_404(User, pk=pk, role_assignments__role=role)
        ranks = SportRankHistory.objects.filter(athlete=user).select_related("discipline") if role == "athlete" else []
        categories = JudgeCategoryHistory.objects.filter(judge=user) if role == "judge" else []
        current_rank = most_significant(ranks, rank_level)
        current_category = most_significant(categories, category_level)
        today = timezone.localdate()
        links = CoachAthleteLink.objects.filter(athlete=user) if role == "athlete" else CoachAthleteLink.objects.filter(coach=user) if role == "coach" else CoachAthleteLink.objects.none()
        links = links.select_related("coach", "athlete", "discipline").order_by("pk")
        assignments = JudgeAssignment.objects.filter(judge=user).select_related("competition__discipline").order_by("-competition__starts_at", "-pk") if role == "judge" else []
        return Response({"ranks": [{"rank": item.get_rank_display(), "discipline": item.discipline.name, "assigned_on": item.assigned_on, "valid_until": item.valid_until, "validity": validity_state(item.valid_until, today), "current": bool(current_rank and item.pk == current_rank.pk)} for item in ranks], "categories": [{"category": item.get_category_display(), "assigned_on": item.assigned_on, "valid_until": item.valid_until, "validity": validity_state(item.valid_until, today), "current": bool(current_category and item.pk == current_category.pk)} for item in categories], "coach_links": [{"coach": item.coach.full_name, "athlete": item.athlete.full_name, "discipline": item.discipline.name, "status": item.status} for item in links], "assignments": [{"competition": item.competition.title, "discipline": item.competition.discipline.name, "starts_at": item.competition.starts_at, "role": item.role_label} for item in assignments]})


class PersonDetail(FederationMixin, generics.RetrieveUpdateAPIView):
    serializer_class = PersonSerializer
    http_method_names = ["get", "patch", "head", "options"]
    role = None

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "registry_role": self.role}

    def get_queryset(self):
        return User.objects.filter(role_assignments__role=self.role).select_related("athlete_profile__organization")

    @extend_schema(request=PersonUpdateSerializer, responses=PersonSerializer)
    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        user = get_object_or_404(User.objects.select_for_update().filter(role_assignments__role=self.role), pk=kwargs["pk"])
        serializer = PersonUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        birth = serializer.validated_data.get("date_of_birth")
        if birth and user.role_assignments.filter(role=UserRole.Role.ATHLETE).exists() and any(model.objects.filter(athlete=user, starts_on__lt=birth).exists() for model, _ in PERIODS.values()):
            raise serializers.ValidationError({"date_of_birth": "Existing history begins before this date"})
        before = {"full_name": user.full_name, "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None}
        user = serializer.save()
        after = {"full_name": user.full_name, "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None}
        if before != after:
            audit(request.user, "registry.person_updated", user, before=before, after=after)
        return Response(PersonSerializer(user, context={"registry_role": self.role}).data)

class AthleteDetail(PersonDetail):
    role = UserRole.Role.ATHLETE


class CoachDetail(PersonDetail):
    role = UserRole.Role.COACH


class JudgeDetail(PersonDetail):
    role = UserRole.Role.JUDGE


class StaffProfileDetail(FederationMixin, generics.RetrieveUpdateAPIView):
    serializer_class = StaffProfileSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        role = self.kwargs["role"]
        if role not in ("coach", "judge"):
            raise serializers.ValidationError({"role": "Choose coach or judge"})
        return StaffProfile.objects.filter(role=role, user__role_assignments__role=role)

    def get_object(self):
        return get_object_or_404(self.get_queryset(), user_id=self.kwargs["pk"])

    @transaction.atomic
    def perform_update(self, serializer):
        profile = StaffProfile.objects.select_for_update().get(pk=serializer.instance.pk)
        before = {"organization_id": profile.organization_id, "disciplines": list(profile.disciplines.order_by("pk").values_list("pk", flat=True))}
        serializer.instance = profile
        profile = serializer.save()
        after = {"organization_id": profile.organization_id, "disciplines": list(profile.disciplines.order_by("pk").values_list("pk", flat=True))}
        if before != after:
            audit(self.request.user, "registry.staff_profile_updated", profile, before=before, after=after)


class Organizations(FederationMixin, generics.ListCreateAPIView):
    serializer_class = OrganizationSerializer
    pagination_class = RegistryPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "code", "municipality"]
    def get_queryset(self):
        query = OrganizationFilterSerializer(data=self.request.query_params.dict())
        query.is_valid(raise_exception=True)
        values = query.validated_data
        organizations = Organization.objects.all()
        if "active" in values:
            organizations = organizations.filter(is_active=values["active"])
        if "municipality" in values:
            organizations = organizations.filter(municipality=values["municipality"])
        if "organization_type" in values:
            organizations = organizations.filter(organization_type=values["organization_type"])
        return organizations.order_by("name", "pk")

    @extend_schema(parameters=[OpenApiParameter("active", bool), OpenApiParameter("municipality", str), OpenApiParameter("organization_type", str)])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @transaction.atomic
    def perform_create(self, serializer):
        obj = serializer.save()
        audit(self.request.user, "registry.organization_created", obj, after={"code": obj.code, "name": obj.name})


class OrganizationDetail(FederationMixin, generics.RetrieveUpdateAPIView):
    serializer_class = OrganizationSerializer
    queryset = Organization.objects.all()

    @transaction.atomic
    def perform_update(self, serializer):
        obj = self.get_object()
        before = {"code": obj.code, "name": obj.name, "is_active": obj.is_active, "municipality": obj.municipality, "organization_type": obj.organization_type}
        contact_changed = "contact" in serializer.validated_data and serializer.validated_data["contact"] != obj.contact
        obj = serializer.save()
        audit(self.request.user, "registry.organization_updated", obj, before=before, after={"code": obj.code, "name": obj.name, "is_active": obj.is_active, "municipality": obj.municipality, "organization_type": obj.organization_type, "contact_changed": contact_changed})


PERIODS = {
    "participation": (ParticipationPeriod, ParticipationSerializer),
    "disciplines": (DisciplinePeriod, DisciplinePeriodSerializer),
    "organizations": (OrganizationPeriod, OrganizationPeriodSerializer),
    "municipalities": (MunicipalityPeriod, MunicipalityPeriodSerializer),
    "training-stages": (TrainingStagePeriod, TrainingStagePeriodSerializer),
}
PERIOD_SCHEMA = PolymorphicProxySerializer(component_name="RegistryPeriod", serializers=[ParticipationSerializer, DisciplinePeriodSerializer, OrganizationPeriodSerializer, MunicipalityPeriodSerializer, TrainingStagePeriodSerializer], resource_type_field_name=None)


class PeriodView(FederationMixin, APIView):
    serializer_class = ParticipationSerializer

    def get_data(self, pk, kind):
        athlete = get_object_or_404(User, pk=pk, role_assignments__role=UserRole.Role.ATHLETE)
        if kind not in PERIODS:
            raise serializers.ValidationError({"kind": "Unknown period type"})
        model, serializer = PERIODS[kind]
        return athlete, model, serializer

    @extend_schema(responses=PolymorphicProxySerializer(component_name="RegistryPeriodList", serializers=[ParticipationSerializer, DisciplinePeriodSerializer, OrganizationPeriodSerializer, MunicipalityPeriodSerializer, TrainingStagePeriodSerializer], resource_type_field_name=None, many=True))
    def get(self, request, pk, kind):
        athlete, model, serializer = self.get_data(pk, kind)
        return Response(serializer(model.objects.filter(athlete=athlete).order_by("starts_on", "pk"), many=True).data)

    @extend_schema(request=PERIOD_SCHEMA, responses={201: PERIOD_SCHEMA})
    def post(self, request, pk, kind):
        athlete, model, serializer_class = self.get_data(pk, kind)
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        period = add_period(actor=request.user, model=model, athlete=athlete, **serializer.validated_data)
        return Response(serializer_class(period).data, status=201)


class TransferView(FederationMixin, APIView):
    serializer_class = TransferSerializer

    @extend_schema(request=TransferSerializer, responses={201: OrganizationPeriodSerializer})
    def post(self, request, pk):
        athlete = get_object_or_404(User, pk=pk, role_assignments__role=UserRole.Role.ATHLETE)
        serializer = TransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        period = transfer_organization(actor=request.user, athlete=athlete, **serializer.validated_data)
        return Response(OrganizationPeriodSerializer(period).data, status=201)


class ClosePeriodView(FederationMixin, APIView):
    serializer_class = ClosePeriodSerializer

    @extend_schema(request=ClosePeriodSerializer, responses=PERIOD_SCHEMA)
    def post(self, request, pk, kind, period_id):
        athlete, model, serializer_class = PeriodView().get_data(pk, kind)
        serializer = ClosePeriodSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        period = close_period(actor=request.user, model=model, athlete=athlete, period_id=period_id, **serializer.validated_data)
        return Response(serializer_class(period).data)


class CorrectPeriodView(FederationMixin, APIView):
    serializer_class = PeriodCorrectionSerializer

    @extend_schema(request=PeriodCorrectionSerializer, responses=PERIOD_SCHEMA)
    def post(self, request, pk, kind, period_id):
        athlete, model, period_serializer = PeriodView().get_data(pk, kind)
        serializer = PeriodCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not isinstance(serializer.validated_data["corrected"], dict) or "ends_on" not in serializer.validated_data["corrected"]:
            raise serializers.ValidationError({"corrected": "Provide a complete replacement including ends_on"})
        corrected = period_serializer(data=serializer.validated_data["corrected"])
        corrected.is_valid(raise_exception=True)
        period = correct_period(actor=request.user, model=model, athlete=athlete, period_id=period_id, expected=serializer.validated_data["expected"], corrected=corrected.validated_data, reason=serializer.validated_data["reason"])
        return Response(period_serializer(period).data)


class PeriodAuditView(FederationMixin, APIView):
    serializer_class = PeriodAuditSerializer

    @extend_schema(responses=PeriodAuditSerializer(many=True))
    def get(self, request, pk, kind, period_id):
        athlete, model, _ = PeriodView().get_data(pk, kind)
        period = get_object_or_404(model, pk=period_id, athlete=athlete)
        events = AuditEvent.objects.filter(target_type=period._meta.model_name, target_id=period.pk, action__startswith="registry.").select_related("actor").order_by("-created_at", "-pk")
        return Response(PeriodAuditSerializer(events, many=True).data)


REPORT_PARAMETERS = [OpenApiParameter(name, typ, required=name in ("start_year", "end_year")) for name, typ in (("start_year", int), ("end_year", int), ("organization", int), ("discipline", int), ("municipality", str), ("age_group", int))]


class ParticipationReport(FederationMixin, APIView):
    serializer_class = AnnualReportSerializer

    @extend_schema(parameters=REPORT_PARAMETERS, responses=AnnualReportSerializer(many=True))
    def get(self, request):
        query = ReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        with consistent_report_read():
            rows = participation_report(**query.validated_data)
        response = Response(rows)
        response["X-Report-Fingerprint"] = report_fingerprint(query.validated_data, rows)
        return response


class ParticipationExport(FederationMixin, APIView):
    serializer_class = AnnualReportSerializer

    @extend_schema(parameters=REPORT_PARAMETERS, responses={(200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes})
    def get(self, request):
        query = ReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        with consistent_report_read():
            rows = participation_report(**query.validated_data)
        fingerprint = report_fingerprint(query.validated_data, rows)
        response = HttpResponse(export_participation(rows, query.validated_data, fingerprint), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["X-Report-Fingerprint"] = fingerprint
        response["Content-Disposition"] = 'attachment; filename="participation.xlsx"'
        return response
