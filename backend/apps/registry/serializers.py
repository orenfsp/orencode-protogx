from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import User
from apps.catalogs.models import Organization

from .models import (
    DisciplinePeriod,
    MunicipalityPeriod,
    OrganizationPeriod,
    ParticipationPeriod,
    TrainingStagePeriod,
)


class PersonSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "full_name", "date_of_birth", "is_active", "organization")

    def get_organization(self, obj) -> str | None:
        profile = getattr(obj, "athlete_profile", None)
        return profile.organization.name if profile and profile.organization else None


class PersonUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("full_name", "date_of_birth")

    def validate_date_of_birth(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError("Date of birth cannot be in the future")
        return value


class PersonFilterSerializer(serializers.Serializer):
    active = serializers.BooleanField(required=False)
    organization = serializers.IntegerField(required=False, min_value=1)
    discipline = serializers.IntegerField(required=False, min_value=1)
    municipality = serializers.CharField(required=False, max_length=200)


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "code", "name", "organization_type", "municipality", "is_active", "contact")

    def validate_code(self, value):
        if self.instance and value != self.instance.code:
            raise serializers.ValidationError("Organization code is stable and cannot be changed")
        return value


class ParticipationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParticipationPeriod
        fields = ("id", "starts_on", "ends_on")
        read_only_fields = ("id",)


class DisciplinePeriodSerializer(serializers.ModelSerializer):
    discipline_name = serializers.CharField(source="discipline.name", read_only=True)

    class Meta:
        model = DisciplinePeriod
        fields = ("id", "starts_on", "ends_on", "discipline", "discipline_name")
        read_only_fields = ("id",)


class OrganizationPeriodSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = OrganizationPeriod
        fields = ("id", "starts_on", "ends_on", "organization", "organization_name")
        read_only_fields = ("id",)


class MunicipalityPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = MunicipalityPeriod
        fields = ("id", "starts_on", "ends_on", "municipality")
        read_only_fields = ("id",)


class TrainingStagePeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingStagePeriod
        fields = ("id", "starts_on", "ends_on", "stage")
        read_only_fields = ("id",)


class TransferSerializer(serializers.Serializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())
    effective_on = serializers.DateField()


class ClosePeriodSerializer(serializers.Serializer):
    ends_on = serializers.DateField()


class PeriodCorrectionSerializer(serializers.Serializer):
    expected = serializers.JSONField()
    corrected = serializers.JSONField()
    reason = serializers.CharField(max_length=500, trim_whitespace=True, allow_blank=False)


class OptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class RegistryOptionsSerializer(serializers.Serializer):
    organizations = OptionSerializer(many=True)
    disciplines = OptionSerializer(many=True)
    age_groups = OptionSerializer(many=True)
    municipalities = serializers.ListField(child=serializers.CharField())


class ReportQuerySerializer(serializers.Serializer):
    start_year = serializers.IntegerField(min_value=1900, max_value=9998)
    end_year = serializers.IntegerField(min_value=1901, max_value=9999)
    organization = serializers.IntegerField(min_value=1, required=False)
    discipline = serializers.IntegerField(min_value=1, required=False)
    municipality = serializers.CharField(max_length=200, required=False)
    age_group = serializers.IntegerField(min_value=1, required=False)

    def validate(self, attrs):
        if not 1 <= attrs["end_year"] - attrs["start_year"] <= 9:
            raise serializers.ValidationError("Choose between two and ten consecutive years")
        return attrs


class BreakdownRowSerializer(serializers.Serializer):
    name = serializers.CharField()
    participants = serializers.IntegerField()


class BreakdownsSerializer(serializers.Serializer):
    organizations = BreakdownRowSerializer(many=True)
    disciplines = BreakdownRowSerializer(many=True)
    municipalities = BreakdownRowSerializer(many=True)
    age_groups = BreakdownRowSerializer(many=True)


class AnnualReportSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    unique_athletes = serializers.IntegerField()
    started = serializers.IntegerField()
    ceased = serializers.IntegerField()
    change = serializers.IntegerField(allow_null=True)
    growth_percent = serializers.FloatField(allow_null=True)
    breakdowns = BreakdownsSerializer()
