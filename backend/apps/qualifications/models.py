"""AC-09: спортивные разряды и судейские категории.

Заявка → решение федерации → запись в неизменяемой истории со сроком действия.
Записи истории не перезаписываются: подтверждение или повышение создаёт новую строку.
Разряды спортсменов и категории судей ведутся раздельно.
"""

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class SportRank(models.TextChoices):
    # Порядок значений задаёт RANK_ORDER в services.py. Перечень настраиваемый
    # демонстрационный справочник; соответствие официальной ЕВСК не заявляется.
    YOUTH_3 = "youth_3", "III юношеский разряд"
    YOUTH_2 = "youth_2", "II юношеский разряд"
    YOUTH_1 = "youth_1", "I юношеский разряд"
    ADULT_3 = "adult_3", "III спортивный разряд"
    ADULT_2 = "adult_2", "II спортивный разряд"
    ADULT_1 = "adult_1", "I спортивный разряд"
    CMS = "cms", "Кандидат в мастера спорта"
    MS = "ms", "Мастер спорта России"
    MSMK = "msmk", "Мастер спорта России международного класса"


class JudgeCategory(models.TextChoices):
    YOUTH = "youth", "Юный спортивный судья"
    THIRD = "third", "Спортивный судья третьей категории"
    SECOND = "second", "Спортивный судья второй категории"
    FIRST = "first", "Спортивный судья первой категории"
    ALL_RUSSIAN = "all_russian", "Спортивный судья всероссийской категории"


class RequestType(models.TextChoices):
    ASSIGN = "assign", "Присвоение"
    CONFIRM = "confirm", "Подтверждение"


class ReviewStatus(models.TextChoices):
    PENDING = "pending", "На рассмотрении"
    APPROVED = "approved", "Присвоено"
    REJECTED = "rejected", "Отклонено"


class QualificationRule(models.Model):
    """Настраиваемый критерий для предварительной подсказки «результат может подойти».

    Подсказка не является присвоением разряда. Демонстрационные правила имеют
    source_verified=False, пока федерация не сверит их с первоисточником ЕВСК.
    """

    discipline = models.ForeignKey("catalogs.Discipline", on_delete=models.PROTECT, related_name="qualification_rules")
    rank = models.CharField(max_length=16, choices=SportRank.choices)
    competition_level = models.CharField(max_length=100)
    max_place = models.PositiveSmallIntegerField()
    rule_version = models.CharField(max_length=50, default="demo-1")
    effective_from = models.DateField(null=True, blank=True)
    source_url = models.URLField(blank=True)
    source_verified = models.BooleanField(default=False)
    source_note = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("discipline_id", "rank", "competition_level", "rule_version")
        constraints = [
            models.UniqueConstraint(
                fields=["discipline", "rank", "competition_level", "rule_version"],
                name="unique_qualification_rule_version",
            ),
        ]


class RankApplication(models.Model):
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="rank_applications")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="submitted_rank_applications")
    request_type = models.CharField(max_length=16, choices=RequestType.choices)
    requested_rank = models.CharField(max_length=16, choices=SportRank.choices)
    discipline = models.ForeignKey("catalogs.Discipline", on_delete=models.PROTECT, related_name="rank_applications")
    competition = models.ForeignKey("competitions.Competition", on_delete=models.PROTECT, related_name="rank_applications")
    result = models.ForeignKey("competitions.Result", on_delete=models.PROTECT, related_name="rank_applications")
    publication = models.ForeignKey("competitions.ProtocolPublication", null=True, blank=True, on_delete=models.PROTECT, related_name="rank_applications")
    result_snapshot = models.JSONField(null=True, blank=True)
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    decision_reason = models.TextField(blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="decided_rank_applications")
    submitted_at = models.DateTimeField(default=timezone.now)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-id",)
        constraints = [
            models.UniqueConstraint(
                fields=["result", "requested_rank"],
                condition=Q(status="pending"),
                name="unique_pending_rank_application",
            ),
        ]


class SportRankHistory(models.Model):
    athlete = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="rank_history")
    discipline = models.ForeignKey("catalogs.Discipline", on_delete=models.PROTECT, related_name="rank_history")
    rank = models.CharField(max_length=16, choices=SportRank.choices)
    application = models.OneToOneField(RankApplication, on_delete=models.PROTECT, related_name="rank_record")
    order_number = models.CharField(max_length=100)
    assigned_on = models.DateField()
    valid_until = models.DateField()
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_ranks")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-assigned_on", "-id")
        constraints = [
            models.CheckConstraint(condition=Q(valid_until__gt=F("assigned_on")), name="rank_valid_until_after_assigned"),
        ]


class JudgeCategoryApplication(models.Model):
    judge = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="category_applications")
    request_type = models.CharField(max_length=16, choices=RequestType.choices)
    requested_category = models.CharField(max_length=16, choices=JudgeCategory.choices)
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    decision_reason = models.TextField(blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="decided_category_applications")
    submitted_at = models.DateTimeField(default=timezone.now)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-id",)
        constraints = [
            models.UniqueConstraint(fields=["judge"], condition=Q(status="pending"), name="unique_pending_category_application"),
        ]


class JudgeCategoryHistory(models.Model):
    judge = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="category_history")
    category = models.CharField(max_length=16, choices=JudgeCategory.choices)
    application = models.OneToOneField(JudgeCategoryApplication, on_delete=models.PROTECT, related_name="category_record")
    order_number = models.CharField(max_length=100)
    assigned_on = models.DateField()
    valid_until = models.DateField()
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_categories")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-assigned_on", "-id")
        constraints = [
            models.CheckConstraint(condition=Q(valid_until__gt=F("assigned_on")), name="category_valid_until_after_assigned"),
        ]


class QualificationCorrection(models.Model):
    """Append-only revisions; history rows are the current projection of this ledger."""
    rank_record = models.ForeignKey(SportRankHistory, null=True, on_delete=models.PROTECT, related_name="corrections")
    category_record = models.ForeignKey(JudgeCategoryHistory, null=True, on_delete=models.PROTECT, related_name="corrections")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.TextField()
    before = models.JSONField()
    after = models.JSONField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.CheckConstraint(condition=(Q(rank_record__isnull=False, category_record__isnull=True) | Q(rank_record__isnull=True, category_record__isnull=False)), name="qualification_correction_one_target")]
