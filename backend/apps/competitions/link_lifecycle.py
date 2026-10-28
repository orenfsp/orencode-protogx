from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CoachAthleteLink
from .serializers import CoachLinkSerializer
from .services import audit, require_role


class LinkTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["confirmed", "suspended", "ended"])
    reason = serializers.CharField(max_length=500)


class LinkLifecycleView(APIView):
    @extend_schema(request=LinkTransitionSerializer, responses=CoachLinkSerializer)
    @transaction.atomic
    def post(self, request, pk):
        role = require_role(request, "athlete", "coach")
        scope = {"athlete": request.user} if role == "athlete" else {"coach": request.user}
        link = get_object_or_404(CoachAthleteLink.objects.select_for_update(), pk=pk, **scope)
        serializer = LinkTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        status = serializer.validated_data["status"]
        allowed = {"confirmed": {"suspended", "ended"}, "suspended": {"confirmed", "ended"}}
        if status not in allowed.get(link.status, set()) or (status == "confirmed" and role != "athlete"):
            raise ValidationError("Переход недоступен; возобновление подтверждает спортсмен")
        before = link.status
        link.status = status
        link.save(update_fields=["status"])
        audit(request.user, "coach_link.status_changed", link, before={"status": before}, after={"status": status, "reason": serializer.validated_data["reason"]})
        return Response(CoachLinkSerializer(link, context={"request": request}).data)
