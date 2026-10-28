from django.apps import apps
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import has_current_consent
from apps.competitions.models import Competition
from apps.competitions.services import age_on, audit
from apps.teams.models import RegionalTeam


class YearFilter(serializers.Serializer):
    year = serializers.IntegerField(min_value=1901, max_value=2199, required=False)


class MinistryView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        if not request.user.has_perm("extensions.view_ministry_dashboard"):
            raise PermissionDenied("Требуется право чтения кабинета министерства")
        serializer = YearFilter(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        year = serializer.validated_data.get("year", timezone.localdate().year)
        events = Competition.objects.filter(
            state__in=["published", "closed"], starts_at__year=year
        ).select_related("calendar_entry")
        teams = RegionalTeam.objects.filter(
            status="published", season__year=year
        ).prefetch_related("memberships__athlete")
        items = [
            {
                "id": f"event-{c.pk}",
                "kind": "Календарь",
                "name": c.title,
                "source": f"competitions/{c.pk}",
                "details": f"{c.starts_at.date()} · {c.level} · {c.calendar_entry.entry_number if c.calendar_entry else 'без записи плана'}",
            }
            for c in events
        ]
        for team in teams:
            roster = []
            for m in (
                team.memberships.filter(removed_at=None)
                .select_related("athlete")
                .order_by("position", "pk")
            ):
                adult = (
                    m.athlete.date_of_birth
                    and age_on(m.athlete.date_of_birth, timezone.localdate()) >= 18
                )
                roster.append(
                    f"{m.position}. {m.athlete.full_name if adult and has_current_consent(m.athlete) else 'Персональные данные ограничены'}"
                )
            items.append(
                {
                    "id": f"team-{team.pk}",
                    "kind": "Состав сборной",
                    "name": team.name,
                    "source": f"teams/{team.pk}",
                    "details": "; ".join(roster),
                }
            )
        available = apps.is_installed("apps.registry")
        if available:
            from apps.registry.analytics import (
                consistent_report_read,
                participation_report,
            )

            with consistent_report_read():
                rows = participation_report(year - 1, year)
            items += [
                {
                    "id": f"report-{r['year']}",
                    "kind": "Численность",
                    "name": str(r["year"]),
                    "source": "registry:calendar-year-v1",
                    "details": f"Уникальных спортсменов: {r['unique_athletes']}",
                }
                for r in rows
            ]
        audit(request.user, "ministry.viewed", request.user, after={"year": year})
        response = Response(
            {
                "items": items,
                "notice": "Доступ только для чтения. Персональные данные несовершеннолетних ограничены. "
                + (
                    "Методика отчёта: calendar-year-v1."
                    if available
                    else "Обязательный отчёт AC-11 ещё в PR #5; его данные здесь недоступны и не заменены оценкой."
                ),
                "options": {},
                "registry_available": available,
            }
        )
        response["Cache-Control"] = "private, no-store"
        return response
