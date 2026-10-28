from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import (
    AthleteRating,
    AthleteRestriction,
    RatingPointRule,
    RatingRuleVersion,
    RatingSeason,
)


class RatingSeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatingSeason
        fields = ("id", "year", "name", "is_active")


class RatingPointRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatingPointRule
        fields = ("competition_level", "place", "points")


class RatingRuleSerializer(serializers.ModelSerializer):
    point_rules = RatingPointRuleSerializer(many=True, read_only=True)
    discipline_code = serializers.CharField(source="discipline.code", read_only=True)
    season_year = serializers.IntegerField(source="season.year", read_only=True)

    class Meta:
        model = RatingRuleVersion
        fields = ("id", "season", "season_year", "discipline", "discipline_code", "version", "effective_from", "effective_until", "coefficient_threshold", "stability_coefficient", "rounding_places", "rounding_mode", "is_active", "point_rules", "created_by", "created_at")
        read_only_fields = ("version", "created_by", "created_at")


class RatingPointRuleInputSerializer(serializers.Serializer):
    competition_level = serializers.CharField(max_length=100)
    place = serializers.IntegerField(min_value=1)
    points = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0)


class RatingRuleInputSerializer(serializers.ModelSerializer):
    point_rules = RatingPointRuleInputSerializer(many=True)

    class Meta:
        model = RatingRuleVersion
        fields = ("season", "discipline", "effective_from", "effective_until", "coefficient_threshold", "stability_coefficient", "rounding_places", "rounding_mode", "is_active", "point_rules")


class RatingContributionSerializer(serializers.Serializer):
    competition_id = serializers.IntegerField()
    competition_title = serializers.CharField(source="competition.title")
    competition_level = serializers.CharField(source="competition.level")
    publication_id = serializers.IntegerField()
    publication_version = serializers.IntegerField(source="publication.version")
    placement = serializers.IntegerField()
    awarded_points = serializers.DecimalField(max_digits=8, decimal_places=2)
    age_group = serializers.CharField()
    source_snapshot = serializers.SerializerMethodField()

    def get_source_snapshot(self, obj) -> dict:
        # The public rating breakdown needs scoring evidence, never private names
        # or arbitrary additional fields copied into an immutable protocol row.
        return {key: obj.result_snapshot.get(key) for key in ("status", "place", "score", "age_group")}


class AthleteRatingSerializer(serializers.ModelSerializer):
    athlete_name = serializers.SerializerMethodField()
    season = serializers.IntegerField(source="season.year")
    discipline_code = serializers.CharField(source="discipline.code")
    discipline_name = serializers.CharField(source="discipline.name")
    breakdown = serializers.SerializerMethodField()
    placement = serializers.IntegerField(read_only=True)

    class Meta:
        model = AthleteRating
        fields = ("id", "athlete", "athlete_name", "season", "discipline", "discipline_code", "discipline_name", "base_score", "prize_count", "coefficient", "rating_score", "calculated_at", "placement", "breakdown")

    @extend_schema_field(RatingContributionSerializer(many=True))
    def get_breakdown(self, obj):
        return RatingContributionSerializer(obj.athlete.rating_contributions.filter(season=obj.season, discipline=obj.discipline, is_current=True).select_related("competition", "publication"), many=True).data

    def get_athlete_name(self, obj) -> str:
        from django.utils import timezone
        from apps.competitions.services import age_on
        from apps.competitions.models import CoachAthleteLink
        born = obj.athlete.date_of_birth
        if born and age_on(born, timezone.localdate()) >= 18:
            return obj.athlete.full_name
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            role = request.session.get("active_role")
            if request.user.role_assignments.filter(role=role).exists():
                if role == "federation" or (role == "athlete" and request.user.pk == obj.athlete_id):
                    return obj.athlete.full_name
                if role == "coach" and CoachAthleteLink.objects.filter(coach=request.user, athlete=obj.athlete, discipline=obj.discipline, status="confirmed").exists():
                    return obj.athlete.full_name
        return f"Спортсмен №{obj.athlete_id}"


class AthleteRestrictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AthleteRestriction
        fields = ("id", "athlete", "kind", "starts_at", "ends_at", "status", "created_by", "created_at")
        read_only_fields = ("created_by", "created_at")
