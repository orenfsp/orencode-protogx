from django.db.models import Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.competitions.models import CoachAthleteLink, Result
from apps.competitions.services import require_role

from .models import (
    JudgeCategory,
    JudgeCategoryApplication,
    JudgeCategoryHistory,
    QualificationRule,
    RankApplication,
    RequestType,
    ReviewStatus,
    SportRank,
    SportRankHistory,
)
from .serializers import (
    CategoryApplicationCreateSerializer,
    DecisionInputSerializer,
    JudgeCategoryApplicationSerializer,
    JudgeCategoryHistorySerializer,
    QualificationRuleSerializer,
    RankApplicationCreateSerializer,
    RankApplicationSerializer,
    SportRankHistorySerializer,
)
from .services import (
    HINT_DISCLAIMER,
    active_rules,
    category_level,
    create_category_application,
    create_rank_application,
    days_left,
    decide_category_application,
    decide_rank_application,
    hint_for,
    most_significant,
    rank_level,
    validity_state,
)

RESULT_LIMIT = 300


def coach_scope(user, athlete_field, discipline_field):
    """Q по подтверждённым связям тренера: пара (спортсмен, дисциплина) должна совпасть."""
    scope = Q(pk__in=[])
    links = CoachAthleteLink.objects.filter(coach=user, status="confirmed").values_list("athlete_id", "discipline_id")
    for athlete_id, discipline_id in links:
        scope |= Q(**{athlete_field: athlete_id, discipline_field: discipline_id})
    return scope


def int_param(request, name):
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except ValueError:
        raise ValidationError({name: "Ожидается целое число"})


class OptionsView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        require_role(request, "federation", "athlete", "coach", "judge")
        as_options = lambda choices: [{"value": value, "label": label} for value, label in choices]  # noqa: E731
        return Response({"ranks": as_options(SportRank.choices), "categories": as_options(JudgeCategory.choices), "request_types": as_options(RequestType.choices), "hint_disclaimer": HINT_DISCLAIMER})


class QualificationRulesView(APIView):
    @extend_schema(responses=QualificationRuleSerializer(many=True))
    def get(self, request):
        require_role(request, "federation")
        return Response(QualificationRuleSerializer(QualificationRule.objects.select_related("discipline"), many=True).data)


class RankResultsView(APIView):
    """Результаты, на основании которых можно подать заявку, с предварительной подсказкой по правилам."""

    @extend_schema(parameters=[OpenApiParameter("hinted", OpenApiTypes.BOOL)], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        role = require_role(request, "federation", "athlete", "coach")
        queryset = Result.objects.filter(
            status=Result.Status.CLASSIFIED, validated_by__isnull=False, application__competition__protocols__isnull=False,
        ).select_related("application__athlete", "application__competition__discipline")
        if role == "athlete":
            queryset = queryset.filter(application__athlete=request.user)
        elif role == "coach":
            queryset = queryset.filter(coach_scope(request.user, "application__athlete_id", "application__competition__discipline_id"))
        results = list(queryset.distinct().order_by("-id")[:RESULT_LIMIT])

        rules = active_rules()
        athlete_ids = {r.application.athlete_id for r in results}
        history = {}
        for record in SportRankHistory.objects.filter(athlete_id__in=athlete_ids):
            history.setdefault(record.athlete_id, []).append(record)
        pending = {}
        for app in RankApplication.objects.filter(result__in=results, status=ReviewStatus.PENDING):
            pending.setdefault(app.result_id, []).append(app.requested_rank)

        rows = []
        for result in results:
            app = result.application
            rule = hint_for(result, rules)
            if request.query_params.get("hinted") in ("1", "true") and rule is None:
                continue
            current = most_significant(history.get(app.athlete_id, []), rank_level)
            rows.append({
                "result": result.pk, "athlete": app.athlete_id, "athlete_name": app.athlete.full_name,
                "competition": app.competition_id, "competition_title": app.competition.title, "competition_level": app.competition.level,
                "discipline": app.competition.discipline_id, "discipline_name": app.competition.discipline.name,
                "place": result.place, "score": str(result.score) if result.score is not None else None,
                "current_rank": current.rank if current else None,
                "current_rank_label": current.get_rank_display() if current else None,
                "pending_ranks": pending.get(result.pk, []),
                "hint": None if rule is None else {
                    "rank": rule.rank, "rank_label": rule.get_rank_display(), "rule_version": rule.rule_version,
                    "source_verified": rule.source_verified, "disclaimer": HINT_DISCLAIMER,
                },
            })
        return Response(rows)


class RankApplicationsView(APIView):
    @extend_schema(parameters=[OpenApiParameter("status", str)], responses=RankApplicationSerializer(many=True))
    def get(self, request):
        role = require_role(request, "federation", "athlete", "coach")
        queryset = RankApplication.objects.select_related("athlete", "submitted_by", "discipline", "competition", "result", "rank_record")
        if role == "athlete":
            queryset = queryset.filter(athlete=request.user)
        elif role == "coach":
            queryset = queryset.filter(coach_scope(request.user, "athlete_id", "discipline_id") | Q(submitted_by=request.user))
        status = request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)
        return Response(RankApplicationSerializer(queryset.distinct(), many=True).data)

    @extend_schema(request=RankApplicationCreateSerializer, responses={201: RankApplicationSerializer})
    def post(self, request):
        role = require_role(request, "athlete", "coach")
        serializer = RankApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = create_rank_application(request.user, role, serializer.validated_data)
        return Response(RankApplicationSerializer(application).data, status=201)


class RankApplicationDecisionView(APIView):
    @extend_schema(request=DecisionInputSerializer, responses=RankApplicationSerializer)
    def post(self, request, pk):
        require_role(request, "federation")
        serializer = DecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = decide_rank_application(pk, request.user, serializer.validated_data)
        if application is None:
            raise NotFound("Заявка не найдена")
        application = RankApplication.objects.select_related("athlete", "submitted_by", "discipline", "competition", "result", "rank_record").get(pk=application.pk)
        return Response(RankApplicationSerializer(application).data)


class RankHistoryView(APIView):
    @extend_schema(parameters=[OpenApiParameter("athlete", int)], responses=SportRankHistorySerializer(many=True))
    def get(self, request):
        role = require_role(request, "federation", "athlete", "coach")
        queryset = SportRankHistory.objects.select_related("athlete", "discipline", "application__competition", "application__result")
        if role == "athlete":
            queryset = queryset.filter(athlete=request.user)
        elif role == "coach":
            queryset = queryset.filter(coach_scope(request.user, "athlete_id", "discipline_id"))
        athlete = int_param(request, "athlete")
        if athlete is not None:
            queryset = queryset.filter(athlete_id=athlete)
        return Response(SportRankHistorySerializer(queryset, many=True).data)


class CategoryApplicationsView(APIView):
    @extend_schema(parameters=[OpenApiParameter("status", str)], responses=JudgeCategoryApplicationSerializer(many=True))
    def get(self, request):
        role = require_role(request, "federation", "judge")
        queryset = JudgeCategoryApplication.objects.select_related("judge", "category_record")
        if role == "judge":
            queryset = queryset.filter(judge=request.user)
        status = request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)
        return Response(JudgeCategoryApplicationSerializer(queryset, many=True).data)

    @extend_schema(request=CategoryApplicationCreateSerializer, responses={201: JudgeCategoryApplicationSerializer})
    def post(self, request):
        require_role(request, "judge")
        serializer = CategoryApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = create_category_application(request.user, serializer.validated_data)
        return Response(JudgeCategoryApplicationSerializer(application).data, status=201)


class CategoryApplicationDecisionView(APIView):
    @extend_schema(request=DecisionInputSerializer, responses=JudgeCategoryApplicationSerializer)
    def post(self, request, pk):
        require_role(request, "federation")
        serializer = DecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = decide_category_application(pk, request.user, serializer.validated_data)
        if application is None:
            raise NotFound("Заявка не найдена")
        application = JudgeCategoryApplication.objects.select_related("judge", "category_record").get(pk=application.pk)
        return Response(JudgeCategoryApplicationSerializer(application).data)


class CategoryHistoryView(APIView):
    @extend_schema(responses=JudgeCategoryHistorySerializer(many=True))
    def get(self, request):
        role = require_role(request, "federation", "judge")
        queryset = JudgeCategoryHistory.objects.select_related("judge")
        if role == "judge":
            queryset = queryset.filter(judge=request.user)
        return Response(JudgeCategoryHistorySerializer(queryset, many=True).data)


class DeadlinesView(APIView):
    """Контроль сроков: разряды и категории, которые истекают в ближайшие N дней или уже истекли.

    Для каждого человека учитывается его «текущая» запись (см. services.most_significant),
    поэтому заменённая более новой запись не вызывает ложного предупреждения.
    """

    @extend_schema(parameters=[OpenApiParameter("days", int)], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        role = require_role(request, "federation", "athlete", "coach", "judge")
        days = int_param(request, "days")
        days = 60 if days is None else days
        if not 0 <= days <= 365:
            raise ValidationError({"days": "Допустимо от 0 до 365"})
        today = timezone.localdate()
        items = []

        def collect(records, level, kind, person_field, label_of):
            grouped = {}
            for record in records:
                grouped.setdefault(getattr(record, person_field + "_id"), []).append(record)
            for rows in grouped.values():
                current = most_significant(rows, level)
                left = days_left(current.valid_until, today)
                if left <= days:
                    person = getattr(current, person_field)
                    items.append({"kind": kind, "person": person.pk, "person_name": person.full_name, "label": label_of(current),
                                  "valid_until": current.valid_until.isoformat(), "days_left": left, "validity": validity_state(current.valid_until, today)})

        if role in ("federation", "athlete", "coach"):
            ranks = SportRankHistory.objects.select_related("athlete")
            if role == "athlete":
                ranks = ranks.filter(athlete=request.user)
            elif role == "coach":
                ranks = ranks.filter(coach_scope(request.user, "athlete_id", "discipline_id"))
            collect(ranks, rank_level, "rank", "athlete", lambda r: r.get_rank_display())
        if role in ("federation", "judge"):
            categories = JudgeCategoryHistory.objects.select_related("judge")
            if role == "judge":
                categories = categories.filter(judge=request.user)
            collect(categories, category_level, "judge_category", "judge", lambda r: r.get_category_display())
        items.sort(key=lambda item: (item["days_left"], item["person_name"]))
        return Response({"days": days, "items": items})
