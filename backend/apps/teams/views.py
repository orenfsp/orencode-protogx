from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalogs.models import Discipline
from apps.competitions.models import AgeGroup, AuditEvent
from apps.ratings.models import RatingSeason

from .exporters import render_team_docx, render_team_pdf
from .models import RegionalTeam, TeamDecisionHistory, TeamMembership
from .serializers import (
    MemberAddSerializer,
    MemberRemoveSerializer,
    RegionalTeamSerializer,
    ReorderSerializer,
    TeamCandidateSerializer,
    TeamCreateSerializer,
    TeamDocumentResponseSerializer,
    TeamHistorySerializer,
    TeamMembershipSerializer,
)
from .services import (
    add_member,
    candidate_rows,
    create_team,
    publish_team,
    remove_member,
    reorder_members,
    require_federation,
)


class TeamOptionsView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RegionalTeamSerializer

    def get(self, request):
        require_federation(request)
        return Response({"seasons": list(RatingSeason.objects.filter(is_active=True).values("id", "year", "name")), "disciplines": list(Discipline.objects.filter(is_active=True).values("id", "code", "name")), "age_groups": list(AgeGroup.objects.values("id", "name", "min_age", "max_age"))})


class TeamsView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RegionalTeamSerializer

    @extend_schema(responses=RegionalTeamSerializer(many=True))
    def get(self, request):
        require_federation(request)
        qs = RegionalTeam.objects.select_related("season", "discipline", "age_group", "created_by").prefetch_related("memberships__athlete")
        if request.query_params.get("season"):
            qs = qs.filter(season__year=request.query_params["season"])
        if request.query_params.get("discipline"):
            value = request.query_params["discipline"]
            qs = qs.filter(discipline__code=value) if not value.isdigit() else qs.filter(discipline_id=value)
        if request.query_params.get("age_group"):
            qs = qs.filter(age_group_id=request.query_params["age_group"])
        return Response(RegionalTeamSerializer(qs, many=True).data)

    @extend_schema(request=TeamCreateSerializer, responses=RegionalTeamSerializer)
    @transaction.atomic
    def post(self, request):
        require_federation(request)
        serializer = TeamCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = create_team(actor=request.user, validated_data=serializer.validated_data)
        return Response(RegionalTeamSerializer(team).data, status=201)


class TeamDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RegionalTeamSerializer

    def get_team(self, request, pk):
        require_federation(request)
        return get_object_or_404(RegionalTeam.objects.select_related("season", "discipline", "age_group", "created_by").prefetch_related("memberships__athlete"), pk=pk)

    def get(self, request, pk):
        return Response(RegionalTeamSerializer(self.get_team(request, pk)).data)


class TeamCandidatesView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TeamCandidateSerializer

    def get(self, request, pk):
        team = TeamDetailView().get_team(request, pk)
        return Response(TeamCandidateSerializer(candidate_rows(team), many=True).data)


class TeamMembersView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RegionalTeamSerializer

    def get_team(self, request, pk):
        return TeamDetailView().get_team(request, pk)

    @extend_schema(request=MemberAddSerializer, responses=RegionalTeamSerializer)
    @transaction.atomic
    def post(self, request, pk):
        team = self.get_team(request, pk)
        serializer = MemberAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        add_member(actor=request.user, team=team, athlete=serializer.validated_data["athlete"], note=serializer.validated_data.get("note", ""))
        return Response(RegionalTeamSerializer(team).data, status=201)


class TeamMemberRemoveView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RegionalTeamSerializer

    @transaction.atomic
    def post(self, request, pk, membership_id):
        require_federation(request)
        membership = get_object_or_404(TeamMembership.objects.select_related("team"), pk=membership_id, team_id=pk)
        serializer = MemberRemoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        remove_member(actor=request.user, membership=membership, reason=serializer.validated_data.get("reason", ""))
        return Response(RegionalTeamSerializer(RegionalTeam.objects.get(pk=pk)).data)


class TeamReorderView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TeamMembershipSerializer

    @transaction.atomic
    def post(self, request, pk):
        require_federation(request)
        team = get_object_or_404(RegionalTeam, pk=pk)
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        memberships = reorder_members(actor=request.user, team=team, member_ids=serializer.validated_data["member_ids"])
        return Response(TeamMembershipSerializer(memberships, many=True).data)


class TeamHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TeamHistorySerializer

    def get(self, request, pk):
        require_federation(request)
        get_object_or_404(RegionalTeam, pk=pk)
        return Response(TeamHistorySerializer(TeamDecisionHistory.objects.filter(team_id=pk).select_related("actor"), many=True).data)


class TeamPublishView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RegionalTeamSerializer

    @transaction.atomic
    def post(self, request, pk):
        require_federation(request)
        team = get_object_or_404(RegionalTeam, pk=pk)
        return Response(RegionalTeamSerializer(publish_team(actor=request.user, team=team)).data)


class TeamDocumentsView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TeamDocumentResponseSerializer

    def get(self, request, pk):
        team = TeamDetailView().get_team(request, pk)
        kind = request.query_params.get("type", "roster")
        # `format` is reserved by DRF content negotiation; use document_format for DOCX/PDF.
        fmt = request.query_params.get("document_format", request.query_params.get("format", "pdf"))
        draft = kind in {"draft", "draft-order"}
        if kind not in {"roster", "draft", "draft-order"} or fmt not in {"pdf", "docx"}:
            return Response({"detail": "type must be roster or draft-order; format must be pdf or docx"}, status=400)
        payload = render_team_pdf(team, draft=draft) if fmt == "pdf" else render_team_docx(team, draft=draft)
        AuditEvent.objects.create(
            actor=request.user,
            action="regional_team.document_generated",
            target_type=team._meta.model_name,
            target_id=team.pk,
            after={"active_role": "federation", "type": "draft-order" if draft else "roster", "format": fmt},
        )
        content_type = "application/pdf" if fmt == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"regional-team-{team.pk}-{'draft-order' if draft else 'roster'}.{fmt}"
        response = HttpResponse(payload, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
