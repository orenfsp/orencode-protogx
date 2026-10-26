from datetime import date

from django.contrib.auth import authenticate, password_validation
from django.db import transaction
from rest_framework import serializers

from .models import Guardian, PersonalDataConsent, User, UserRole


class MeSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    active_role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "full_name", "roles", "active_role")

    def get_roles(self, obj) -> list[str]:
        return list(obj.role_assignments.values_list("role", flat=True))

    def get_active_role(self, obj) -> str | None:
        request = self.context.get("request")
        role = request.session.get("active_role") if request else None
        return role if role in self.get_roles(obj) else None


class AuthResponseSerializer(serializers.Serializer):
    user = MeSerializer()


class CsrfSerializer(serializers.Serializer):
    csrfToken = serializers.CharField()


class EmptySerializer(serializers.Serializer):
    pass


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(max_length=200)
    date_of_birth = serializers.DateField()
    consent = serializers.BooleanField()
    consent_version = serializers.CharField(max_length=40)
    guardian_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    guardian_relationship = serializers.CharField(max_length=100, required=False, allow_blank=True)
    guardian_consent = serializers.BooleanField(required=False, default=False)

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Account already exists")
        return value

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    def validate(self, attrs):
        if not attrs["consent"]:
            raise serializers.ValidationError({"consent": "Consent is required"})
        if attrs["consent_version"] != "v1-demo-2026-10-27":
            raise serializers.ValidationError({"consent_version": "Unsupported consent version"})
        born = attrs.get("date_of_birth")
        if born:
            today = date.today()
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            if age < 0:
                raise serializers.ValidationError({"date_of_birth": "Date cannot be in the future"})
            if age < 18 and not (attrs.get("guardian_name") and attrs.get("guardian_relationship") and attrs.get("guardian_consent")):
                raise serializers.ValidationError({"guardian_consent": "Guardian details and consent are required for a minor"})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        guardian_name = validated_data.pop("guardian_name", "")
        guardian_relationship = validated_data.pop("guardian_relationship", "")
        guardian_consent = validated_data.pop("guardian_consent", False)
        validated_data.pop("consent")
        consent_version = validated_data.pop("consent_version")
        user = User.objects.create_user(**validated_data)
        UserRole.objects.create(user=user, role=UserRole.Role.ATHLETE)
        born = user.date_of_birth
        guardian = None
        if born:
            today = date.today()
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            if age < 18 and guardian_consent:
                guardian = Guardian.objects.create(minor=user, full_name=guardian_name, relationship=guardian_relationship)
        PersonalDataConsent.objects.create(user=user, text_version=consent_version, guardian=guardian)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(self.context["request"], email=attrs["email"].lower(), password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        attrs["user"] = user
        return attrs


class ActiveRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=UserRole.Role.choices)
