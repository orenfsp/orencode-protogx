import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("catalogs", "0002_seed_disciplines"),
        ("competitions", "0005_protocoltemplate_competition_type_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(name="RatingSeason", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("year", models.PositiveSmallIntegerField(unique=True)), ("name", models.CharField(max_length=100)), ("is_active", models.BooleanField(default=True)),
        ], options={"ordering": ("-year",)}),
        migrations.CreateModel(name="RatingRuleVersion", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("version", models.PositiveIntegerField()),
            ("effective_from", models.DateField(blank=True, null=True)), ("effective_until", models.DateField(blank=True, null=True)),
            ("coefficient_threshold", models.PositiveSmallIntegerField(default=2)), ("stability_coefficient", models.DecimalField(decimal_places=2, default="1.20", max_digits=4)),
            ("rounding_places", models.PositiveSmallIntegerField(default=2)), ("rounding_mode", models.CharField(default="ROUND_HALF_UP", max_length=20)),
            ("is_active", models.BooleanField(default=True)), ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_rating_rules", to=settings.AUTH_USER_MODEL)),
            ("discipline", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rating_rule_versions", to="catalogs.discipline")),
            ("season", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rule_versions", to="ratings.ratingseason")),
        ], options={"ordering": ("season_id", "discipline_id", "-version")}),
        migrations.CreateModel(name="RatingContribution", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("application_id", models.PositiveBigIntegerField()),
            ("result_snapshot", models.JSONField(default=dict)), ("placement", models.PositiveSmallIntegerField()), ("age_group", models.CharField(blank=True, max_length=100)),
            ("awarded_points", models.DecimalField(decimal_places=2, max_digits=8)), ("is_current", models.BooleanField(default=True)),
            ("superseded_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("athlete", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rating_contributions", to=settings.AUTH_USER_MODEL)),
            ("competition", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rating_contributions", to="competitions.competition")),
            ("discipline", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rating_contributions", to="catalogs.discipline")),
            ("publication", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rating_contributions", to="competitions.protocolpublication")),
            ("rule_version", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="contributions", to="ratings.ratingruleversion")),
            ("season", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="contributions", to="ratings.ratingseason")),
        ], options={"ordering": ("-awarded_points", "competition__starts_at", "pk")}),
        migrations.CreateModel(name="AthleteRating", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("base_score", models.DecimalField(decimal_places=2, max_digits=10)),
            ("prize_count", models.PositiveIntegerField(default=0)), ("coefficient", models.DecimalField(decimal_places=2, max_digits=4)), ("rating_score", models.DecimalField(decimal_places=2, max_digits=10)),
            ("calculated_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("athlete", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ratings", to=settings.AUTH_USER_MODEL)),
            ("discipline", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="athlete_ratings", to="catalogs.discipline")),
            ("rule_version", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ratings", to="ratings.ratingruleversion")),
            ("season", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ratings", to="ratings.ratingseason")),
        ], options={"ordering": ("-rating_score", "athlete_id")}),
        migrations.CreateModel(name="AthleteRestriction", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("kind", models.CharField(choices=[("suspension", "Приостановление"), ("disqualification", "Дисквалификация")], max_length=24)),
            ("starts_at", models.DateField()), ("ends_at", models.DateField()), ("status", models.CharField(choices=[("active", "Активно"), ("revoked", "Отменено")], default="active", max_length=16)),
            ("reason_private", models.TextField(blank=True)), ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
            ("athlete", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rating_restrictions", to=settings.AUTH_USER_MODEL)),
            ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_rating_restrictions", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ("-starts_at", "-pk"), "constraints": [models.CheckConstraint(condition=models.Q(ends_at__gte=models.F("starts_at")), name="restriction_end_after_start")]}),
        migrations.CreateModel(name="RatingPointRule", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("competition_level", models.CharField(max_length=100)),
            ("place", models.PositiveSmallIntegerField()), ("points", models.DecimalField(decimal_places=2, max_digits=8)),
            ("rule_version", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="point_rules", to="ratings.ratingruleversion")),
        ], options={"ordering": ("competition_level", "place"), "constraints": [models.UniqueConstraint(fields=("rule_version", "competition_level", "place"), name="unique_rating_point_rule"), models.CheckConstraint(condition=models.Q(place__gte=1), name="rating_place_positive")]}),
        migrations.AddConstraint(model_name="ratingruleversion", constraint=models.UniqueConstraint(fields=("season", "discipline", "version"), name="unique_rating_rule_version")),
        migrations.AddConstraint(model_name="ratingruleversion", constraint=models.CheckConstraint(condition=models.Q(coefficient_threshold__gte=1), name="rating_threshold_positive")),
        migrations.AddConstraint(model_name="ratingcontribution", constraint=models.UniqueConstraint(condition=models.Q(is_current=True), fields=("athlete", "competition", "season", "discipline"), name="unique_current_rating_contribution")),
        migrations.AddConstraint(model_name="athleterating", constraint=models.UniqueConstraint(fields=("athlete", "season", "discipline"), name="unique_athlete_rating")),
    ]
