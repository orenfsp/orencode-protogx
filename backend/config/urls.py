from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework import serializers
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()


class HealthView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = HealthSerializer

    def get(self, request):
        return Response({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", HealthView.as_view()),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/disciplines/", include("apps.catalogs.urls")),
    path("api/v1/", include("apps.competitions.urls")),
    path("api/v1/", include("apps.qualifications.urls")),
    path("api/v1/", include("apps.ratings.urls")),
    path("api/v1/", include("apps.teams.urls")),
    path("api/v1/", include("apps.extensions.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
