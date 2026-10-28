from django.db import IntegrityError, models, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User, UserRole

from .exporters import render_protocol_docx, render_protocol_pdf
from .models import (
    AgeGroup,
    Application,
    CalendarEntry,
    CoachAthleteLink,
    Competition,
    JudgeAssignment,
    ProtocolPublication,
    ProtocolTemplate,
    Result,
)
from .serializers import (
    AgeGroupSerializer,
    ApplicationSerializer,
    AthleteHistorySerializer,
    CalendarEntrySerializer,
    CoachLinkDecisionSerializer,
    CoachLinkRequestSerializer,
    CoachLinkSerializer,
    CompetitionSerializer,
    DecisionSerializer,
    JudgeAssignmentSerializer,
    ProtocolPublicationSerializer,
    ProtocolPublishRequestSerializer,
    ProtocolSnapshotSerializer,
    ProtocolTemplateSerializer,
    ResultSerializer,
    UserChoiceSerializer,
)
from .services import (
    age_on,
    audit,
    check_application_eligibility,
    protocol_snapshot,
    publish_protocol,
    require_role,
    validate_result_data,
    validate_template_definition,
)


class AgeGroupsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=AgeGroupSerializer(many=True))
    def get(self, request):
        return Response(AgeGroupSerializer(AgeGroup.objects.all().order_by("min_age"), many=True).data)

    @extend_schema(request=AgeGroupSerializer, responses={201: AgeGroupSerializer})
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation")
        serializer = AgeGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data["min_age"] > serializer.validated_data["max_age"]:
            raise ValidationError("Minimum age cannot exceed maximum age")
        group = serializer.save()
        audit(request.user, "age_group.created", group, after=serializer.data)
        return Response(serializer.data, status=201)


class CalendarEntriesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=CalendarEntrySerializer(many=True))
    def get(self, request):
        return Response(CalendarEntrySerializer(CalendarEntry.objects.all().order_by("-year", "entry_number"), many=True).data)

    @extend_schema(request=CalendarEntrySerializer, responses={201: CalendarEntrySerializer})
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation")
        serializer = CalendarEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = serializer.save()
        audit(request.user, "calendar.created", entry, after=serializer.data)
        return Response(serializer.data, status=201)


class TemplatesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=ProtocolTemplateSerializer(many=True))
    def get(self, request):
        queryset = ProtocolTemplate.objects.select_related("discipline").all()
        if request.query_params.get("discipline"):
            queryset = queryset.filter(discipline__code=request.query_params["discipline"])
        return Response(ProtocolTemplateSerializer(queryset, many=True).data)

    @extend_schema(request=ProtocolTemplateSerializer, responses={201: ProtocolTemplateSerializer})
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation")
        serializer = ProtocolTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        sections = data.get("sections", ["header", "participants", "judges", "signatures"])
        signatures = data.get("signature_roles", ["Главный судья", "Секретарь"])
        sort = data.get("sort", {"key": "place" if "place" in data["columns"] else "athlete", "direction": "asc"})
        validate_template_definition(data["metric_fields"], data["columns"], sections, signatures, sort)
        last = ProtocolTemplate.objects.select_for_update().filter(discipline=data["discipline"]).order_by("-version").first()
        template = serializer.save(version=(last.version if last else 0) + 1, source_verified=False, sections=sections, signature_roles=signatures, sort=sort)
        audit(request.user, "template.created", template, after={"version": template.version})
        return Response(ProtocolTemplateSerializer(template).data, status=201)


class CompetitionsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(parameters=[OpenApiParameter("discipline", str), OpenApiParameter("age_group", int), OpenApiParameter("eligible_age", bool)], responses=CompetitionSerializer(many=True))
    def get(self, request):
        queryset = Competition.objects.select_related("discipline", "template").prefetch_related("age_groups", "stages")
        if not request.user.is_authenticated or request.session.get("active_role") != "federation" or not request.user.role_assignments.filter(role="federation").exists():
            queryset = queryset.filter(state__in=["published", "closed"])
        if request.query_params.get("discipline"):
            queryset = queryset.filter(discipline__code=request.query_params["discipline"])
        if request.query_params.get("age_group"):
            try:
                group = int(request.query_params["age_group"])
            except ValueError as error:
                raise ValidationError("Некорректная возрастная группа") from error
            queryset = queryset.filter(age_groups=group)
        if request.query_params.get("eligible_age") == "true":
            require_role(request, "athlete")
            if request.user.date_of_birth is None:
                raise ValidationError("Укажите дату рождения для подбора по возрасту")
            queryset = [competition for competition in queryset.order_by("starts_at") if any(
                group.min_age <= age_on(request.user.date_of_birth, competition.age_reference_date or competition.starts_at.date()) <= group.max_age
                for group in competition.age_groups.all()
            )]
            return Response(CompetitionSerializer(queryset, many=True).data)
        return Response(CompetitionSerializer(queryset.order_by("starts_at"), many=True).data)

    @extend_schema(request=CompetitionSerializer, responses={201: CompetitionSerializer})
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation")
        serializer = CompetitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        competition = serializer.save(created_by=request.user)
        from .models import CompetitionType
        CompetitionType.objects.get_or_create(name=competition.competition_type)
        audit(request.user, "competition.created", competition, competition=competition, after=CompetitionSerializer(competition).data)
        return Response(CompetitionSerializer(competition).data, status=201)


class CompetitionDetailView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, request, pk):
        competition = get_object_or_404(Competition.objects.select_related("discipline", "template").prefetch_related("age_groups", "stages"), pk=pk)
        is_federation = request.user.is_authenticated and request.session.get("active_role") == "federation" and request.user.role_assignments.filter(role="federation").exists()
        if competition.state == "draft" and not is_federation:
            raise PermissionDenied("Draft competition")
        return competition

    @extend_schema(responses=CompetitionSerializer)
    def get(self, request, pk):
        return Response(CompetitionSerializer(self.get_object(request, pk)).data)

    @extend_schema(request=CompetitionSerializer, responses=CompetitionSerializer)
    @transaction.atomic
    def patch(self, request, pk):
        require_role(request, "federation")
        competition = self.get_object(request, pk)
        if competition.protocols.exists():
            raise ValidationError("Competition setup is frozen after protocol publication")
        before = CompetitionSerializer(competition).data
        serializer = CompetitionSerializer(competition, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if competition.applications.exists():
            data = serializer.validated_data
            frozen = {
                "discipline": competition.discipline,
                "template": competition.template,
                "starts_at": competition.starts_at,
                "ends_at": competition.ends_at,
                "registration_deadline": competition.registration_deadline,
                "age_reference_date": competition.age_reference_date,
                "allow_ties": competition.allow_ties,
                "format": competition.format,
            }
            if any(key in data and data[key] != value for key, value in frozen.items()):
                raise ValidationError("Competition eligibility and template are frozen after the first application")
            if "age_groups" in data and {group.pk for group in data["age_groups"]} != set(competition.age_groups.values_list("pk", flat=True)):
                raise ValidationError("Age groups are frozen after the first application")
            if "stages" in data:
                current_stages = list(competition.stages.values("order", "name", "format", "starts_at", "ends_at"))
                if [dict(stage) for stage in data["stages"]] != current_stages:
                    raise ValidationError("Stages are frozen after the first application")
        competition = serializer.save()
        audit(request.user, "competition.updated", competition, competition=competition, before=before, after=serializer.data)
        return Response(serializer.data)


class CompetitionPublishView(APIView):
    @extend_schema(request=None, responses=CompetitionSerializer)
    @transaction.atomic
    def post(self, request, pk):
        require_role(request, "federation")
        competition = get_object_or_404(Competition.objects.select_for_update(), pk=pk)
        if competition.state != "draft":
            raise ValidationError("Only a draft can be published")
        if competition.registration_deadline <= timezone.now():
            raise ValidationError("Registration deadline must be in the future")
        competition.state = "published"
        competition.save(update_fields=["state", "updated_at"])
        audit(request.user, "competition.published", competition, competition=competition, before={"state": "draft"}, after={"state": "published"})
        return Response(CompetitionSerializer(competition).data)


class ApplicationsView(APIView):
    @extend_schema(responses=ApplicationSerializer(many=True))
    def get(self, request):
        role = require_role(request, "federation", "athlete", "coach", "judge")
        queryset = Application.objects.select_related("athlete", "competition", "age_group")
        if role == "athlete":
            queryset = queryset.filter(athlete=request.user)
        elif role == "coach":
            queryset = queryset.filter(athlete__coach_links__coach=request.user, athlete__coach_links__status="confirmed", athlete__coach_links__discipline=models.F("competition__discipline"))
        elif role == "judge":
            queryset = queryset.filter(competition__judge_assignments__judge=request.user, status="approved")
        if request.query_params.get("competition"):
            queryset = queryset.filter(competition_id=request.query_params["competition"])
        return Response(ApplicationSerializer(queryset.order_by("-submitted_at").distinct(), many=True).data)

    @extend_schema(request=ApplicationSerializer, responses={201: ApplicationSerializer})
    @transaction.atomic
    def post(self, request):
        role = require_role(request, "athlete", "coach")
        serializer = ApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        competition = serializer.validated_data["competition"]
        athlete = serializer.validated_data["athlete"]
        if role == "athlete" and athlete.pk != request.user.pk:
            raise PermissionDenied("Athletes can only apply for themselves")
        check_application_eligibility(competition, athlete, serializer.validated_data["age_group"], request.user)
        try:
            application = serializer.save(submitted_by=request.user)
        except IntegrityError as error:
            raise ValidationError("Application already exists") from error
        audit(request.user, "application.submitted", application, competition=competition, after={"athlete_id": athlete.pk, "status": application.status})
        return Response(ApplicationSerializer(application).data, status=201)


class ApplicationDecisionView(APIView):
    @extend_schema(request=DecisionSerializer, responses=ApplicationSerializer)
    @transaction.atomic
    def post(self, request, pk):
        require_role(request, "federation")
        application = get_object_or_404(Application.objects.select_for_update(), pk=pk)
        if application.status != "pending":
            raise ValidationError("Only pending applications can be decided")
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data
        if decision["status"] == "rejected" and not decision.get("reason"):
            raise ValidationError("Rejection reason is required")
        application.status = decision["status"]
        application.decision_reason = decision.get("reason", "")
        application.decided_by = request.user
        application.decided_at = timezone.now()
        application.save()
        audit(request.user, "application.decided", application, competition=application.competition, before={"status": "pending"}, after={"status": application.status, "reason": application.decision_reason})
        return Response(ApplicationSerializer(application).data)


class JudgeAssignmentsView(APIView):
    @extend_schema(responses=JudgeAssignmentSerializer(many=True))
    def get(self, request):
        role = require_role(request, "federation", "judge")
        queryset = JudgeAssignment.objects.select_related("judge", "competition")
        if role == "judge":
            queryset = queryset.filter(judge=request.user)
        if request.query_params.get("competition"):
            queryset = queryset.filter(competition_id=request.query_params["competition"])
        return Response(JudgeAssignmentSerializer(queryset.order_by("-assigned_at"), many=True).data)

    @extend_schema(request=JudgeAssignmentSerializer, responses={201: JudgeAssignmentSerializer})
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation")
        serializer = JudgeAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        judge = serializer.validated_data["judge"]
        if not judge.role_assignments.filter(role="judge").exists():
            raise ValidationError("Assigned user must be a judge")
        if JudgeAssignment.objects.filter(competition=serializer.validated_data["competition"], judge=judge).exists():
            raise ValidationError("Judge is already assigned")
        assignment = serializer.save(assigned_by=request.user)
        audit(request.user, "judge.assigned", assignment, competition=assignment.competition, after={"judge_id": judge.pk})
        return Response(JudgeAssignmentSerializer(assignment).data, status=201)


class ResultsView(APIView):
    @extend_schema(responses=ResultSerializer(many=True))
    def get(self, request):
        role = require_role(request, "federation", "judge")
        queryset = Result.objects.select_related("application__competition")
        if role == "judge":
            queryset = queryset.filter(application__competition__judge_assignments__judge=request.user)
        if request.query_params.get("competition"):
            queryset = queryset.filter(application__competition_id=request.query_params["competition"])
        return Response(ResultSerializer(queryset.distinct(), many=True).data)

    @extend_schema(request=ResultSerializer, responses={201: ResultSerializer})
    @transaction.atomic
    def post(self, request):
        role = require_role(request, "federation", "judge")
        serializer = ResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        application = data["application"]
        Competition.objects.select_for_update().get(pk=application.competition_id)
        application = Application.objects.select_for_update().select_related("competition__template").get(pk=application.pk)
        if role == "judge" and not JudgeAssignment.objects.filter(competition=application.competition, judge=request.user).exists():
            raise PermissionDenied("Judge is not assigned to this competition")
        if application.competition.state != "published":
            raise ValidationError("Competition must be published")
        validate_result_data(application, data["status"], data.get("place"), data.get("score"), data.get("metrics", {}))
        result = Result.objects.select_for_update().filter(application=application).first()
        before = ResultSerializer(result).data if result else {}
        if result:
            for field in ("status", "place", "score", "metrics"):
                setattr(result, field, data.get(field, {} if field == "metrics" else None))
            result.updated_by = request.user
            result.validated_by = None
            result.save()
            created = False
        else:
            result = Result.objects.create(**data, updated_by=request.user)
            created = True
        audit(request.user, "result.entered" if created else "result.corrected", result, competition=application.competition, before=before, after=ResultSerializer(result).data)
        return Response(ResultSerializer(result).data, status=201 if created else 200)


class ResultValidateView(APIView):
    @extend_schema(request=None, responses=ResultSerializer)
    @transaction.atomic
    def post(self, request, pk):
        require_role(request, "federation")
        result = get_object_or_404(Result.objects.select_for_update().select_related("application__competition"), pk=pk)
        if result.validated_by_id:
            raise ValidationError("Result is already validated")
        result.validated_by = request.user
        result.save(update_fields=["validated_by", "updated_at"])
        audit(request.user, "result.validated", result, competition=result.application.competition, after={"validated_by": request.user.pk})
        return Response(ResultSerializer(result).data)


class ProtocolPreviewView(APIView):
    @extend_schema(responses=ProtocolSnapshotSerializer)
    def get(self, request, pk):
        require_role(request, "federation")
        competition = get_object_or_404(Competition.objects.select_related("template", "discipline"), pk=pk)
        return Response(protocol_snapshot(competition))


class ProtocolPublishView(APIView):
    @extend_schema(request=ProtocolPublishRequestSerializer, responses={201: ProtocolPublicationSerializer})
    def post(self, request, pk):
        require_role(request, "federation")
        competition = get_object_or_404(Competition, pk=pk)
        serializer = ProtocolPublishRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        publication = publish_protocol(competition, request.user, serializer.validated_data.get("correction_reason", ""))
        return Response(ProtocolPublicationSerializer(publication).data, status=201)


class ProtocolsView(APIView):
    @extend_schema(responses=ProtocolPublicationSerializer(many=True))
    def get(self, request, pk):
        require_role(request, "federation")
        return Response(ProtocolPublicationSerializer(ProtocolPublication.objects.filter(competition_id=pk), many=True).data)


class ProtocolDownloadView(APIView):
    @extend_schema(
        parameters=[OpenApiParameter(name="file_format", type=str, location=OpenApiParameter.QUERY, enum=["pdf", "docx"], required=True)],
        responses={(200, "application/pdf"): OpenApiTypes.BINARY, (200, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"): OpenApiTypes.BINARY},
    )
    def get(self, request, pk, version):
        require_role(request, "federation")
        publication = get_object_or_404(ProtocolPublication, competition_id=pk, version=version)
        output_format = request.query_params.get("file_format")
        if output_format == "pdf":
            content = render_protocol_pdf(publication)
            content_type = "application/pdf"
        elif output_format == "docx":
            content = render_protocol_docx(publication)
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            raise ValidationError("file_format must be pdf or docx")
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="protocol-{pk}-v{version}.{output_format}"'
        response["Cache-Control"] = "private, no-store"
        return response


class AthleteHistoryView(APIView):
    @extend_schema(responses=AthleteHistorySerializer(many=True))
    def get(self, request):
        require_role(request, "athlete")
        publications = ProtocolPublication.objects.filter(
            competition__applications__athlete=request.user,
            competition__applications__status="approved",
        ).select_related("competition").distinct().order_by("competition_id", "-version")
        latest = {}
        for publication in publications:
            latest.setdefault(publication.competition_id, publication)
        history = []
        for publication in latest.values():
            for row in publication.snapshot["rows"]:
                if row["athlete_id"] == request.user.pk:
                    history.append({"competition_id": publication.competition_id, "competition_title": publication.snapshot["competition_title"], "version": publication.version, "published_at": publication.published_at, "row": row})
        return Response(history)


class CoachLinksView(APIView):
    @extend_schema(responses=CoachLinkSerializer(many=True))
    def get(self, request):
        role = require_role(request, "coach", "athlete")
        queryset = CoachAthleteLink.objects.select_related("coach", "athlete", "discipline")
        queryset = queryset.filter(coach=request.user) if role == "coach" else queryset.filter(athlete=request.user)
        return Response(CoachLinkSerializer(queryset, many=True, context={"request": request}).data)

    @extend_schema(request=CoachLinkRequestSerializer, responses={202: None})
    @transaction.atomic
    def post(self, request):
        require_role(request, "coach")
        serializer = CoachLinkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        athlete = User.objects.filter(email__iexact=serializer.validated_data["athlete_email"], role_assignments__role=UserRole.Role.ATHLETE).first()
        if athlete and not CoachAthleteLink.objects.filter(coach=request.user, athlete=athlete, discipline=serializer.validated_data["discipline"]).exists():
            link = CoachAthleteLink.objects.create(coach=request.user, athlete=athlete, discipline=serializer.validated_data["discipline"])
            audit(request.user, "coach_link.requested", link, after={"discipline_id": link.discipline_id})
        return Response({"detail": "If the athlete account exists, the request is available for confirmation"}, status=202)


class CoachLinkDecisionView(APIView):
    @extend_schema(request=CoachLinkDecisionSerializer, responses=CoachLinkSerializer)
    @transaction.atomic
    def post(self, request, pk):
        require_role(request, "athlete")
        link = get_object_or_404(CoachAthleteLink.objects.select_for_update(), pk=pk, athlete=request.user)
        if link.status != "pending" or request.data.get("status") not in ("confirmed", "rejected"):
            raise ValidationError("Pending link requires confirmed or rejected status")
        link.status = request.data["status"]
        link.save(update_fields=["status"])
        audit(request.user, "coach_link.decided", link, after={"status": link.status})
        return Response(CoachLinkSerializer(link, context={"request": request}).data)


class JudgeChoicesView(APIView):
    @extend_schema(responses=UserChoiceSerializer(many=True))
    def get(self, request):
        require_role(request, "federation")
        queryset = User.objects.filter(role_assignments__role=UserRole.Role.JUDGE).order_by("full_name")
        return Response(UserChoiceSerializer(queryset, many=True).data)
