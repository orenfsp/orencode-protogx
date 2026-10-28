from django.http import HttpResponse
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import Guardian, has_current_consent
from apps.competitions.models import CoachAthleteLink
from apps.competitions.services import age_on, require_role


def validated(serializer_class, data):
    serializer = serializer_class(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def private_response(content, content_type, filename):
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def athlete_access(request, athlete, discipline=None, *, write=False):
    role = require_role(request, "federation", "coach", *( () if write else ("athlete",)))
    if role == "federation":
        return role
    if role == "athlete" and athlete.pk == request.user.pk:
        return role
    links = CoachAthleteLink.objects.filter(coach=request.user, athlete=athlete, status="confirmed")
    if discipline is not None:
        links = links.filter(discipline=discipline)
    if role == "coach" and links.exists():
        return role
    raise PermissionDenied("Нет доступа к спортсмену по подтверждённой связи")


def require_athlete_consent(athlete, day):
    if not athlete.is_active or not athlete.role_assignments.filter(role="athlete").exists() or not has_current_consent(athlete):
        raise ValidationError("Необходимо действующее согласие спортсмена")
    if not athlete.date_of_birth:
        raise ValidationError("Не указана дата рождения")
    if age_on(athlete.date_of_birth, day) < 18 and not Guardian.objects.filter(minor=athlete, confirmation_status="verified").exists():
        raise ValidationError("Необходимо проверенное согласие представителя")


class IdInput(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)


class EmptyInput(serializers.Serializer):
    pass
