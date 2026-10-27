"""Правила AC-09. Права и состояния проверяются здесь и во views, а не во frontend."""

from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.competitions.models import CoachAthleteLink, ProtocolPublication, Result
from apps.competitions.services import audit

from .models import (
    JudgeCategory,
    JudgeCategoryApplication,
    JudgeCategoryHistory,
    QualificationRule,
    RankApplication,
    RequestType,
    ReviewStatus,
    SportRank,
    SportRankHistory,
)

RANK_ORDER = [value for value, _ in SportRank.choices]
CATEGORY_ORDER = [value for value, _ in JudgeCategory.choices]
EXPIRY_WARNING_DAYS = 60
HINT_DISCLAIMER = "Предварительная подсказка по настроенным правилам; не является присвоением разряда."


def rank_level(rank):
    return RANK_ORDER.index(rank)


def category_level(category):
    return CATEGORY_ORDER.index(category)


def days_left(valid_until: date, today: date) -> int:
    return (valid_until - today).days


def validity_state(valid_until: date, today: date, warn_days: int = EXPIRY_WARNING_DAYS) -> str:
    left = days_left(valid_until, today)
    if left < 0:
        return "expired"
    return "expiring" if left <= warn_days else "active"


def most_significant(records, level):
    """Запись, определяющая «текущий» уровень человека.

    Среди действующих берётся высший уровень (при равенстве — с наибольшим сроком); если
    действующих нет — тот же отбор среди истёкших, чтобы просрочка оставалась видна.
    """
    today = timezone.localdate()
    records = list(records)
    valid = [r for r in records if r.valid_until >= today]
    pool = valid or records
    if not pool:
        return None
    return max(pool, key=lambda r: (level(r.rank if hasattr(r, "rank") else r.category), r.valid_until, r.pk))


def current_rank_record(athlete_id):
    return most_significant(SportRankHistory.objects.filter(athlete_id=athlete_id), rank_level)


def current_category_record(judge_id):
    return most_significant(JudgeCategoryHistory.objects.filter(judge_id=judge_id), category_level)


def has_confirmed_link(coach, athlete_id, discipline_id) -> bool:
    return CoachAthleteLink.objects.filter(coach=coach, athlete_id=athlete_id, discipline_id=discipline_id, status="confirmed").exists()


def athlete_has_coach(athlete_id, discipline_id) -> bool:
    return CoachAthleteLink.objects.filter(athlete_id=athlete_id, discipline_id=discipline_id, status="confirmed").exists()


def hint_for(result, rules):
    """Лучшее подходящее правило для результата либо None. Только предварительная подсказка."""
    if result.status != Result.Status.CLASSIFIED or result.place is None:
        return None
    competition = result.application.competition
    level = competition.level.strip().casefold()
    matched = [
        rule for rule in rules
        if rule.discipline_id == competition.discipline_id
        and rule.competition_level.strip().casefold() == level
        and result.place <= rule.max_place
    ]
    return max(matched, key=lambda rule: rank_level(rule.rank)) if matched else None


def active_rules():
    return list(QualificationRule.objects.filter(is_active=True).order_by("pk"))


# ---------- разряды ----------

def validate_rank_submission(user, role, result_id, requested_rank, request_type):
    """Возвращает (result, athlete) либо поднимает ошибку. Роль уже проверена require_role."""
    try:
        result = Result.objects.select_related("application__athlete", "application__competition").get(pk=result_id)
    except Result.DoesNotExist:
        raise ValidationError({"result": "Результат не найден"})
    application = result.application
    athlete, competition = application.athlete, application.competition

    if role == "athlete":
        if athlete.pk != user.pk:
            raise PermissionDenied("Спортсмен подаёт заявку только за себя")
        if athlete_has_coach(athlete.pk, competition.discipline_id):
            raise ValidationError("У вас есть подтверждённый тренер по этой дисциплине: заявку подаёт тренер")
    elif role == "coach":
        if not has_confirmed_link(user, athlete.pk, competition.discipline_id):
            raise PermissionDenied("Нужна подтверждённая связь с этим спортсменом по дисциплине")
    else:  # защитная ветка: вызывающий код допускает только athlete и coach
        raise PermissionDenied("Недопустимая роль")

    if result.status != Result.Status.CLASSIFIED:
        raise ValidationError({"result": "Заявка возможна только на классифицированный результат"})
    if result.validated_by_id is None:
        raise ValidationError({"result": "Результат ещё не проверен федерацией"})
    if not ProtocolPublication.objects.filter(competition=competition).exists():
        raise ValidationError({"result": "Протокол соревнования не опубликован"})
    if RankApplication.objects.filter(result=result, requested_rank=requested_rank, status=ReviewStatus.PENDING).exists():
        raise ValidationError("Такая заявка уже находится на рассмотрении")

    history = SportRankHistory.objects.filter(athlete=athlete)
    if request_type == RequestType.ASSIGN:
        current = current_rank_record(athlete.pk)
        if current and current.valid_until >= timezone.localdate() and rank_level(requested_rank) <= rank_level(current.rank):
            raise ValidationError({"requested_rank": "Запрашиваемый разряд должен быть выше действующего"})
    elif not history.filter(rank=requested_rank).exists():
        raise ValidationError({"requested_rank": "Подтверждать можно только ранее присвоенный разряд"})
    return result, athlete


@transaction.atomic
def create_rank_application(user, role, data):
    result, athlete = validate_rank_submission(user, role, data["result"], data["requested_rank"], data["request_type"])
    competition = result.application.competition
    application = RankApplication.objects.create(
        athlete=athlete, submitted_by=user, request_type=data["request_type"], requested_rank=data["requested_rank"],
        discipline_id=competition.discipline_id, competition=competition, result=result, comment=data.get("comment", ""),
    )
    audit(user, "rank_application.submitted", application, competition=competition,
          after={"athlete": athlete.pk, "rank": application.requested_rank, "request_type": application.request_type, "result": result.pk})
    return application


def _check_decision(status, reason, order_number, assigned_on, valid_until):
    if status == ReviewStatus.REJECTED:
        if not reason.strip():
            raise ValidationError({"reason": "Для отказа нужна причина"})
        return
    errors = {}
    if not order_number.strip():
        errors["order_number"] = "Укажите номер приказа"
    if assigned_on is None:
        errors["assigned_on"] = "Укажите дату присвоения"
    if valid_until is None:
        errors["valid_until"] = "Укажите срок действия"
    if errors:
        raise ValidationError(errors)
    if assigned_on > timezone.localdate():
        raise ValidationError({"assigned_on": "Дата присвоения не может быть в будущем"})
    if valid_until <= assigned_on:
        raise ValidationError({"valid_until": "Срок действия должен быть позже даты присвоения"})


@transaction.atomic
def decide_rank_application(application_id, actor, data):
    try:
        application = RankApplication.objects.select_for_update().select_related("competition").get(pk=application_id)
    except RankApplication.DoesNotExist:
        return None
    if application.status != ReviewStatus.PENDING:
        raise ValidationError("Решение можно принять только по заявке на рассмотрении")
    status, reason = data["status"], data.get("reason", "")
    _check_decision(status, reason, data.get("order_number", ""), data.get("assigned_on"), data.get("valid_until"))
    application.status = status
    application.decision_reason = reason if status == ReviewStatus.REJECTED else ""
    application.decided_by = actor
    application.decided_at = timezone.now()
    application.save(update_fields=["status", "decision_reason", "decided_by", "decided_at"])
    after = {"status": status, "rank": application.requested_rank, "athlete": application.athlete_id}
    if status == ReviewStatus.APPROVED:
        record = SportRankHistory.objects.create(
            athlete_id=application.athlete_id, discipline_id=application.discipline_id, rank=application.requested_rank,
            application=application, order_number=data["order_number"].strip(), assigned_on=data["assigned_on"],
            valid_until=data["valid_until"], recorded_by=actor,
        )
        after.update({"history": record.pk, "valid_until": record.valid_until.isoformat()})
    audit(actor, f"rank_application.{status}", application, competition=application.competition, before={"status": "pending"}, after=after)
    return application


# ---------- судейские категории ----------

def validate_category_submission(judge, requested_category, request_type):
    history = JudgeCategoryHistory.objects.filter(judge=judge)
    if JudgeCategoryApplication.objects.filter(judge=judge, status=ReviewStatus.PENDING).exists():
        raise ValidationError("У вас уже есть заявка на рассмотрении")
    if request_type == RequestType.ASSIGN:
        current = current_category_record(judge.pk)
        if current and current.valid_until >= timezone.localdate() and category_level(requested_category) <= category_level(current.category):
            raise ValidationError({"requested_category": "Запрашиваемая категория должна быть выше действующей"})
    elif not history.filter(category=requested_category).exists():
        raise ValidationError({"requested_category": "Подтверждать можно только ранее присвоенную категорию"})


@transaction.atomic
def create_category_application(judge, data):
    validate_category_submission(judge, data["requested_category"], data["request_type"])
    application = JudgeCategoryApplication.objects.create(
        judge=judge, request_type=data["request_type"], requested_category=data["requested_category"], comment=data.get("comment", ""),
    )
    audit(judge, "judge_category_application.submitted", application,
          after={"category": application.requested_category, "request_type": application.request_type})
    return application


@transaction.atomic
def decide_category_application(application_id, actor, data):
    try:
        application = JudgeCategoryApplication.objects.select_for_update().get(pk=application_id)
    except JudgeCategoryApplication.DoesNotExist:
        return None
    if application.status != ReviewStatus.PENDING:
        raise ValidationError("Решение можно принять только по заявке на рассмотрении")
    status, reason = data["status"], data.get("reason", "")
    _check_decision(status, reason, data.get("order_number", ""), data.get("assigned_on"), data.get("valid_until"))
    application.status = status
    application.decision_reason = reason if status == ReviewStatus.REJECTED else ""
    application.decided_by = actor
    application.decided_at = timezone.now()
    application.save(update_fields=["status", "decision_reason", "decided_by", "decided_at"])
    after = {"status": status, "category": application.requested_category, "judge": application.judge_id}
    if status == ReviewStatus.APPROVED:
        record = JudgeCategoryHistory.objects.create(
            judge_id=application.judge_id, category=application.requested_category, application=application,
            order_number=data["order_number"].strip(), assigned_on=data["assigned_on"], valid_until=data["valid_until"], recorded_by=actor,
        )
        after.update({"history": record.pk, "valid_until": record.valid_until.isoformat()})
    audit(actor, f"judge_category_application.{status}", application, before={"status": "pending"}, after=after)
    return application
