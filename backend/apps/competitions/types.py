from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CompetitionType
from .services import audit, require_role


class CompetitionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetitionType
        fields = ["id", "name", "is_active"]


class CompetitionTypesView(APIView):
    @extend_schema(responses=CompetitionTypeSerializer(many=True))
    def get(self, request):
        require_role(request, "federation")
        return Response(CompetitionTypeSerializer(CompetitionType.objects.order_by("name"), many=True).data)

    @extend_schema(request=CompetitionTypeSerializer, responses={201: CompetitionTypeSerializer})
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation")
        serializer = CompetitionTypeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        audit(request.user, "competition_type.created", item, after=serializer.data)
        return Response(serializer.data, status=201)


class CompetitionTypeDetailView(APIView):
    @extend_schema(request=CompetitionTypeSerializer, responses=CompetitionTypeSerializer)
    @transaction.atomic
    def patch(self, request, pk):
        require_role(request, "federation")
        item = get_object_or_404(CompetitionType.objects.select_for_update(), pk=pk)
        before = CompetitionTypeSerializer(item).data
        serializer = CompetitionTypeSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit(request.user, "competition_type.updated", item, before=before, after=serializer.data)
        return Response(serializer.data)
