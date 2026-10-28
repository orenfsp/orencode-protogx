from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
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
from apps.catalogs.models import Organization
from apps.competitions.services import audit
from apps.teams.services import require_federation

from .analytics import participation_report
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
    PersonSerializer,
    ReportQuerySerializer,
    TrainingStagePeriodSerializer,
    TransferSerializer,
)
from .services import add_period, close_period, transfer_organization


class RegistryPagination(PageNumberPagination):
    page_size = 50


class FederationMixin:
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        require_federation(request)


class PeopleList(FederationMixin, generics.ListAPIView):
    serializer_class = PersonSerializer
    pagination_class = RegistryPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["full_name"]
    role = None

    def get_queryset(self):
        return User.objects.filter(role_assignments__role=self.role).select_related("athlete_profile__organization").order_by("full_name", "pk")


class AthletesList(PeopleList):
    role = UserRole.Role.ATHLETE


class CoachesList(PeopleList):
    role = UserRole.Role.COACH


class JudgesList(PeopleList):
    role = UserRole.Role.JUDGE


class PersonDetail(FederationMixin, generics.RetrieveAPIView):
    serializer_class = PersonSerializer
    role = None

    def get_queryset(self):
        return User.objects.filter(role_assignments__role=self.role).select_related("athlete_profile__organization")


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


REPORT_PARAMETERS = [OpenApiParameter(name, typ, required=name in ("start_year", "end_year")) for name, typ in (("start_year", int), ("end_year", int), ("organization", int), ("discipline", int), ("municipality", str), ("age_group", int))]


class ParticipationReport(FederationMixin, APIView):
    serializer_class = AnnualReportSerializer

    @extend_schema(parameters=REPORT_PARAMETERS, responses=AnnualReportSerializer(many=True))
    def get(self, request):
        query = ReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        return Response(participation_report(**query.validated_data))


class ParticipationExport(FederationMixin, APIView):
    serializer_class = AnnualReportSerializer

    @extend_schema(parameters=REPORT_PARAMETERS, responses={(200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): bytes})
    def get(self, request):
        query = ReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        rows = participation_report(**query.validated_data)
        response = HttpResponse(export_participation(rows, query.validated_data), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="participation.xlsx"'
        return response
