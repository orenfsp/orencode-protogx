from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalogs.models import Discipline
from apps.competitions.models import AgeGroup, Competition

from .models import (
    AthleteRating,
    AthleteRestriction,
    RatingContribution,
    RatingRuleVersion,
    RatingSeason,
)
from .serializers import (
    AthleteRatingSerializer,
    AthleteRestrictionSerializer,
    RatingRuleInputSerializer,
    RatingRuleSerializer,
    RatingSeasonSerializer,
)
from .services import (
    calculate_ratings,
    create_rule_version,
    require_federation,
    season_for_year,
)


def _rank_value(value):
    if not value:
        return None
    from apps.qualifications.models import SportRank
    return dict((item, index) for index, (item, _label) in enumerate(SportRank.choices)).get(value)


class RatingOptionsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=inline_serializer("RatingOptionsResponse", fields={"seasons": RatingSeasonSerializer(many=True), "disciplines": inline_serializer("RatingDisciplineOptions", fields={"id": serializers.IntegerField(), "code": serializers.CharField(), "name": serializers.CharField()}, many=True), "age_groups": inline_serializer("RatingAgeGroupOptions", fields={"id": serializers.IntegerField(), "name": serializers.CharField(), "min_age": serializers.IntegerField(), "max_age": serializers.IntegerField()}, many=True)}))
    def get(self, request):
        years = set(Competition.objects.values_list("starts_at__year", flat=True))
        years.add(timezone.localdate().year)
        for year in years:
            RatingSeason.objects.get_or_create(year=year, defaults={"name": f"Сезон {year}"})
        return Response({
            "seasons": RatingSeasonSerializer(RatingSeason.objects.filter(is_active=True), many=True).data,
            "disciplines": list(Discipline.objects.filter(is_active=True).values("id", "code", "name")),
            "age_groups": list(AgeGroup.objects.all().order_by("min_age").values("id", "name", "min_age", "max_age")),
        })


class RatingsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(parameters=[
        OpenApiParameter("season", OpenApiTypes.INT, OpenApiParameter.QUERY),
        OpenApiParameter("discipline", OpenApiTypes.STR, OpenApiParameter.QUERY),
        OpenApiParameter("age_group", OpenApiTypes.INT, OpenApiParameter.QUERY),
        OpenApiParameter("min_rank", OpenApiTypes.STR, OpenApiParameter.QUERY),
        OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY),
        OpenApiParameter("page_size", OpenApiTypes.INT, OpenApiParameter.QUERY),
    ], responses=inline_serializer("RatingsResponse", fields={"items": AthleteRatingSerializer(many=True), "page": serializers.IntegerField(), "page_size": serializers.IntegerField(), "total": serializers.IntegerField(), "pages": serializers.IntegerField()}))
    def get(self, request):
        try:
            season_year = int(request.query_params.get("season", 0) or 0)
        except (TypeError, ValueError):
            return Response({"season": ["Must be an integer"]}, status=400)
        discipline_value = request.query_params.get("discipline")
        queryset = AthleteRating.objects.select_related("athlete", "season", "discipline").prefetch_related(
            Prefetch("athlete__rating_contributions", queryset=RatingContribution.objects.filter(is_current=True).select_related("competition", "publication"), to_attr="_rating_contributions"),
        )
        if season_year:
            queryset = queryset.filter(season__year=season_year)
        if discipline_value:
            queryset = queryset.filter(discipline__code=discipline_value) if not discipline_value.isdigit() else queryset.filter(discipline_id=int(discipline_value))
        age_group = request.query_params.get("age_group")
        if age_group:
            age_names = AgeGroup.objects.filter(pk=age_group).values_list("name", flat=True)
            matching_contributions = RatingContribution.objects.filter(
                athlete_id=OuterRef("athlete_id"),
                season_id=OuterRef("season_id"),
                discipline_id=OuterRef("discipline_id"),
                is_current=True,
                age_group__in=age_names,
            )
            queryset = queryset.annotate(_has_age_group=Exists(matching_contributions)).filter(_has_age_group=True)
        min_rank = _rank_value(request.query_params.get("min_rank"))
        if min_rank is not None:
            from apps.qualifications.models import SportRankHistory
            allowed = []
            for item in queryset.values("athlete_id", "discipline_id").distinct():
                history = SportRankHistory.objects.filter(athlete_id=item["athlete_id"], discipline_id=item["discipline_id"]).order_by("-valid_until", "-assigned_on", "-pk").first()
                if history and _rank_value(history.rank) is not None and _rank_value(history.rank) >= min_rank:
                    allowed.append((item["athlete_id"], item["discipline_id"]))
            if allowed:
                pair_filter = Q()
                for athlete_id, discipline_id in allowed:
                    pair_filter |= Q(athlete_id=athlete_id, discipline_id=discipline_id)
                queryset = queryset.filter(pair_filter)
            else:
                queryset = queryset.none()
        queryset = queryset.order_by("-rating_score", "athlete__full_name", "athlete_id")
        page = max(int(request.query_params.get("page", 1) or 1), 1)
        page_size = min(max(int(request.query_params.get("page_size", 25) or 25), 1), 100)
        total = queryset.count()
        items = queryset[(page - 1) * page_size:page * page_size]
        data = AthleteRatingSerializer(items, many=True).data
        for index, row in enumerate(data, start=(page - 1) * page_size + 1):
            row["placement"] = index
        return Response({"items": data, "page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size})


class RatingRulesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=RatingRuleSerializer(many=True))
    def get(self, request):
        require_federation(request)
        return Response(RatingRuleSerializer(RatingRuleVersion.objects.select_related("season", "discipline").prefetch_related("point_rules"), many=True).data)

    @extend_schema(request=RatingRuleInputSerializer, responses=RatingRuleSerializer)
    @transaction.atomic
    def post(self, request):
        require_federation(request)
        serializer = RatingRuleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        season = data.pop("season")
        discipline = data.pop("discipline")
        rule = create_rule_version(actor=request.user, season=season, discipline=discipline, validated_data=data)
        return Response(RatingRuleSerializer(rule).data, status=201)


class RatingRecalculateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=inline_serializer("RatingRecalculateRequest", fields={"season": serializers.IntegerField(), "discipline": serializers.IntegerField()}), responses=inline_serializer("RatingRecalculateResponse", fields={"status": serializers.CharField(), "season": serializers.IntegerField(), "discipline": serializers.CharField()}))
    @transaction.atomic
    def post(self, request):
        require_federation(request)
        try:
            season = season_for_year(int(request.data.get("season")))
        except (TypeError, ValueError):
            return Response({"season": ["Season year is required"]}, status=400)
        discipline = get_object_or_404(Discipline, pk=request.data.get("discipline"))
        calculate_ratings(season=season, discipline=discipline, actor=request.user)
        return Response({"status": "calculated", "season": season.year, "discipline": discipline.code})


class RatingRestrictionsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=AthleteRestrictionSerializer(many=True))
    def get(self, request):
        require_federation(request)
        return Response(AthleteRestrictionSerializer(AthleteRestriction.objects.select_related("athlete"), many=True).data)

    @extend_schema(request=AthleteRestrictionSerializer, responses=AthleteRestrictionSerializer)
    @transaction.atomic
    def post(self, request):
        require_federation(request)
        serializer = AthleteRestrictionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        restriction = serializer.save(created_by=request.user)
        return Response(AthleteRestrictionSerializer(restriction).data, status=201)
