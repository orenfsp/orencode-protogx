import hashlib
from io import BytesIO

from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.competitions.models import Application, Competition, Result
from apps.competitions.serializers import ResultSerializer
from apps.competitions.services import (
    audit,
    publish_protocol,
    require_role,
    validate_result_data,
)
from apps.ratings.models import AthleteRestriction

from .common import athlete_access, private_response, validated
from .models import ReviewCase, ReviewEvidence, ReviewHistory, ReviewPolicy
from .notifications import notify


class CaseInput(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["appeal", "incident"])
    application = serializers.PrimaryKeyRelatedField(
        queryset=Application.objects.filter(status="approved")
    )
    statement = serializers.CharField(max_length=10000)


class EvidenceInput(serializers.Serializer):
    description = serializers.CharField(max_length=500)
    url = serializers.URLField(required=False, allow_blank=True)
    file = serializers.FileField(required=False, max_length=200)


class ReviewActionInput(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=["start", "request_materials", "submit_materials", "accept", "reject"]
    )
    expected_revision = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=10000)
    appeal_rights = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, default=""
    )
    correction = serializers.DictField(required=False)
    publish_correction = serializers.BooleanField(default=False)
    sanction = serializers.ChoiceField(
        choices=["disqualification", "technical_loss"], required=False
    )
    starts_on = serializers.DateField(required=False)
    ends_on = serializers.DateField(required=False)


class PolicyInput(serializers.ModelSerializer):
    class Meta:
        model = ReviewPolicy
        fields = [
            "competition",
            "appeal_deadline",
            "source_url",
            "rule_note",
            "allow_disqualification",
            "allow_technical_loss",
        ]


def case_access(request, case, *, reviewer=False):
    role = require_role(request, "federation", "judge", "athlete", "coach")
    if role == "federation":
        if reviewer and (
            case.submitted_by_id == request.user.pk
            or case.application.athlete_id == request.user.pk
        ):
            raise PermissionDenied("Нельзя рассматривать собственное дело")
        return
    if (
        role == "judge"
        and case.application.competition.judge_assignments.filter(
            judge=request.user
        ).exists()
    ):
        if reviewer and (
            case.submitted_by_id == request.user.pk
            or Result.objects.filter(
                application=case.application, updated_by=request.user
            ).exists()
        ):
            raise PermissionDenied(
                "Конфликт интересов: собственный рапорт или результат"
            )
        return
    if not reviewer:
        athlete_access(
            request, case.application.athlete, case.application.competition.discipline
        )
        return
    raise PermissionDenied("Нет права рассмотрения")


def record_step(case, actor, action, reason):
    ReviewHistory.objects.create(
        case=case, actor=actor, action=action, reason=reason, state=case.status
    )
    audit(
        actor,
        f"review.{action}",
        case,
        competition=case.application.competition,
        after={"status": case.status, "revision": case.revision},
    )
    notify(
        case.application.athlete,
        f"review:{case.pk}:{case.revision}",
        "Изменён статус апелляции или рапорта",
    )
    notify(
        case.submitted_by,
        f"review:{case.pk}:{case.revision}",
        "Изменён статус обращения",
    )
    for user in User.objects.filter(
        is_active=True, role_assignments__role="federation"
    ):
        notify(
            user,
            f"review:{case.pk}:{case.revision}",
            "Доступно действие по апелляции или рапорту",
        )
    for assignment in case.application.competition.judge_assignments.select_related(
        "judge"
    ):
        notify(
            assignment.judge,
            f"review:{case.pk}:{case.revision}",
            "Доступно действие по апелляции или рапорту",
        )


class ReviewCasesView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        role = require_role(request, "federation", "judge", "athlete", "coach")
        cases = ReviewCase.objects.select_related(
            "application__athlete", "application__competition"
        )
        applications = Application.objects.filter(status="approved").select_related(
            "competition", "athlete"
        )
        if role == "athlete":
            applications = applications.filter(athlete=request.user)
        elif role == "coach":
            applications = applications.filter(
                athlete__coach_links__coach=request.user,
                athlete__coach_links__status="confirmed",
                athlete__coach_links__discipline=F("competition__discipline"),
            ).distinct()
        elif role == "judge":
            applications = applications.filter(
                competition__judge_assignments__judge=request.user
            )
        cases = cases.filter(application__in=applications)
        items = []
        for c in cases.order_by("-pk")[:100]:
            items.append(
                {
                    "id": c.pk,
                    "kind": c.get_kind_display(),
                    "name": c.application.athlete.full_name,
                    "status": c.status,
                    "revision": c.revision,
                    "details": c.statement,
                    "decision": c.decision,
                    "appeal_rights": c.appeal_rights
                    or "Порядок обжалования не указан; требуется регламент",
                    "sanction": c.get_sanction_display() if c.sanction else "—",
                    "effective_period": f"{c.restriction.starts_at} — {c.restriction.ends_at}"
                    if c.restriction_id
                    else str(c.sanction_effective_on or "—"),
                    "policy_source": ReviewPolicy.objects.filter(
                        competition=c.application.competition
                    )
                    .values_list("source_url", flat=True)
                    .first()
                    or "Регламент не внесён",
                    "history": [
                        f"{h.created_at.date()} · {h.state} · {h.reason}"
                        for h in c.history.order_by("pk")
                    ],
                    "evidence": [
                        {
                            "id": e.pk,
                            "description": e.description,
                            "url": e.url,
                            "download_url": f"/api/v1/reviews/evidence/{e.pk}/"
                            if e.content
                            else None,
                        }
                        for e in c.evidence.all()
                    ],
                }
            )
        return Response(
            {
                "items": items,
                "notice": "Срок апелляции определяется только явно внесённым регламентом. Решение требует обоснования. Корректировку и публикацию новой версии выполняет федерация; доказательства приватны. При отсутствии установленной политики санкции запрещены.",
                "options": {
                    "competitions": [
                        {"value": c.pk, "label": c.title}
                        for c in Competition.objects.all()
                    ]
                    if role == "federation"
                    else [],
                    "applications": [
                        {
                            "value": a.pk,
                            "label": f"{a.competition.title} · {a.athlete.full_name}",
                        }
                        for a in applications
                    ],
                    "cases": [
                        {
                            "value": c.pk,
                            "label": f"№{c.pk}: {c.get_kind_display()} (ревизия {c.revision})",
                        }
                        for c in cases
                    ],
                },
            }
        )

    @extend_schema(request=CaseInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        data = validated(CaseInput, request.data)
        application = data["application"]
        if data["kind"] == "appeal":
            athlete_access(
                request, application.athlete, application.competition.discipline
            )
            policy = ReviewPolicy.objects.filter(
                competition=application.competition
            ).first()
            if (
                policy
                and policy.appeal_deadline
                and timezone.now() > policy.appeal_deadline
            ):
                raise ValidationError("Истёк срок апелляции по внесённому регламенту")
        else:
            role = require_role(request, "federation", "judge")
            if (
                role == "judge"
                and not application.competition.judge_assignments.filter(
                    judge=request.user
                ).exists()
            ):
                raise PermissionDenied("Судья не назначен на соревнование")
        publication = application.competition.protocols.first()
        if data["kind"] == "appeal" and not publication:
            raise ValidationError("Для апелляции нужен опубликованный результат")
        case = ReviewCase.objects.create(
            **data, submitted_by=request.user, publication=publication
        )
        record_step(case, request.user, "submitted", data["statement"])
        return Response({"id": case.pk, "revision": case.revision}, status=201)


class ReviewActionView(APIView):
    @extend_schema(request=ReviewActionInput, responses=OpenApiTypes.OBJECT)
    @transaction.atomic
    def post(self, request, pk):
        initial = get_object_or_404(ReviewCase, pk=pk)
        Competition.objects.select_for_update().get(
            pk=initial.application.competition_id
        )
        case = ReviewCase.objects.select_for_update().get(pk=pk)
        data = validated(ReviewActionInput, request.data)
        action = data["action"]
        if "sanction" in data and ("correction" in data or data["publish_correction"]):
            raise ValidationError("Выберите санкцию либо исправление результата")
        case_access(request, case, reviewer=action != "submit_materials")
        if case.revision != data["expected_revision"]:
            raise ValidationError("Дело изменилось; обновите данные")
        transitions = {
            "start": ("submitted", "reviewing"),
            "request_materials": ("reviewing", "needs_materials"),
            "submit_materials": ("needs_materials", "submitted"),
            "accept": ("reviewing", "accepted"),
            "reject": ("reviewing", "rejected"),
        }
        before, after = transitions[action]
        if case.status != before:
            raise ValidationError("Недопустимый переход статуса")
        if (
            any(k in data for k in ["correction", "sanction"])
            or data["publish_correction"]
        ) and action != "accept":
            raise ValidationError(
                "Изменение результата допустимо только в удовлетворённом решении"
            )
        if "correction" in data or "sanction" in data or data["publish_correction"]:
            require_role(request, "federation")
            if "sanction" in data:
                policy = ReviewPolicy.objects.filter(
                    competition=case.application.competition
                ).first()
                allowed = policy and (
                    policy.allow_disqualification
                    if data["sanction"] == "disqualification"
                    else policy.allow_technical_loss
                )
                if not allowed or case.kind != "incident":
                    raise ValidationError(
                        "Санкция не разрешена внесённым регламентом или это не рапорт"
                    )
                if not data["appeal_rights"].strip():
                    raise ValidationError(
                        "Укажите порядок обжалования по внесённому регламенту"
                    )
                case.sanction = data["sanction"]
                case.sanction_effective_on = data.get(
                    "starts_on", case.application.competition.starts_at.date()
                )
                correction = {
                    "status": "disqualified"
                    if data["sanction"] == "disqualification"
                    else "unclassified",
                    "place": None,
                    "score": None,
                    "metrics": {},
                }
                if data["sanction"] == "disqualification":
                    if (
                        not data.get("starts_on")
                        or not data.get("ends_on")
                        or data["ends_on"] < data["starts_on"]
                    ):
                        raise ValidationError("Укажите корректный период санкции")
                    restriction = AthleteRestriction.objects.create(
                        athlete=case.application.athlete,
                        kind="disqualification",
                        starts_at=data["starts_on"],
                        ends_at=data["ends_on"],
                        reason_private=data["reason"],
                        created_by=request.user,
                    )
                    case.restriction = restriction
                    audit(
                        request.user,
                        "review.restriction_recorded",
                        restriction,
                        competition=case.application.competition,
                        after={
                            "case": case.pk,
                            "policy": policy.pk,
                            "starts_on": str(restriction.starts_at),
                            "ends_on": str(restriction.ends_at),
                        },
                    )
            elif "correction" in data:
                correction = data["correction"]
                if set(correction) - {"status", "place", "score", "metrics"}:
                    raise ValidationError("Неизвестные поля исправления")
            else:
                result = get_object_or_404(Result, application=case.application)
                if not result.validated_by_id:
                    raise ValidationError(
                        "Сначала проверьте исправленный результат в карточке соревнования"
                    )
                correction = {
                    "status": result.status,
                    "place": result.place,
                    "score": result.score,
                    "metrics": result.metrics,
                }
            # Reuse the existing metric/type and approval validation, never mutate a snapshot.
            serializer = ResultSerializer(
                data={"application": case.application_id, **correction}
            )
            serializer.is_valid(raise_exception=True)
            clean = serializer.validated_data
            validate_result_data(
                case.application,
                clean["status"],
                clean.get("place"),
                clean.get("score"),
                clean.get("metrics", {}),
            )
            Result.objects.update_or_create(
                application=case.application,
                defaults={
                    "status": clean["status"],
                    "place": clean.get("place"),
                    "score": clean.get("score"),
                    "metrics": clean.get("metrics", {}),
                    "updated_by": request.user,
                    "validated_by": request.user,
                },
            )
            if case.restriction_id:
                # Acquire season locks in chronological order BEFORE publication.
                # Restrictions can affect other events/disciplines, whose current
                # contribution snapshots must also be recalculated.
                from apps.catalogs.models import Discipline
                from apps.ratings.models import RatingContribution
                from apps.ratings.services import calculate_ratings, season_for_year

                # Reuse core event-date eligibility; do not add a competing
                # local-date filtering methodology at year/day boundaries.
                pairs = set(
                    RatingContribution.objects.filter(
                        athlete=case.application.athlete
                    ).values_list("season__year", "discipline_id")
                )
                pairs.add(
                    (
                        case.application.competition.starts_at.year,
                        case.application.competition.discipline_id,
                    )
                )
                for year, discipline_id in sorted(pairs):
                    calculate_ratings(
                        season=season_for_year(year),
                        discipline=Discipline.objects.get(pk=discipline_id),
                        actor=request.user,
                    )
            case.correction_publication = publish_protocol(
                case.application.competition,
                request.user,
                f"Дело №{case.pk}: {data['reason']}",
            )
        case.status = after
        case.revision += 1
        if action in ["accept", "reject"]:
            case.decision, case.decided_by = data["reason"], request.user
            case.appeal_rights = data["appeal_rights"]
        case.save()
        record_step(case, request.user, action, data["reason"])
        return Response(
            {
                "id": case.pk,
                "status": case.status,
                "revision": case.revision,
                "publication": case.correction_publication_id,
            }
        )


class ReviewEvidenceView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @extend_schema(request=EvidenceInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request, pk):
        case = get_object_or_404(ReviewCase.objects.select_for_update(), pk=pk)
        case_access(request, case)
        if case.status in ["accepted", "rejected"]:
            raise ValidationError("Дело закрыто")
        data = validated(EvidenceInput, request.data)
        file = data.get("file")
        content = None
        mime = ""
        if file:
            if file.size > 5 * 1024 * 1024:
                raise ValidationError("Максимальный размер 5 МиБ")
            raw = file.read()
            try:
                if raw.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")):
                    with Image.open(BytesIO(raw)) as img:
                        if img.width * img.height > 20_000_000:
                            raise ValidationError("Слишком большое изображение")
                        img.load()
                        stream = BytesIO()
                        img.convert("RGB").save(stream, format="PNG")
                        content = stream.getvalue()
                        if len(content) > 5 * 1024 * 1024:
                            raise ValidationError(
                                "Изображение после безопасной обработки превышает 5 МиБ"
                            )
                        mime = "image/png"
                elif file.name.lower().endswith(".txt"):
                    raw.decode("utf-8")
                    content = raw
                    mime = "text/plain; charset=utf-8"
                else:
                    raise ValidationError("Допустимы PNG, JPEG и UTF-8 TXT")
            except (
                UnidentifiedImageError,
                OSError,
                ValueError,
                Image.DecompressionBombError,
            ) as exc:
                raise ValidationError("Некорректный файл") from exc
        if not content and not data.get("url"):
            raise ValidationError("Приложите файл или ссылку")
        evidence = ReviewEvidence.objects.create(
            case=case,
            submitted_by=request.user,
            description=data["description"],
            url=data.get("url", ""),
            content=content,
            content_type=mime,
            sha256=hashlib.sha256(content).hexdigest() if content else "",
        )
        audit(
            request.user,
            "review.evidence_added",
            evidence,
            after={"sha256": evidence.sha256},
        )
        return Response({"id": evidence.pk}, status=201)


class EvidenceDownloadView(APIView):
    @extend_schema(responses=OpenApiTypes.BINARY)
    def get(self, request, pk):
        evidence = get_object_or_404(ReviewEvidence, pk=pk)
        case_access(request, evidence.case)
        if not evidence.content:
            raise ValidationError("Для этой записи сохранена внешняя ссылка")
        return private_response(
            bytes(evidence.content),
            evidence.content_type,
            f"evidence-{pk}.{'png' if evidence.content_type == 'image/png' else 'txt'}",
        )


class ReviewPolicyView(APIView):
    @extend_schema(request=PolicyInput, responses={201: OpenApiTypes.OBJECT})
    @transaction.atomic
    def post(self, request):
        require_role(request, "federation")
        serializer = PolicyInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = serializer.save()
        audit(request.user, "review.policy_created", policy)
        return Response({"id": policy.pk}, status=201)
