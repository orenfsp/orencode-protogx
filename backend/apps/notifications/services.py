from datetime import date, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.competitions.models import CoachAthleteLink, Competition

from .models import Notification, ReportDeadline

ROLES = ("federation", "athlete", "coach", "judge")
BODY = "В личном кабинете появилось новое событие. Войдите на платформу ФСП для просмотра подробностей."


def visible_notifications(user, role):
    links = CoachAthleteLink.objects.filter(coach=user, athlete_id=OuterRef("subject_id"), discipline_id=OuterRef("discipline_id"), status="confirmed")
    return Notification.objects.filter(recipient=user, role=role).annotate(linked=Exists(links)).filter(
        Q(role__in=["federation", "athlete", "judge"]) | Q(subject__isnull=True) | Q(linked=True)
    )


def queue(event_key, kind, title, recipients, *, subject=None, discipline=None):
    """Caller must share the domain transaction. Unique key also protects scheduler replays."""
    for person_id, role in set(recipients):
        if UserRole.objects.filter(user_id=person_id, role=role, user__is_active=True).exists():
            Notification.objects.get_or_create(event_key=event_key, recipient_id=person_id, role=role, defaults={
                "kind": kind, "title": title, "body": BODY, "subject": subject, "discipline": discipline,
            })


def federation_recipients():
    return list(UserRole.objects.filter(role="federation").values_list("user_id", "role"))


def athlete_recipients(athlete_id, discipline_id):
    coaches = CoachAthleteLink.objects.filter(athlete_id=athlete_id, discipline_id=discipline_id, status="confirmed").values_list("coach_id", flat=True)
    return [(athlete_id, "athlete")] + [(pk, "coach") for pk in coaches]


def domain_event(action, target):
    """Called synchronously by the existing audit service inside the domain transaction."""
    recipients, subject, discipline = [], None, None
    title = None
    if action == "competition.published":
        recipients = list(UserRole.objects.filter(role__in=["federation", "athlete", "coach"]).values_list("user_id", "role"))
        title = "Открыта регистрация на соревнование"
    elif action in ("application.submitted", "application.decided"):
        subject, discipline = target.athlete, target.competition.discipline
        recipients = athlete_recipients(target.athlete_id, target.competition.discipline_id)
        if action.endswith("submitted"):
            recipients += federation_recipients()
        title = "Заявка на соревнование принята" if action.endswith("submitted") else "Изменён статус заявки на соревнование"
    elif action == "protocol.published":
        recipients = federation_recipients()
        # Separate per-athlete queue items allow scope to be rechecked later.
        for application in target.competition.applications.filter(status="approved").select_related("athlete"):
            queue(f"protocol:{target.pk}:{application.athlete_id}", action, "Опубликован протокол соревнования", athlete_recipients(application.athlete_id, target.competition.discipline_id), subject=application.athlete, discipline=target.competition.discipline)
        title = "Опубликован протокол соревнования"
    elif action.startswith("rank_application."):
        subject, discipline = target.athlete, target.discipline
        recipients = athlete_recipients(target.athlete_id, target.discipline_id) + federation_recipients()
        title = "Обновлена заявка на спортивный разряд"
    elif action.startswith("judge_category_application."):
        recipients = [(target.judge_id, "judge")] + federation_recipients()
        title = "Обновлена заявка на судейскую категорию"
    elif action == "competition.registration_changed" and target.registration_open:
        recipients = list(UserRole.objects.filter(role__in=["athlete", "coach"]).values_list("user_id", "role"))
        # The audit event id distinguishes repeated close/reopen transitions.
        from apps.competitions.models import AuditEvent
        event = AuditEvent.objects.filter(action=action, target_type="competition", target_id=target.pk).first()
        queue(f"registration-reopened:{event.pk}", action, "Возобновлён приём заявок на соревнование", recipients)
    if title:
        # Status changes use distinct keys, publication pk identifies immutable version.
        suffix = getattr(target, "status", "")
        queue(f"{action}:{target.pk}:{suffix}", action, title, recipients, subject=subject, discipline=discipline)


def dispatch(limit=100):
    """Serialize each send using PostgreSQL row locks; SMTP provides at-least-once delivery."""
    handled = 0
    for _ in range(limit):
        with transaction.atomic():
            notification = Notification.objects.select_for_update(skip_locked=True).filter(
                status="pending", next_attempt_at__lte=timezone.now()
            ).order_by("id").first()
            if notification is None:
                break
            handled += 1
            user = notification.recipient
            if (not user.is_active or not user.role_assignments.filter(role=notification.role).exists()
                    or not visible_notifications(user, notification.role).filter(pk=notification.pk).exists()):
                notification.status = "cancelled"
                notification.save(update_fields=["status"])
                continue
            notification.attempts += 1
            try:
                if send_mail(notification.title, notification.body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False) != 1:
                    raise RuntimeError("No delivery accepted")
            except Exception as error:
                # Store only a class name; provider errors can contain credentials or PII.
                notification.error_code = type(error).__name__[:80]
                notification.status = "failed" if notification.attempts >= 5 else "pending"
                notification.next_attempt_at = timezone.now() + timedelta(seconds=min(3600, 60 * 2 ** (notification.attempts - 1)))
            else:
                notification.status = "sent"
                notification.sent_at = timezone.now()
                notification.error_code = ""
            notification.save()
    return handled


@transaction.atomic
def schedule_deadlines(today=None):
    from apps.qualifications.models import JudgeCategoryHistory, SportRankHistory
    from apps.qualifications.services import (
        category_level,
        most_significant,
        rank_level,
    )

    today = today or timezone.localdate()
    for competition in Competition.objects.filter(state="published", registration_open=True, registration_deadline__date__gte=today, registration_deadline__date__lte=today + timedelta(days=7)):
        recipients = list(UserRole.objects.filter(role__in=["athlete", "coach", "federation"]).values_list("user_id", "role"))
        queue(f"registration-deadline:{competition.pk}:{competition.registration_deadline.isoformat()}", "deadline.registration", f"Приём заявок завершается {timezone.localtime(competition.registration_deadline):%d.%m.%Y}", recipients)
    # Group sports ranks by person AND discipline so one discipline cannot hide another.
    for model, person_field, level, kind, role in [
        (SportRankHistory, "athlete", rank_level, "rank", "athlete"),
        (JudgeCategoryHistory, "judge", category_level, "judge_category", "judge"),
    ]:
        groups = {}
        for record in model.objects.all():
            group = (getattr(record, person_field + "_id"), getattr(record, "discipline_id", None))
            groups.setdefault(group, []).append(record)
        for (person_id, discipline_id), records in groups.items():
            record = most_significant(records, level)
            if 0 <= (record.valid_until - today).days <= 60:
                recipients = athlete_recipients(person_id, discipline_id) if role == "athlete" else [(person_id, role)]
                queue(f"expiry:{kind}:{record.pk}:{record.valid_until}", f"deadline.{kind}", f"Срок разряда или категории истекает {record.valid_until:%d.%m.%Y}", recipients + federation_recipients(), subject=getattr(record, person_field), discipline=getattr(record, "discipline", None))
    due = date(today.year, 2, 1)
    if due < today:
        due = date(today.year + 1, 2, 1)
    if (due - today).days <= 60:
        queue(f"premium:{due}", "deadline.premium", "Ходатайства на премии Губернатора: до 1 февраля", federation_recipients())
    for deadline in ReportDeadline.objects.filter(due_on__gte=today, due_on__lte=today + timedelta(days=30)):
        queue(f"report:{deadline.pk}:{deadline.due_on}", "deadline.report", f"Срок отчёта федерации: {deadline.due_on:%d.%m.%Y}", federation_recipients())
