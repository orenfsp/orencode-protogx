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

from apps.accounts.models import User, UserRole
from apps.catalogs.models import Discipline, Organization
from apps.competitions.models import AgeGroup
from apps.competitions.services import audit
from apps.teams.services import require_federation

from .analytics import consistent_report_read, participation_report, report_fingerprint
from .exporters import export_participation
from .models import (
    DisciplinePeriod,
    MunicipalityPeriod,
    OrganizationPeriod,
    ParticipationPeriod,
    TrainingStagePeriod,
)
from .serializers import (
    AnnualReportSerializer,
    ClosePeriodSerializer,
    DisciplinePeriodSerializer,
    MunicipalityPeriodSerializer,
    OrganizationPeriodSerializer,
    OrganizationSerializer,
    ParticipationSerializer,
    PeriodCorrectionSerializer,
    PersonFilterSerializer,
    PersonSerializer,
    PersonUpdateSerializer,
    RegistryOptionsSerializer,
    ReportQuerySerializer,
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

    def get_queryset(self):
        query = PersonFilterSerializer(data=self.request.query_params.dict())
        query.is_valid(raise_exception=True)
        values = query.validated_data
        qs = User.objects.filter(role_assignments__role=self.role).select_related("athlete_profile__organization")
        if "active" in values:
            qs = qs.filter(is_active=values["active"])
        if "organization" in values:
            qs = qs.filter(athlete_profile__organization_id=values["organization"])
        today = timezone.localdate()
        if "discipline" in values:
            if self.role == UserRole.Role.ATHLETE:
                ids = DisciplinePeriod.objects.filter(discipline_id=values["discipline"], starts_on__lte=today).filter(Q(ends_on__isnull=True) | Q(ends_on__gte=today)).values("athlete_id")
                qs = qs.filter(pk__in=ids)
            elif self.role == UserRole.Role.COACH:
                qs = qs.filter(coached_links__discipline_id=values["discipline"], coached_links__status="confirmed")
            else:
                qs = qs.filter(judge_assignments__competition__discipline_id=values["discipline"])
        if "municipality" in values:
            ids = MunicipalityPeriod.objects.filter(municipality=values["municipality"], starts_on__lte=today).filter(Q(ends_on__isnull=True) | Q(ends_on__gte=today)).values("athlete_id")
            qs = qs.filter(pk__in=ids)
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


class PersonDetail(FederationMixin, generics.RetrieveUpdateAPIView):
    serializer_class = PersonSerializer
    http_method_names = ["get", "patch", "head", "options"]
    role = None

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
        return Response(PersonSerializer(user).data)

class AthleteDetail(PersonDetail):
    role = UserRole.Role.ATHLETE


class CoachDetail(PersonDetail):
    role = UserRole.Role.COACH


class JudgeDetail(PersonDetail):
    role = UserRole.Role.JUDGE


class Organizations(FederationMixin, generics.ListCreateAPIView):
    serializer_class = OrganizationSerializer
    pagination_class = RegistryPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "code", "municipality"]
    queryset = Organization.objects.order_by("name", "pk")

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
