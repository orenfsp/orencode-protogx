from rest_framework import serializers

from .models import Notification, ReportDeadline


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "created_at", "read_at", "status", "attempts", "sent_at", "error_code"]
        read_only_fields = fields


class ReportDeadlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportDeadline
        fields = ["id", "title", "due_on"]
        read_only_fields = ["id"]
