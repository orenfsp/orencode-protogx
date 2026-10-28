from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalogs.models import Discipline
from apps.competitions.models import Competition

from .models import TrainingOrganization


class NewcomerView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=OpenApiTypes.OBJECT, auth=[])
    def get(self, request):
        cards = (
            TrainingOrganization.objects.filter(public=True)
            .select_related("organization")
            .prefetch_related("disciplines")
        )
        if request.query_params.get("municipality"):
            cards = cards.filter(
                municipality__iexact=request.query_params["municipality"][:200]
            )
        if request.query_params.get("discipline"):
            cards = cards.filter(
                disciplines__code=request.query_params["discipline"][:64]
            )
        events = (
            Competition.objects.filter(state="published", starts_at__gt=timezone.now())
            .select_related("discipline")
            .order_by("starts_at")[:20]
        )
        return Response(
            {
                "notice": "Спортивное программирование — соревнования в решении задач и разработке. Выберите дисциплину, найдите место занятий, зарегистрируйтесь и изучите регламент соревнования. Наличие в списке не подтверждает лицензию или аккредитацию.",
                "items": [
                    {
                        "id": f"discipline-{d.pk}",
                        "kind": "Дисциплина",
                        "name": d.name,
                        "description": "Начните с учебных задач и ознакомления с регламентом выбранной дисциплины",
                        "link": "/competitions",
                    }
                    for d in Discipline.objects.filter(is_active=True)
                ]
                + [
                    {
                        "id": f"organization-{c.pk}",
                        "kind": "Где заниматься",
                        "name": c.organization.name,
                        "description": f"{c.municipality} · {c.program}",
                        "link": c.contact_url,
                    }
                    for c in cards.distinct()
                ]
                + [
                    {
                        "id": f"event-{c.pk}",
                        "kind": "Ближайшее соревнование",
                        "name": c.title,
                        "description": f"{c.discipline.name} · {c.starts_at.date()} · приём до {c.registration_deadline.date()}",
                        "link": f"/competitions/{c.pk}",
                    }
                    for c in events
                ],
                "options": {},
            }
        )
