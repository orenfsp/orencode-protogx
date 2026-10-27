from rest_framework import serializers

from apps.accounts.models import User
from apps.catalogs.models import Discipline

from .models import (
    AgeGroup,
    Application,
    CalendarEntry,
    CoachAthleteLink,
    Competition,
    CompetitionStage,
    JudgeAssignment,
    ProtocolPublication,
    ProtocolTemplate,
    Result,
)


class AgeGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgeGroup
        fields = ("id", "name", "min_age", "max_age")


class CalendarEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEntry
        fields = ("id", "source", "entry_number", "title", "year", "reference_url")


class ProtocolTemplateSerializer(serializers.ModelSerializer):
    discipline_code = serializers.CharField(source="discipline.code", read_only=True)

    class Meta:
        model = ProtocolTemplate
        fields = ("id", "discipline", "discipline_code", "version", "name", "competition_type", "rule_version", "effective_from", "metric_fields", "columns", "sections", "signature_roles", "sort", "source_url", "source_verified", "source_note")
        read_only_fields = ("version", "source_verified")


class StageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetitionStage
        fields = ("id", "order", "name", "format", "starts_at", "ends_at")


class CompetitionSerializer(serializers.ModelSerializer):
    discipline_name = serializers.CharField(source="discipline.name", read_only=True)
    age_group_details = AgeGroupSerializer(source="age_groups", many=True, read_only=True)
    stages = StageSerializer(many=True, required=False)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Competition
        fields = ("id", "title", "discipline", "discipline_name", "age_groups", "age_group_details", "level", "competition_type", "format", "starts_at", "ends_at", "registration_deadline", "age_reference_date", "allow_ties", "location", "regulations", "calendar_entry", "template", "state", "stages", "created_by", "created_at", "updated_at")
        read_only_fields = ("state", "created_at", "updated_at")

    def validate(self, attrs):
        instance = self.instance
        discipline = attrs.get("discipline", instance.discipline if instance else None)
        template = attrs.get("template", instance.template if instance else None)
        starts = attrs.get("starts_at", instance.starts_at if instance else None)
        ends = attrs.get("ends_at", instance.ends_at if instance else None)
        deadline = attrs.get("registration_deadline", instance.registration_deadline if instance else None)
        groups = attrs.get("age_groups", list(instance.age_groups.all()) if instance else [])
        if not instance and not attrs.get("age_reference_date"):
            raise serializers.ValidationError({"age_reference_date": "Regulations must specify an age reference date"})
        if template and discipline and template.discipline_id != discipline.id:
            raise serializers.ValidationError({"template": "Template discipline must match competition discipline"})
        event_type = attrs.get("competition_type", instance.competition_type if instance else None)
        if template and template.competition_type and template.competition_type != event_type:
            raise serializers.ValidationError({"template": "Template is configured for a different competition type"})
        if template and template.effective_from and starts and starts.date() < template.effective_from:
            raise serializers.ValidationError({"template": "Template is not effective on the competition date"})
        if starts and ends and starts >= ends:
            raise serializers.ValidationError({"ends_at": "End must follow start"})
        if deadline and starts and deadline >= starts:
            raise serializers.ValidationError({"registration_deadline": "Registration must close before start"})
        if not groups:
            raise serializers.ValidationError({"age_groups": "At least one age group is required"})
        stages = attrs.get("stages", [])
        if attrs.get("format", instance.format if instance else None) == "hybrid" and not stages and (not instance or not instance.stages.exists()):
            raise serializers.ValidationError({"stages": "Hybrid competition requires stages"})
        for stage in stages:
            if starts and ends and not (starts <= stage["starts_at"] < stage["ends_at"] <= ends):
                raise serializers.ValidationError({"stages": "Stages must fit competition dates"})
        return attrs

    def create(self, validated_data):
        stages = validated_data.pop("stages", [])
        groups = validated_data.pop("age_groups")
        competition = Competition.objects.create(**validated_data)
        competition.age_groups.set(groups)
        for stage in stages:
            CompetitionStage.objects.create(competition=competition, **stage)
        return competition

    def update(self, instance, validated_data):
        stages = validated_data.pop("stages", None)
        groups = validated_data.pop("age_groups", None)
        instance = super().update(instance, validated_data)
        if groups is not None:
            instance.age_groups.set(groups)
        if stages is not None:
            instance.stages.all().delete()
            for stage in stages:
                stage.pop("id", None)
                CompetitionStage.objects.create(competition=instance, **stage)
        return instance


class ApplicationSerializer(serializers.ModelSerializer):
    athlete_name = serializers.CharField(source="athlete.full_name", read_only=True)
    submitted_by = serializers.PrimaryKeyRelatedField(read_only=True)
    decided_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Application
        fields = ("id", "competition", "athlete", "athlete_name", "age_group", "submitted_by", "status", "decision_reason", "decided_by", "submitted_at", "decided_at")
        read_only_fields = ("status", "decision_reason", "submitted_at", "decided_at")


class DecisionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=("approved", "rejected"))
    reason = serializers.CharField(required=False, allow_blank=True)


class JudgeAssignmentSerializer(serializers.ModelSerializer):
    judge_name = serializers.CharField(source="judge.full_name", read_only=True)
    assigned_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = JudgeAssignment
        fields = ("id", "competition", "judge", "judge_name", "role_label", "assigned_by", "assigned_at")
        read_only_fields = ("assigned_at",)


class ResultSerializer(serializers.ModelSerializer):
    application = serializers.PrimaryKeyRelatedField(queryset=Application.objects.all(), validators=[])
    validated_by = serializers.PrimaryKeyRelatedField(read_only=True)
    updated_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Result
        fields = ("id", "application", "status", "place", "score", "metrics", "validated_by", "updated_by", "updated_at")
        read_only_fields = ("updated_at",)


class ProtocolPublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProtocolPublication
        fields = ("id", "competition", "version", "template", "snapshot", "correction_reason", "published_by", "published_at")


class ProtocolPublishRequestSerializer(serializers.Serializer):
    correction_reason = serializers.CharField(required=False, allow_blank=True)


class CoachLinkSerializer(serializers.ModelSerializer):
    coach_name = serializers.CharField(source="coach.full_name", read_only=True)
    athlete = serializers.SerializerMethodField()
    athlete_name = serializers.SerializerMethodField()

    def get_athlete(self, obj) -> int | None:
        request = self.context.get("request")
        return obj.athlete_id if obj.status == "confirmed" or (request and request.user.pk == obj.athlete_id) else None

    def get_athlete_name(self, obj) -> str:
        request = self.context.get("request")
        return obj.athlete.full_name if obj.status == "confirmed" or (request and request.user.pk == obj.athlete_id) else "Ожидает подтверждения"

    class Meta:
        model = CoachAthleteLink
        fields = ("id", "coach", "coach_name", "athlete", "athlete_name", "discipline", "status", "created_at")
        read_only_fields = ("coach", "status", "created_at")


class CoachLinkRequestSerializer(serializers.Serializer):
    athlete_email = serializers.EmailField()
    discipline = serializers.PrimaryKeyRelatedField(queryset=Discipline.objects.all())


class UserChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "full_name")


class ProtocolColumnSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()


class ProtocolSnapshotSerializer(serializers.Serializer):
    competition_id = serializers.IntegerField()
    competition_title = serializers.CharField()
    discipline = serializers.CharField()
    template_id = serializers.IntegerField()
    template_version = serializers.IntegerField()
    source_verified = serializers.BooleanField()
    source_note = serializers.CharField()
    source_url = serializers.URLField(allow_blank=True)
    sections = serializers.ListField(child=serializers.CharField())
    signature_roles = serializers.ListField(child=serializers.CharField())
    sort = serializers.DictField()
    metadata = serializers.DictField()
    judges = serializers.ListField(child=serializers.DictField())
    columns = ProtocolColumnSerializer(many=True)
    rows = serializers.ListField(child=serializers.DictField(), help_text="One row per approved application, including missing results")


class AthleteHistorySerializer(serializers.Serializer):
    competition_id = serializers.IntegerField()
    competition_title = serializers.CharField()
    version = serializers.IntegerField()
    published_at = serializers.DateTimeField()
    row = serializers.DictField()


class CoachLinkDecisionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=("confirmed", "rejected"))
