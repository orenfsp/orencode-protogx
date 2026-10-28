from datetime import date, datetime, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import PersonalDataConsent, User, UserRole
from apps.catalogs.models import Discipline
from apps.competitions.models import (
    AgeGroup,
    Application,
    Competition,
    ProtocolPublication,
    ProtocolTemplate,
    Result,
)
from apps.ratings.models import (
    AthleteRestriction,
    RatingContribution,
    RatingPointRule,
    RatingRuleVersion,
    RatingSeason,
)
from apps.ratings.services import (
    calculate_ratings,
    create_rule_version,
    ensure_default_rule,
)


class RatingDomainTests(TestCase):
    def test_public_minor_rating_redacts_identity_and_raw_protocol_fields(self):
        self.athlete.date_of_birth = date(2015, 1, 1)
        self.athlete.save()
        season = RatingSeason.objects.create(year=2026, name="Сезон 2026")
        competition = self.competition("Regional")
        self.publish(competition, [self.row(self.athlete, 1)])
        calculate_ratings(season=season, discipline=self.discipline, actor=self.federation)
        client = APIClient()
        path = "/api/v1/ratings/?season=2026&discipline=algorithmic"
        item = client.get(path).data["items"][0]
        self.assertEqual(item["athlete_name"], f"Спортсмен №{self.athlete.pk}")
        self.assertNotIn("athlete", item["breakdown"][0]["source_snapshot"])
        client.force_login(self.federation)
        session = client.session
        session["active_role"] = "federation"
        session.save()
        self.assertEqual(client.get(path).data["items"][0]["athlete_name"], self.athlete.full_name)

    def test_russian_case_levels_and_federal_competition_types_map_precisely(self):
        season = RatingSeason.objects.create(year=2026, name="Сезон 2026")
        championship = self.competition("Всероссийское", days=1)
        championship.competition_type = "Чемпионат"
        championship.save()
        youth = self.competition("Всероссийское", days=2)
        youth.competition_type = "Первенство"
        youth.save()
        cup = self.competition("Всероссийское", days=3)
        cup.competition_type = "Кубок"
        cup.save()
        for competition in (championship, youth, cup):
            self.publish(competition, [self.row(self.athlete, 1)])
        calculate_ratings(season=season, discipline=self.discipline, actor=self.federation)
        rating = self.athlete.ratings.get(season=season, discipline=self.discipline)
        self.assertEqual(rating.base_score, Decimal("180.00"))
        self.assertEqual(rating.prize_count, 2)
        self.assertEqual(rating.rating_score, Decimal("216.00"))

    def test_current_suspension_excluded_without_rewriting_past_contributions(self):
        season = RatingSeason.objects.create(year=2026, name="Сезон 2026")
        competition = self.competition("Regional")
        self.publish(competition, [self.row(self.athlete, 1)])
        calculate_ratings(season=season, discipline=self.discipline, actor=self.federation)
        restriction = AthleteRestriction.objects.create(athlete=self.athlete, kind="suspension", starts_at=timezone.localdate(), ends_at=timezone.localdate() + timedelta(days=5), created_by=self.federation)
        client = APIClient()
        self.assertEqual(client.get("/api/v1/ratings/?season=2026&discipline=algorithmic").data["total"], 0)
        self.assertEqual(RatingContribution.objects.filter(athlete=self.athlete, is_current=True).count(), 1)
        restriction.status = "revoked"
        restriction.save()
        self.assertEqual(client.get("/api/v1/ratings/?season=2026&discipline=algorithmic").data["total"], 1)

    def setUp(self):
        self.federation = self.user("fed", "federation")
        self.athlete = self.user("athlete", "athlete")
        self.second = self.user("second", "athlete")
        self.discipline = Discipline.objects.get(code="algorithmic")
        self.other_discipline = Discipline.objects.get(code="product")
        self.age_group = AgeGroup.objects.first()
        self.template = ProtocolTemplate.objects.filter(discipline=self.discipline).first()
        PersonalDataConsent.objects.create(user=self.athlete, text_version="test-v1")
        PersonalDataConsent.objects.create(user=self.second, text_version="test-v1")

    def user(self, email, role):
        user = User.objects.create_user(email=f"{email}@test.invalid", password="SafePassphrase2048!", full_name=email.title(), date_of_birth=date(2000, 1, 1))
        UserRole.objects.create(user=user, role=role)
        return user

    def competition(self, level, discipline=None, days=1):
        discipline = discipline or self.discipline
        return Competition.objects.create(
            title=f"{level} {days}", discipline=discipline, level=level, competition_type="championship", format="online",
            starts_at=timezone.make_aware(datetime(2026, 4, 1) + timedelta(days=days)), ends_at=timezone.make_aware(datetime(2026, 4, 2) + timedelta(days=days)),
            registration_deadline=timezone.make_aware(datetime(2026, 3, 1)), location="Demo", regulations="Demo", template=self.template,
            state=Competition.State.PUBLISHED, created_by=self.federation,
        )

    def publish(self, competition, rows, version=1):
        return ProtocolPublication.objects.create(
            competition=competition, version=version, template=competition.template, snapshot={"rows": rows}, published_by=self.federation,
        )

    def row(self, athlete, place, age_group=None):
        return {"athlete_id": athlete.pk, "application_id": athlete.pk, "athlete": athlete.full_name, "age_group": age_group or self.age_group.name, "status": "classified", "place": place, "score": "100"}

    def test_exact_default_table_and_no_fourth_place_points(self):
        season = RatingSeason.objects.create(year=2026, name="Сезон 2026")
        rule = ensure_default_rule(season, self.discipline, self.federation)
        points = {(item.competition_level, item.place): item.points for item in RatingPointRule.objects.filter(rule_version=rule)}
        self.assertEqual(points[("Russian Championship", 1)], Decimal("100.00"))
        self.assertEqual(points[("Russian Championship", 2)], Decimal("80.00"))
        self.assertEqual(points[("Russian Championship", 3)], Decimal("60.00"))
        self.assertNotIn(("Russian Championship", 4), points)

    def test_two_podium_finishes_apply_stability_and_republication_is_not_duplicate(self):
        season = RatingSeason.objects.create(year=2026, name="Сезон 2026")
        first = self.competition("Regional", days=1)
        second = self.competition("Regional", days=20)
        self.publish(first, [self.row(self.athlete, 1)])
        self.publish(second, [self.row(self.athlete, 2)])
        calculate_ratings(season=season, discipline=self.discipline, actor=self.federation)
        rating = self.athlete.ratings.get(season=season, discipline=self.discipline)
        self.assertEqual(rating.base_score, Decimal("70.00"))
        self.assertEqual(rating.coefficient, Decimal("1.20"))
        self.assertEqual(rating.rating_score, Decimal("84.00"))
        self.assertEqual(RatingContribution.objects.filter(athlete=self.athlete, is_current=True).count(), 2)
        self.publish(first, [self.row(self.athlete, 3)], version=2)
        calculate_ratings(season=season, discipline=self.discipline, actor=self.federation)
        self.assertEqual(self.athlete.ratings.get(season=season, discipline=self.discipline).base_score, Decimal("50.00"))
        self.assertEqual(RatingContribution.objects.filter(athlete=self.athlete, is_current=True).count(), 2)
        self.assertEqual(RatingContribution.objects.filter(athlete=self.athlete, is_current=False).count(), 2)

    def test_seasons_and_disciplines_are_isolated_and_active_restriction_excludes(self):
        season = RatingSeason.objects.create(year=2026, name="Сезон 2026")
        other_season = RatingSeason.objects.create(year=2025, name="Сезон 2025")
        competition = self.competition("Regional")
        self.publish(competition, [self.row(self.athlete, 1)])
        calculate_ratings(season=season, discipline=self.discipline, actor=self.federation)
        self.assertTrue(self.athlete.ratings.filter(season=season, discipline=self.discipline).exists())
        self.assertFalse(self.athlete.ratings.filter(season=other_season).exists())
        event_day = competition.starts_at.date()
        AthleteRestriction.objects.create(athlete=self.athlete, kind="suspension", starts_at=event_day - timedelta(days=1), ends_at=event_day + timedelta(days=1), created_by=self.federation)
        calculate_ratings(season=season, discipline=self.discipline, actor=self.federation)
        self.assertFalse(self.athlete.ratings.filter(season=season, discipline=self.discipline).exists())

    def test_future_and_expired_restrictions_do_not_exclude(self):
        season = RatingSeason.objects.create(year=2026, name="Сезон 2026")
        competition = self.competition("Regional")
        self.publish(competition, [self.row(self.athlete, 1)])
        event_day = competition.starts_at.date()
        AthleteRestriction.objects.create(athlete=self.athlete, kind="suspension", starts_at=event_day + timedelta(days=2), ends_at=event_day + timedelta(days=3), created_by=self.federation)
        AthleteRestriction.objects.create(athlete=self.second, kind="disqualification", starts_at=event_day - timedelta(days=3), ends_at=event_day - timedelta(days=1), created_by=self.federation)
        calculate_ratings(season=season, discipline=self.discipline, actor=self.federation)
        self.assertTrue(self.athlete.ratings.filter(season=season).exists())

    def test_protocol_publication_recalculates_rating_from_its_snapshot(self):
        season = RatingSeason.objects.create(year=2026, name="Сезон 2026")
        competition = self.competition("Regional")
        application = Application.objects.create(
            competition=competition, athlete=self.athlete, age_group=self.age_group,
            submitted_by=self.athlete, status=Application.Status.APPROVED,
        )
        Result.objects.create(
            application=application, status=Result.Status.CLASSIFIED, place=1, score="99",
            metrics={}, validated_by=self.federation, updated_by=self.federation,
        )
        from apps.competitions.services import publish_protocol
        publish_protocol(competition, self.federation)
        rating = self.athlete.ratings.get(season=season, discipline=self.discipline)
        self.assertEqual(rating.base_score, Decimal("40.00"))
        self.assertEqual(rating.rating_score, Decimal("40.00"))

    def test_ratings_api_returns_breakdown_and_deterministic_placement(self):
        competition = self.competition("Regional")
        self.publish(competition, [self.row(self.athlete, 1)])
        season = RatingSeason.objects.create(year=2026, name="Сезон 2026")
        calculate_ratings(season=season, discipline=self.discipline, actor=self.federation)
        client = APIClient()
        response = client.get("/api/v1/ratings/?season=2026&discipline=algorithmic&page=1&page_size=10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(response.data["items"][0]["placement"], 1)
        self.assertEqual(response.data["items"][0]["breakdown"][0]["publication_version"], 1)
        self.assertEqual(response.data["items"][0]["breakdown"][0]["awarded_points"], "40.00")

    def test_rule_changes_are_federation_only_and_public_api_hides_restriction_reason(self):
        client = APIClient()
        client.force_login(self.athlete)
        client.post("/api/v1/auth/active-role/", {"role": "athlete"}, format="json")
        season = RatingSeason.objects.create(year=2026, name="Сезон 2026")
        response = client.post("/api/v1/rating-rules/", {"season": season.pk, "discipline": self.discipline.pk, "coefficient_threshold": 2, "stability_coefficient": "1.20", "rounding_places": 2, "rounding_mode": "ROUND_HALF_UP", "point_rules": []}, format="json")
        self.assertEqual(response.status_code, 403)
        AthleteRestriction.objects.create(athlete=self.athlete, kind="suspension", starts_at=timezone.localdate(), ends_at=timezone.localdate(), reason_private="private", created_by=self.federation)
        client.force_login(self.federation)
        client.post("/api/v1/auth/active-role/", {"role": "federation"}, format="json")
        public = client.get("/api/v1/rating-restrictions/")
        self.assertEqual(public.status_code, 200)
        self.assertNotIn("reason_private", public.data[0])
        self.assertIn(APIClient().get("/api/v1/rating-restrictions/").status_code, (401, 403))

    def test_rule_version_change_preserves_historical_contribution_provenance(self):
        season = RatingSeason.objects.create(year=2026, name="РЎРµР·РѕРЅ 2026")
        competition = self.competition("Regional")
        self.publish(competition, [self.row(self.athlete, 1)])

        first = ensure_default_rule(season, self.discipline, self.federation)
        calculate_ratings(season=season, discipline=self.discipline, actor=self.federation)
        original = RatingContribution.objects.get(athlete=self.athlete, is_current=True)
        self.assertEqual(original.rule_version_id, first.id)

        second = create_rule_version(
            actor=self.federation,
            season=season,
            discipline=self.discipline,
            validated_data={
                "coefficient_threshold": 2,
                "stability_coefficient": Decimal("1.20"),
                "rounding_places": 2,
                "rounding_mode": "ROUND_HALF_UP",
                "is_active": True,
                "point_rules": [{"competition_level": "Regional", "place": 1, "points": Decimal("25.00")}],
            },
        )
        calculate_ratings(season=season, discipline=self.discipline, actor=self.federation)

        current = RatingContribution.objects.get(athlete=self.athlete, is_current=True)
        self.assertEqual(current.rule_version_id, second.id)
        self.assertFalse(RatingContribution.objects.get(pk=original.pk).is_current)
        self.assertEqual(RatingContribution.objects.get(pk=original.pk).rule_version_id, first.id)

    def test_configured_rounding_mode_is_deterministic(self):
        season = RatingSeason.objects.create(year=2026, name="РЎРµР·РѕРЅ 2026")
        competition = self.competition("Regional")
        self.publish(competition, [self.row(self.athlete, 1)])
        rule = RatingRuleVersion.objects.create(
            season=season,
            discipline=self.discipline,
            version=1,
            coefficient_threshold=1,
            stability_coefficient=Decimal("1.20"),
            rounding_places=2,
            rounding_mode="ROUND_DOWN",
            is_active=True,
            created_by=self.federation,
        )
        RatingPointRule.objects.create(rule_version=rule, competition_level="Regional", place=1, points=Decimal("33.33"))

        calculate_ratings(season=season, discipline=self.discipline, actor=self.federation)
        rating = self.athlete.ratings.get(season=season, discipline=self.discipline)
        self.assertEqual(rating.rating_score, Decimal("39.99"))

    def test_rating_filters_are_scoped_to_the_selected_discipline_and_empty_sets_are_stable(self):
        season = RatingSeason.objects.create(year=2026, name="РЎРµР·РѕРЅ 2026")
        other_age_group = AgeGroup.objects.exclude(pk=self.age_group.pk).first()
        self.assertIsNotNone(other_age_group)

        algorithmic = self.competition("Regional", discipline=self.discipline, days=1)
        product = self.competition("Regional", discipline=self.other_discipline, days=2)
        self.publish(algorithmic, [self.row(self.athlete, 1, self.age_group.name)])
        self.publish(product, [self.row(self.athlete, 1, other_age_group.name)])
        calculate_ratings(season=season, discipline=self.discipline, actor=self.federation)
        calculate_ratings(season=season, discipline=self.other_discipline, actor=self.federation)

        client = APIClient()
        response = client.get(f"/api/v1/ratings/?season=2026&discipline=algorithmic&age_group={other_age_group.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total"], 0)
        empty = client.get("/api/v1/ratings/?season=2099&discipline=algorithmic")
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.data["items"], [])
        self.assertEqual(empty.data["total"], 0)
        self.assertEqual(empty.data["pages"], 0)
