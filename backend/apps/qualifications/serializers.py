from django.utils import timezone
from rest_framework import serializers

from .models import (
    JudgeCategory,
    JudgeCategoryApplication,
    JudgeCategoryHistory,
    QualificationRule,
    RankApplication,
    RequestType,
    SportRank,
    SportRankHistory,
)
from .services import days_left, validity_state


class RankApplicationCreateSerializer(serializers.Serializer):
    result = serializers.IntegerField(min_value=1)
    requested_rank = serializers.ChoiceField(choices=SportRank.choices)
    request_type = serializers.ChoiceField(choices=RequestType.choices)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class CategoryApplicationCreateSerializer(serializers.Serializer):
    requested_category = serializers.ChoiceField(choices=JudgeCategory.choices)
    request_type = serializers.ChoiceField(choices=RequestType.choices)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class DecisionInputSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[("approved", "approved"), ("rejected", "rejected")])
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    order_number = serializers.CharField(required=False, allow_blank=True, max_length=100)
    assigned_on = serializers.DateField(required=False)
    valid_until = serializers.DateField(required=False)


class _ValiditySerializer(serializers.ModelSerializer):
    validity = serializers.SerializerMethodField()
    days_left = serializers.SerializerMethodField()

    def get_validity(self, obj) -> str:
        return validity_state(obj.valid_until, timezone.localdate())

    def get_days_left(self, obj) -> int:
        return days_left(obj.valid_until, timezone.localdate())


class SportRankHistorySerializer(_ValiditySerializer):
    athlete_name = serializers.CharField(source="athlete.full_name", read_only=True)
    discipline_name = serializers.CharField(source="discipline.name", read_only=True)
    rank_label = serializers.CharField(source="get_rank_display", read_only=True)
    competition_id = serializers.IntegerField(source="application.competition_id", read_only=True)
    competition_title = serializers.CharField(source="application.competition.title", read_only=True)
    result_id = serializers.IntegerField(source="application.result_id", read_only=True)
    place = serializers.IntegerField(source="application.result.place", read_only=True)

    class Meta:
        model = SportRankHistory
        fields = ("id", "athlete", "athlete_name", "discipline", "discipline_name", "rank", "rank_label", "order_number",
                  "assigned_on", "valid_until", "validity", "days_left", "competition_id", "competition_title", "result_id", "place")


class JudgeCategoryHistorySerializer(_ValiditySerializer):
    judge_name = serializers.CharField(source="judge.full_name", read_only=True)
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = JudgeCategoryHistory
        fields = ("id", "judge", "judge_name", "category", "category_label", "order_number", "assigned_on", "valid_until", "validity", "days_left")


class RankApplicationSerializer(serializers.ModelSerializer):
    athlete_name = serializers.CharField(source="athlete.full_name", read_only=True)
    submitted_by_name = serializers.CharField(source="submitted_by.full_name", read_only=True)
    discipline_name = serializers.CharField(source="discipline.name", read_only=True)
    competition_title = serializers.CharField(source="competition.title", read_only=True)
    competition_level = serializers.CharField(source="competition.level", read_only=True)
    requested_rank_label = serializers.CharField(source="get_requested_rank_display", read_only=True)
    place = serializers.IntegerField(source="result.place", read_only=True)
    score = serializers.DecimalField(source="result.score", max_digits=12, decimal_places=3, read_only=True)
    record = serializers.SerializerMethodField()

    class Meta:
        model = RankApplication
        fields = ("id", "athlete", "athlete_name", "submitted_by", "submitted_by_name", "request_type", "requested_rank", "requested_rank_label",
                  "discipline", "discipline_name", "competition", "competition_title", "competition_level", "result", "place", "score",
                  "comment", "status", "decision_reason", "decided_by", "submitted_at", "decided_at", "record")

    def get_record(self, obj):
        record = getattr(obj, "rank_record", None)
        if record is None:
            return None
        return {"id": record.pk, "order_number": record.order_number, "assigned_on": record.assigned_on, "valid_until": record.valid_until}


class JudgeCategoryApplicationSerializer(serializers.ModelSerializer):
    judge_name = serializers.CharField(source="judge.full_name", read_only=True)
    requested_category_label = serializers.CharField(source="get_requested_category_display", read_only=True)
    record = serializers.SerializerMethodField()

    class Meta:
        model = JudgeCategoryApplication
        fields = ("id", "judge", "judge_name", "request_type", "requested_category", "requested_category_label", "comment", "status",
                  "decision_reason", "decided_by", "submitted_at", "decided_at", "record")

    def get_record(self, obj):
        record = getattr(obj, "category_record", None)
        if record is None:
            return None
        return {"id": record.pk, "order_number": record.order_number, "assigned_on": record.assigned_on, "valid_until": record.valid_until}


class QualificationRuleSerializer(serializers.ModelSerializer):
    discipline_code = serializers.CharField(source="discipline.code", read_only=True)
    rank_label = serializers.CharField(source="get_rank_display", read_only=True)

    class Meta:
        model = QualificationRule
        fields = ("id", "discipline", "discipline_code", "rank", "rank_label", "competition_level", "max_place", "rule_version",
                  "effective_from", "source_url", "source_verified", "source_note", "is_active")
