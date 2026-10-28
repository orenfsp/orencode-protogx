from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import User

from .models import RegionalTeam, TeamDecisionHistory, TeamMembership


class TeamMembershipSerializer(serializers.ModelSerializer):
    athlete_name = serializers.CharField(source="athlete.full_name", read_only=True)
    athlete_email = serializers.EmailField(source="athlete.email", read_only=True)
    organization_name = serializers.SerializerMethodField()
    current_eligibility = serializers.SerializerMethodField()

    class Meta:
        model = TeamMembership
        fields = ("id", "athlete", "athlete_name", "athlete_email", "organization_name", "position", "selected_by", "selected_at", "removed_at", "removal_reason", "eligibility_snapshot", "current_eligibility", "selection_note")
        read_only_fields = ("selected_by", "selected_at", "removed_at", "eligibility_snapshot")

    @extend_schema_field(serializers.DictField())
    def get_current_eligibility(self, obj):
        from .services import eligibility_snapshot
        return eligibility_snapshot(athlete=obj.athlete, team=obj.team)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_organization_name(self, obj):
        profile = getattr(obj.athlete, "athlete_profile", None)
        return profile.organization.name if profile and profile.organization else None


class RegionalTeamSerializer(serializers.ModelSerializer):
    season_year = serializers.IntegerField(source="season.year", read_only=True)
    discipline_code = serializers.CharField(source="discipline.code", read_only=True)
    discipline_name = serializers.CharField(source="discipline.name", read_only=True)
    age_group_name = serializers.CharField(source="age_group.name", read_only=True)
    members = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = RegionalTeam
        fields = ("id", "name", "region", "status", "season", "season_year", "discipline", "discipline_code", "discipline_name", "age_group", "age_group_name", "created_by", "created_at", "updated_at", "member_count", "members")
        read_only_fields = ("created_by", "created_at", "updated_at", "member_count", "members")

    @extend_schema_field(serializers.IntegerField)
    def get_member_count(self, obj):
        return obj.memberships.filter(removed_at__isnull=True).count()

    @extend_schema_field(TeamMembershipSerializer(many=True))
    def get_members(self, obj):
        return TeamMembershipSerializer(obj.memberships.filter(removed_at__isnull=True).select_related("athlete", "athlete__athlete_profile__organization").order_by("position"), many=True).data


class TeamCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionalTeam
        fields = ("name", "region", "season", "discipline", "age_group")

    def validate(self, attrs):
        if attrs["age_group"].min_age > attrs["age_group"].max_age:
            raise serializers.ValidationError("Invalid age group")
        return attrs


class MemberAddSerializer(serializers.Serializer):
    athlete = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class MemberRemoveSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class ReorderSerializer(serializers.Serializer):
    member_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)


class TeamHistorySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.full_name", read_only=True)

    class Meta:
        model = TeamDecisionHistory
        fields = ("id", "action", "actor", "actor_name", "membership", "before", "after", "created_at")


class TeamCandidateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    sport_rank = serializers.CharField(allow_null=True)
    eligible = serializers.BooleanField()
    selected = serializers.BooleanField()
    eligibility = serializers.DictField()
    rating = serializers.DictField(allow_null=True)


class TeamPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = RegionalTeamSerializer(many=True)


class CandidatePageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = TeamCandidateSerializer(many=True)


class TeamDocumentResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(required=False)
