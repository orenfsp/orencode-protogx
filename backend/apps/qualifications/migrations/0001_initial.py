import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models
from django.db.models import F, Q

RANK_CHOICES = [
    ("youth_3", "III юношеский разряд"),
    ("youth_2", "II юношеский разряд"),
    ("youth_1", "I юношеский разряд"),
    ("adult_3", "III спортивный разряд"),
    ("adult_2", "II спортивный разряд"),
    ("adult_1", "I спортивный разряд"),
    ("cms", "Кандидат в мастера спорта"),
    ("ms", "Мастер спорта России"),
    ("msmk", "Мастер спорта России международного класса"),
]
CATEGORY_CHOICES = [
    ("youth", "Юный спортивный судья"),
    ("third", "Спортивный судья третьей категории"),
    ("second", "Спортивный судья второй категории"),
    ("first", "Спортивный судья первой категории"),
    ("all_russian", "Спортивный судья всероссийской категории"),
]
REQUEST_TYPE_CHOICES = [("assign", "Присвоение"), ("confirm", "Подтверждение")]
STATUS_CHOICES = [("pending", "На рассмотрении"), ("approved", "Присвоено"), ("rejected", "Отклонено")]


def pk():
    return ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"))


def user_fk(related_name, **kwargs):
    return models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name=related_name, to=settings.AUTH_USER_MODEL, **kwargs)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("catalogs", "0002_seed_disciplines"),
        ("competitions", "0005_protocoltemplate_competition_type_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="QualificationRule",
            fields=[
                pk(),
                ("rank", models.CharField(choices=RANK_CHOICES, max_length=16)),
                ("competition_level", models.CharField(max_length=100)),
                ("max_place", models.PositiveSmallIntegerField()),
                ("rule_version", models.CharField(default="demo-1", max_length=50)),
                ("effective_from", models.DateField(blank=True, null=True)),
                ("source_url", models.URLField(blank=True)),
                ("source_verified", models.BooleanField(default=False)),
                ("source_note", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("discipline", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="qualification_rules", to="catalogs.discipline")),
            ],
            options={
                "ordering": ("discipline_id", "rank", "competition_level", "rule_version"),
                "constraints": [
                    models.UniqueConstraint(fields=("discipline", "rank", "competition_level", "rule_version"), name="unique_qualification_rule_version"),
                ],
            },
        ),
        migrations.CreateModel(
            name="RankApplication",
            fields=[
                pk(),
                ("request_type", models.CharField(choices=REQUEST_TYPE_CHOICES, max_length=16)),
                ("requested_rank", models.CharField(choices=RANK_CHOICES, max_length=16)),
                ("comment", models.TextField(blank=True)),
                ("status", models.CharField(choices=STATUS_CHOICES, default="pending", max_length=16)),
                ("decision_reason", models.TextField(blank=True)),
                ("submitted_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("athlete", user_fk("rank_applications")),
                ("competition", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rank_applications", to="competitions.competition")),
                ("decided_by", user_fk("decided_rank_applications", blank=True, null=True)),
                ("discipline", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rank_applications", to="catalogs.discipline")),
                ("result", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rank_applications", to="competitions.result")),
                ("submitted_by", user_fk("submitted_rank_applications")),
            ],
            options={
                "ordering": ("-id",),
                "constraints": [
                    models.UniqueConstraint(condition=Q(("status", "pending")), fields=("result", "requested_rank"), name="unique_pending_rank_application"),
                ],
            },
        ),
        migrations.CreateModel(
            name="SportRankHistory",
            fields=[
                pk(),
                ("rank", models.CharField(choices=RANK_CHOICES, max_length=16)),
                ("order_number", models.CharField(max_length=100)),
                ("assigned_on", models.DateField()),
                ("valid_until", models.DateField()),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("application", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="rank_record", to="qualifications.rankapplication")),
                ("athlete", user_fk("rank_history")),
                ("discipline", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rank_history", to="catalogs.discipline")),
                ("recorded_by", user_fk("recorded_ranks")),
            ],
            options={
                "ordering": ("-assigned_on", "-id"),
                "constraints": [
                    models.CheckConstraint(condition=Q(("valid_until__gt", F("assigned_on"))), name="rank_valid_until_after_assigned"),
                ],
            },
        ),
        migrations.CreateModel(
            name="JudgeCategoryApplication",
            fields=[
                pk(),
                ("request_type", models.CharField(choices=REQUEST_TYPE_CHOICES, max_length=16)),
                ("requested_category", models.CharField(choices=CATEGORY_CHOICES, max_length=16)),
                ("comment", models.TextField(blank=True)),
                ("status", models.CharField(choices=STATUS_CHOICES, default="pending", max_length=16)),
                ("decision_reason", models.TextField(blank=True)),
                ("submitted_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("decided_by", user_fk("decided_category_applications", blank=True, null=True)),
                ("judge", user_fk("category_applications")),
            ],
            options={
                "ordering": ("-id",),
                "constraints": [
                    models.UniqueConstraint(condition=Q(("status", "pending")), fields=("judge",), name="unique_pending_category_application"),
                ],
            },
        ),
        migrations.CreateModel(
            name="JudgeCategoryHistory",
            fields=[
                pk(),
                ("category", models.CharField(choices=CATEGORY_CHOICES, max_length=16)),
                ("order_number", models.CharField(max_length=100)),
                ("assigned_on", models.DateField()),
                ("valid_until", models.DateField()),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("application", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="category_record", to="qualifications.judgecategoryapplication")),
                ("judge", user_fk("category_history")),
                ("recorded_by", user_fk("recorded_categories")),
            ],
            options={
                "ordering": ("-assigned_on", "-id"),
                "constraints": [
                    models.CheckConstraint(condition=Q(("valid_until__gt", F("assigned_on"))), name="category_valid_until_after_assigned"),
                ],
            },
        ),
    ]
