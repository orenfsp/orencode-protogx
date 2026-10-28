from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.competitions.services import audit, require_role

from .models import ReportDeadline
from .serializers import NotificationSerializer, ReportDeadlineSerializer
from .services import ROLES, visible_notifications


class NotificationsView(APIView):
    @extend_schema(responses=NotificationSerializer(many=True))
    def get(self, request):
        role = require_role(request, *ROLES)
        return Response(NotificationSerializer(visible_notifications(request.user, role)[:100], many=True).data)


class NotificationReadView(APIView):
    @extend_schema(request=None, responses=NotificationSerializer)
    @transaction.atomic
    def post(self, request, pk):
        role = require_role(request, *ROLES)
        item = get_object_or_404(visible_notifications(request.user, role).select_for_update(), pk=pk)
        if item.read_at is None:
            item.read_at = timezone.now()
            item.save(update_fields=["read_at"])
        return Response(NotificationSerializer(item).data)


class ReportDeadlinesView(APIView):
    @extend_schema(responses=ReportDeadlineSerializer(many=True))
    def get(self, request):
        require_role(request, "federation")
        return Response(ReportDeadlineSerializer(ReportDeadline.objects.order_by("due_on", "id"), many=True).data)

    @extend_schema(request=ReportDeadlineSerializer, responses={201: ReportDeadlineSerializer})
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation")
        serializer = ReportDeadlineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save(created_by=request.user)
        audit(request.user, "report_deadline.created", item, after=serializer.data)
        return Response(serializer.data, status=201)
