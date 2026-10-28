from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import User
from apps.competitions.models import AuditEvent

from .notifications import notify


@receiver(post_save, sender=AuditEvent, dispatch_uid="fsp_extension_outbox")
def domain_event(sender, instance, created, **kwargs):
    if not created:
        return
    event = instance
    if event.action == "competition.published":
        recipients = User.objects.filter(is_active=True, role_assignments__role="athlete")
    elif event.competition_id and event.action in ("application.decided", "protocol.published"):
        recipients = User.objects.filter(competition_applications__competition_id=event.competition_id, competition_applications__status="approved")
        if event.action == "application.decided":
            recipients = recipients.filter(competition_applications__pk=event.target_id)
    else:
        return
    for user in recipients.distinct():
        notify(user, f"audit:{event.pk}", {"competition.published": "Открыто соревнование", "application.decided": "Изменён статус заявки", "protocol.published": "Опубликована версия протокола"}[event.action])
