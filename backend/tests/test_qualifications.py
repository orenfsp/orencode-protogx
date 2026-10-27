from datetime import date, timedelta
from decimal import Decimal

from django.contrib import admin
from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Guardian, PersonalDataConsent, User, UserRole
from apps.catalogs.models import Discipline
from apps.competitions.models import (
    AgeGroup,
    Application,
    AuditEvent,
    CoachAthleteLink,
    Competition,
    ProtocolPublication,
    ProtocolTemplate,
    Result,
)
from apps.qualifications.models import (
    JudgeCategoryApplication,
    JudgeCategoryHistory,
    QualificationRule,
    RankApplication,
    SportRankHistory,
)


class QualificationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.today = timezone.localdate()
        self.federation = self.user("federation", "federation")
        self.athlete = self.user("athlete", "athlete")
        self.other = self.user("other", "athlete")
        self.coach = self.user("coach", "coach")
        self.outsider = self.user("outsider", "coach")
        self.judge = self.user("judge", "judge")
        self.other_judge = self.user("otherjudge", "judge")
        self.algorithmic = Discipline.objects.get(code="algorithmic")
        self.robotics = Discipline.objects.get(code="robotics")
        self.group = AgeGroup.objects.get(name="Демо: 18+")

    # --- helpers ---
    def user(self, slug, role):
        user = User.objects.create_user(email=f"{slug}@example.test", password="SafePassphrase2048!", full_name=f"Тест {slug}", date_of_birth=date(1995, 1, 1))
        UserRole.objects.create(user=user, role=role)
        PersonalDataConsent.objects.create(user=user, text_version="test")
        return user

    def as_role(self, user, role):
        self.client.force_login(user)
        response = self.client.post("/api/v1/auth/active-role/", {"role": role}, format="json")
        self.assertEqual(response.status_code, 200, response.data)

    def competition(self, level="Региональное", discipline=None):
        discipline = discipline or self.algorithmic
        now = timezone.now()
        return Competition.objects.create(
            title=f"Тест {level}", discipline=discipline, level=level, competition_type="турнир", format="online",
            starts_at=now - timedelta(days=3), ends_at=now - timedelta(days=2), registration_deadline=now - timedelta(days=10),
            age_reference_date=self.today, location="Площадка", regulations="Регламент",
            template=ProtocolTemplate.objects.get(discipline=discipline, version=1), state="published", created_by=self.federation,
        )

    def result(self, athlete, competition=None, place=1, status="classified", validated=True, published=True):
        competition = competition or self.competition()
        application = Application.objects.create(competition=competition, athlete=athlete, age_group=self.group, submitted_by=athlete, status="approved")
        result = Result.objects.create(
            application=application, status=status, place=place if status == "classified" else None,
            score=Decimal("10.000") if status == "classified" else None, updated_by=self.federation,
            validated_by=self.federation if validated else None,
        )
        if published:
            publication, _ = ProtocolPublication.objects.get_or_create(competition=competition, version=1, defaults={"template": competition.template, "snapshot": {"rows": []}, "published_by": self.federation})
            publication.snapshot["rows"].append({"application_id": application.pk, "athlete_id": athlete.pk, "status": status, "place": place if validated and status == "classified" else None, "score": "10.000" if validated and status == "classified" else None})
            publication.save(update_fields=["snapshot"])
        return result

    def link(self, coach, athlete, discipline=None, status="confirmed"):
        return CoachAthleteLink.objects.create(coach=coach, athlete=athlete, discipline=discipline or self.algorithmic, status=status)

    def submit_rank(self, result, rank="adult_3", request_type="assign", comment=""):
        return self.client.post("/api/v1/rank-applications/", {"result": result.pk, "requested_rank": rank, "request_type": request_type, "comment": comment}, format="json")

    def decide(self, path, application_id, **body):
        body.setdefault("status", "approved")
        if body["status"] == "approved":
            body.setdefault("order_number", "Приказ №1")
            body.setdefault("assigned_on", self.today.isoformat())
            body.setdefault("valid_until", (self.today + timedelta(days=730)).isoformat())
        return self.client.post(f"/api/v1/{path}/{application_id}/decision/", body, format="json")

    def grant_rank(self, athlete, rank="adult_3", valid_days=730, assigned_days_ago=1):
        """Присвоенный разряд через настоящий workflow-объект (заявка + запись истории)."""
        result = self.result(athlete)
        application = RankApplication.objects.create(
            athlete=athlete, submitted_by=athlete, request_type="assign", requested_rank=rank, discipline=self.algorithmic,
            competition=result.application.competition, result=result, status="approved", decided_by=self.federation, decided_at=timezone.now(),
        )
        assigned = self.today - timedelta(days=assigned_days_ago)
        return SportRankHistory.objects.create(
            athlete=athlete, discipline=self.algorithmic, rank=rank, application=application, order_number="Приказ-демо",
            assigned_on=assigned, valid_until=self.today + timedelta(days=valid_days), recorded_by=self.federation,
        )

    def grant_category(self, judge, category="third", valid_days=730, assigned_days_ago=1):
        application = JudgeCategoryApplication.objects.create(
            judge=judge, request_type="assign", requested_category=category, status="approved", decided_by=self.federation, decided_at=timezone.now(),
        )
        return JudgeCategoryHistory.objects.create(
            judge=judge, category=category, application=application, order_number="Приказ-демо",
            assigned_on=self.today - timedelta(days=assigned_days_ago), valid_until=self.today + timedelta(days=valid_days), recorded_by=self.federation,
        )


class RankWorkflowTests(QualificationTestCase):
    def test_admin_records_are_read_only(self):
        request = RequestFactory().get("/admin/")
        request.user = self.federation
        for model in (RankApplication, SportRankHistory, JudgeCategoryApplication, JudgeCategoryHistory):
            model_admin = admin.site._registry[model]
            self.assertFalse(model_admin.has_add_permission(request))
            self.assertFalse(model_admin.has_change_permission(request))
            self.assertFalse(model_admin.has_delete_permission(request))

    def test_more_than_300_results_are_discoverable(self):
        competition = self.competition()
        users = User.objects.bulk_create([User(email=f"page-{i}@example.test", full_name=f"Fictional {i}", date_of_birth=date(1995, 1, 1)) for i in range(301)])
        applications = Application.objects.bulk_create([Application(competition=competition, athlete=user, age_group=self.group, submitted_by=user, status="approved") for user in users])
        Result.objects.bulk_create([Result(application=app, status="classified", place=1, score=10, validated_by=self.federation, updated_by=self.federation) for app in applications])
        ProtocolPublication.objects.create(competition=competition, version=1, template=competition.template, snapshot={"rows": [{"application_id": app.pk, "athlete_id": app.athlete_id, "status": "classified", "place": 1, "score": "10.000"} for app in applications]}, published_by=self.federation)
        self.as_role(self.federation, "federation")
        first = self.client.get("/api/v1/rank-results/?page=1").data
        last = self.client.get(f"/api/v1/rank-results/?page={first['pages']}").data
        self.assertEqual(first["count"], 301)
        self.assertEqual(len(last["items"]), 1)

    def test_published_snapshot_is_preserved_after_correction(self):
        result = self.result(self.athlete, place=1)
        result.place = 3
        result.save(update_fields=["place"])
        self.as_role(self.athlete, "athlete")
        created = self.submit_rank(result)
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["place"], 1)
        publication = result.application.competition.protocols.first()
        ProtocolPublication.objects.create(competition=publication.competition, version=2, template=publication.template, snapshot={"rows": [{"application_id": result.application_id, "athlete_id": self.athlete.pk, "status": "classified", "place": 3, "score": "10.000"}]}, published_by=self.federation)
        self.assertEqual(self.client.get("/api/v1/rank-applications/").data[0]["place"], 1)
        self.assertEqual(RankApplication.objects.get(pk=created.data["id"]).publication_id, publication.pk)
        later = self.submit_rank(result, rank="adult_2")
        self.assertEqual(later.status_code, 201, later.data)
        self.assertEqual(later.data["place"], 3)
        self.assertNotEqual(later.data["publication"], created.data["publication"])

    def test_unrelated_or_missing_snapshot_row_is_rejected(self):
        result = self.result(self.athlete)
        publication = result.application.competition.protocols.first()
        publication.snapshot = {"rows": [{"application_id": result.application_id, "athlete_id": self.other.pk, "status": "classified", "place": 1}]}
        publication.save(update_fields=["snapshot"])
        self.as_role(self.athlete, "athlete")
        self.assertEqual(self.submit_rank(result).status_code, 400)

    def test_coach_loses_application_access_after_link_revocation(self):
        result = self.result(self.athlete)
        link = self.link(self.coach, self.athlete)
        self.as_role(self.coach, "coach")
        self.assertEqual(self.submit_rank(result).status_code, 201)
        link.status = "rejected"
        link.save(update_fields=["status"])
        self.assertEqual(self.client.get("/api/v1/rank-applications/").data, [])
        self.assertEqual(self.submit_rank(result, rank="adult_2").status_code, 403)

    def test_current_consent_and_guardian_required(self):
        result = self.result(self.athlete)
        self.as_role(self.athlete, "athlete")
        PersonalDataConsent.objects.filter(user=self.athlete).delete()
        self.assertEqual(self.submit_rank(result).status_code, 400)
        PersonalDataConsent.objects.create(user=self.athlete, text_version="test")
        latest = PersonalDataConsent.objects.create(user=self.athlete, text_version="test-new")
        latest.revoked_at = timezone.now()
        latest.save(update_fields=["revoked_at"])
        self.assertEqual(self.submit_rank(result).status_code, 400)
        PersonalDataConsent.objects.create(user=self.athlete, text_version="test-renewed")
        self.athlete.date_of_birth = self.today - timedelta(days=365 * 10)
        self.athlete.save(update_fields=["date_of_birth"])
        guardian = Guardian.objects.create(minor=self.athlete, full_name="Тест", relationship="parent")
        self.assertEqual(self.submit_rank(result).status_code, 400)
        guardian.confirmation_status = "verified"
        guardian.save(update_fields=["confirmation_status"])
        self.assertEqual(self.submit_rank(result).status_code, 201)

    def test_athlete_application_review_and_validity_period(self):
        result = self.result(self.athlete)
        self.as_role(self.athlete, "athlete")
        created = self.submit_rank(result, comment="Прошу присвоить")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["status"], "pending")
        self.assertEqual(created.data["result"], result.pk)
        self.assertEqual(created.data["competition"], result.application.competition_id)
        self.assertEqual(created.data["place"], 1)
        self.assertEqual(self.client.get("/api/v1/rank-history/").data, [])

        self.as_role(self.federation, "federation")
        decided = self.decide("rank-applications", created.data["id"])
        self.assertEqual(decided.status_code, 200, decided.data)
        self.assertEqual(decided.data["status"], "approved")
        self.assertEqual(decided.data["record"]["order_number"], "Приказ №1")

        self.as_role(self.athlete, "athlete")
        history = self.client.get("/api/v1/rank-history/")
        self.assertEqual(len(history.data), 1)
        row = history.data[0]
        self.assertEqual((row["rank"], row["validity"], row["competition_id"], row["result_id"]), ("adult_3", "active", result.application.competition_id, result.pk))
        self.assertEqual(row["valid_until"], (self.today + timedelta(days=730)).isoformat())
        actions = set(AuditEvent.objects.filter(target_type="rankapplication").values_list("action", flat=True))
        self.assertEqual(actions, {"rank_application.submitted", "rank_application.approved"})

    def test_rejection_requires_reason_and_creates_no_history(self):
        result = self.result(self.athlete)
        self.as_role(self.athlete, "athlete")
        application = self.submit_rank(result).data["id"]
        self.as_role(self.federation, "federation")
        self.assertEqual(self.decide("rank-applications", application, status="rejected").status_code, 400)
        rejected = self.decide("rank-applications", application, status="rejected", reason="Недостаточно оснований")
        self.assertEqual(rejected.status_code, 200, rejected.data)
        self.assertEqual(rejected.data["decision_reason"], "Недостаточно оснований")
        self.assertFalse(SportRankHistory.objects.exists())
        self.assertEqual(self.decide("rank-applications", application).status_code, 400, "повторное решение запрещено")

    def test_approval_validates_dates_and_order(self):
        result = self.result(self.athlete)
        self.as_role(self.athlete, "athlete")
        application = self.submit_rank(result).data["id"]
        self.as_role(self.federation, "federation")
        future = (self.today + timedelta(days=1)).isoformat()
        for bad in (
            {"order_number": ""},
            {"valid_until": self.today.isoformat()},
            {"assigned_on": future, "valid_until": (self.today + timedelta(days=400)).isoformat()},
        ):
            self.assertEqual(self.decide("rank-applications", application, **bad).status_code, 400, bad)
        missing = self.client.post(f"/api/v1/rank-applications/{application}/decision/", {"status": "approved"}, format="json")
        self.assertEqual(missing.status_code, 400)
        self.assertFalse(SportRankHistory.objects.exists())
        self.assertEqual(RankApplication.objects.get(pk=application).status, "pending")
        self.assertEqual(self.decide("rank-applications", 999999).status_code, 404)

    def test_only_active_federation_decides(self):
        result = self.result(self.athlete)
        self.as_role(self.athlete, "athlete")
        application = self.submit_rank(result).data["id"]
        self.assertEqual(self.decide("rank-applications", application).status_code, 403)
        self.as_role(self.coach, "coach")
        self.assertEqual(self.decide("rank-applications", application).status_code, 403)
        self.assertEqual(APIClient().post(f"/api/v1/rank-applications/{application}/decision/", {"status": "approved"}, format="json").status_code, 403)
        self.assertEqual(RankApplication.objects.get(pk=application).status, "pending")

    def test_result_must_be_validated_classified_published_and_own(self):
        self.as_role(self.athlete, "athlete")
        cases = {
            "unvalidated": self.result(self.athlete, validated=False),
            "no_show": self.result(self.athlete, status="no_show"),
            "unpublished": self.result(self.athlete, published=False),
        }
        for name, result in cases.items():
            self.assertEqual(self.submit_rank(result).status_code, 400, name)
        foreign = self.result(self.other)
        self.assertEqual(self.submit_rank(foreign).status_code, 403)
        self.assertEqual(self.client.post("/api/v1/rank-applications/", {"result": 999999, "requested_rank": "adult_3", "request_type": "assign"}, format="json").status_code, 400)
        self.assertFalse(RankApplication.objects.exists())

    def test_duplicate_pending_is_rejected_but_new_after_decision_allowed(self):
        result = self.result(self.athlete)
        self.as_role(self.athlete, "athlete")
        first = self.submit_rank(result)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(self.submit_rank(result).status_code, 400)
        self.as_role(self.federation, "federation")
        self.decide("rank-applications", first.data["id"], status="rejected", reason="Нет")
        self.as_role(self.athlete, "athlete")
        self.assertEqual(self.submit_rank(result).status_code, 201)

    def test_athlete_with_confirmed_coach_cannot_apply_but_coach_can(self):
        result = self.result(self.athlete)
        self.link(self.coach, self.athlete)
        self.as_role(self.athlete, "athlete")
        self.assertEqual(self.submit_rank(result).status_code, 400)
        self.as_role(self.coach, "coach")
        created = self.submit_rank(result)
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual((created.data["athlete"], created.data["submitted_by"]), (self.athlete.pk, self.coach.pk))

    def test_coach_needs_confirmed_link_in_the_same_discipline(self):
        result = self.result(self.athlete)
        self.as_role(self.outsider, "coach")
        self.assertEqual(self.submit_rank(result).status_code, 403)
        self.link(self.outsider, self.athlete, status="pending")
        self.assertEqual(self.submit_rank(result).status_code, 403)
        CoachAthleteLink.objects.all().delete()
        self.link(self.outsider, self.athlete, discipline=self.robotics)
        self.assertEqual(self.submit_rank(result).status_code, 403)
        self.assertFalse(RankApplication.objects.exists())

    def test_assign_must_exceed_current_and_confirm_needs_existing_rank(self):
        self.grant_rank(self.athlete, "adult_2")
        result = self.result(self.athlete)
        self.as_role(self.athlete, "athlete")
        self.assertEqual(self.submit_rank(result, rank="adult_3").status_code, 400)
        self.assertEqual(self.submit_rank(result, rank="adult_2").status_code, 400)
        self.assertEqual(self.submit_rank(result, rank="adult_1").status_code, 201)
        self.assertEqual(self.submit_rank(result, rank="adult_3", request_type="confirm").status_code, 400)
        self.assertEqual(self.submit_rank(result, rank="adult_2", request_type="confirm").status_code, 201)

    def test_confirmation_adds_new_record_and_keeps_history(self):
        first = self.grant_rank(self.athlete, "adult_3", valid_days=10, assigned_days_ago=700)
        result = self.result(self.athlete)
        self.as_role(self.athlete, "athlete")
        application = self.submit_rank(result, rank="adult_3", request_type="confirm").data["id"]
        self.as_role(self.federation, "federation")
        self.assertEqual(self.decide("rank-applications", application).status_code, 200)
        self.assertEqual(SportRankHistory.objects.filter(athlete=self.athlete).count(), 2)
        self.assertTrue(SportRankHistory.objects.filter(pk=first.pk, valid_until=first.valid_until).exists())

    def test_visibility_of_applications_and_history(self):
        own, foreign = self.result(self.athlete), self.result(self.other)
        self.link(self.coach, self.athlete)
        granted = self.grant_rank(self.other, "adult_3")
        self.as_role(self.coach, "coach")
        mine = self.submit_rank(own).data["id"]
        self.as_role(self.other, "athlete")
        created = self.submit_rank(foreign, rank="adult_2")
        self.assertEqual(created.status_code, 201, created.data)
        theirs = {created.data["id"], granted.application_id}
        self.assertEqual({row["id"] for row in self.client.get("/api/v1/rank-applications/").data}, theirs)
        self.assertEqual({row["athlete"] for row in self.client.get("/api/v1/rank-history/").data}, {self.other.pk})
        self.as_role(self.athlete, "athlete")
        self.assertEqual({row["id"] for row in self.client.get("/api/v1/rank-applications/").data}, {mine})
        self.assertEqual(self.client.get("/api/v1/rank-history/").data, [])
        self.as_role(self.coach, "coach")
        self.assertEqual({row["id"] for row in self.client.get("/api/v1/rank-applications/").data}, {mine})
        self.assertEqual(self.client.get("/api/v1/rank-history/").data, [], "чужой спортсмен не раскрывается")
        self.as_role(self.outsider, "coach")
        self.assertEqual(self.client.get("/api/v1/rank-applications/").data, [])
        self.as_role(self.federation, "federation")
        self.assertEqual({row["id"] for row in self.client.get("/api/v1/rank-applications/").data}, theirs | {mine})
        self.assertEqual(len(self.client.get(f"/api/v1/rank-history/?athlete={self.other.pk}").data), 1)
        self.assertEqual(self.client.get("/api/v1/rank-history/?athlete=abc").status_code, 400)
        self.as_role(self.judge, "judge")
        self.assertEqual(self.client.get("/api/v1/rank-applications/").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/rank-history/").status_code, 403)
        self.assertIn(APIClient().get("/api/v1/rank-applications/").status_code, (401, 403))

    def test_database_constraint_blocks_invalid_validity_period(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.grant_rank(self.athlete, valid_days=-5, assigned_days_ago=1)


class RankHintTests(QualificationTestCase):
    def rule(self, level="региональное", place=3, rank="adult_3", verified=False, discipline=None, active=True):
        return QualificationRule.objects.create(
            discipline=discipline or self.algorithmic, rank=rank, competition_level=level, max_place=place,
            source_verified=verified, is_active=active,
        )

    def test_hints_are_preliminary_and_follow_rules(self):
        self.rule()
        match = self.result(self.athlete, place=2)
        miss = self.result(self.other, place=5)
        self.as_role(self.federation, "federation")
        rows = {row["result"]: row for row in self.client.get("/api/v1/rank-results/").data["items"]}
        self.assertEqual(rows[match.pk]["hint"]["rank"], "adult_3")
        self.assertFalse(rows[match.pk]["hint"]["source_verified"])
        self.assertIn("не является присвоением", rows[match.pk]["hint"]["disclaimer"])
        self.assertIsNone(rows[miss.pk]["hint"])
        hinted = self.client.get("/api/v1/rank-results/?hinted=1").data["items"]
        self.assertEqual([row["result"] for row in hinted], [match.pk])
        self.assertEqual(QualificationRule.objects.count(), 1)
        self.assertEqual(RankApplication.objects.count(), 0, "подсказка ничего не присваивает")

    def test_best_matching_rule_wins_and_inactive_or_other_discipline_ignored(self):
        self.rule(rank="adult_3")
        self.rule(rank="adult_2")
        self.rule(rank="cms", active=False)
        self.rule(rank="ms", discipline=self.robotics)
        result = self.result(self.athlete, place=1)
        self.as_role(self.federation, "federation")
        self.assertEqual(self.client.get("/api/v1/rank-results/").data["items"][0]["hint"]["rank"], "adult_2")
        self.assertEqual(len(self.client.get("/api/v1/qualification-rules/").data), 4)
        self.assertEqual(result.pk, self.client.get("/api/v1/rank-results/").data["items"][0]["result"])

    def test_results_list_is_scoped_by_role(self):
        mine, foreign, unvalidated = self.result(self.athlete), self.result(self.other), self.result(self.athlete, validated=False)
        self.link(self.coach, self.athlete)
        self.as_role(self.athlete, "athlete")
        self.assertEqual([row["result"] for row in self.client.get("/api/v1/rank-results/").data["items"]], [mine.pk])
        self.as_role(self.coach, "coach")
        self.assertEqual([row["result"] for row in self.client.get("/api/v1/rank-results/").data["items"]], [mine.pk])
        self.as_role(self.outsider, "coach")
        self.assertEqual(self.client.get("/api/v1/rank-results/").data["items"], [])
        self.as_role(self.judge, "judge")
        self.assertEqual(self.client.get("/api/v1/rank-results/").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/qualification-rules/").status_code, 403)
        self.as_role(self.federation, "federation")
        self.assertEqual({row["result"] for row in self.client.get("/api/v1/rank-results/").data["items"]}, {mine.pk, foreign.pk})
        self.assertNotIn(unvalidated.pk, {row["result"] for row in self.client.get("/api/v1/rank-results/").data["items"]})

    def test_pending_rank_and_current_rank_are_reported(self):
        self.grant_rank(self.athlete, "adult_3")
        result = self.result(self.athlete)
        self.as_role(self.athlete, "athlete")
        self.submit_rank(result, rank="adult_2")
        row = [r for r in self.client.get("/api/v1/rank-results/").data["items"] if r["result"] == result.pk][0]
        self.assertEqual((row["pending_ranks"], row["current_rank"]), (["adult_2"], "adult_3"))


class JudgeCategoryTests(QualificationTestCase):
    def submit(self, category="third", request_type="assign"):
        return self.client.post("/api/v1/judge-category-applications/", {"requested_category": category, "request_type": request_type, "comment": "Основание"}, format="json")

    def test_judge_application_review_and_history(self):
        self.as_role(self.judge, "judge")
        created = self.submit()
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(self.submit("second").status_code, 400, "одна заявка на рассмотрении")
        self.as_role(self.federation, "federation")
        decided = self.decide("judge-category-applications", created.data["id"])
        self.assertEqual(decided.status_code, 200, decided.data)
        self.assertEqual(decided.data["record"]["order_number"], "Приказ №1")
        self.as_role(self.judge, "judge")
        history = self.client.get("/api/v1/judge-category-history/").data
        self.assertEqual([(row["category"], row["validity"]) for row in history], [("third", "active")])
        self.assertEqual(self.client.get("/api/v1/judge-category-applications/").data[0]["status"], "approved")
        actions = set(AuditEvent.objects.filter(target_type="judgecategoryapplication").values_list("action", flat=True))
        self.assertEqual(actions, {"judge_category_application.submitted", "judge_category_application.approved"})

    def test_roles_and_visibility(self):
        self.as_role(self.athlete, "athlete")
        self.assertEqual(self.submit().status_code, 403)
        self.assertEqual(self.client.get("/api/v1/judge-category-applications/").status_code, 403)
        self.as_role(self.coach, "coach")
        self.assertEqual(self.client.get("/api/v1/judge-category-history/").status_code, 403)
        self.as_role(self.judge, "judge")
        application = self.submit().data["id"]
        self.assertEqual(self.decide("judge-category-applications", application).status_code, 403)
        self.as_role(self.other_judge, "judge")
        self.assertEqual(self.client.get("/api/v1/judge-category-applications/").data, [])
        self.assertEqual(self.client.get("/api/v1/judge-category-history/").data, [])
        self.as_role(self.federation, "federation")
        self.assertEqual(len(self.client.get("/api/v1/judge-category-applications/").data), 1)
        self.assertEqual(self.submit().status_code, 403, "федерация не подаёт заявки судьи")

    def test_rejection_and_rules(self):
        self.as_role(self.judge, "judge")
        application = self.submit().data["id"]
        self.as_role(self.federation, "federation")
        self.assertEqual(self.decide("judge-category-applications", application, status="rejected").status_code, 400)
        self.assertEqual(self.decide("judge-category-applications", application, status="rejected", reason="Нет стажа").status_code, 200)
        self.assertFalse(JudgeCategoryHistory.objects.exists())
        self.grant_category(self.judge, "second")
        self.as_role(self.judge, "judge")
        self.assertEqual(self.submit("third").status_code, 400)
        self.assertEqual(self.submit("third", "confirm").status_code, 400)
        self.assertEqual(self.submit("first").status_code, 201)

    def test_categories_do_not_affect_sport_ranks(self):
        self.grant_category(self.judge, "first")
        self.assertFalse(SportRankHistory.objects.exists())
        self.as_role(self.judge, "judge")
        self.assertEqual(self.client.get("/api/v1/rank-history/").status_code, 403)


class DeadlineTests(QualificationTestCase):
    def test_expiring_and_expired_are_flagged_per_role(self):
        soon = self.grant_rank(self.athlete, "adult_3", valid_days=20, assigned_days_ago=300)
        self.grant_rank(self.other, "adult_3", valid_days=-3, assigned_days_ago=800)
        far = User.objects.create_user(email="far@example.test", password="SafePassphrase2048!", full_name="Тест far")
        UserRole.objects.create(user=far, role="athlete")
        self.grant_rank(far, "adult_3", valid_days=500)
        self.grant_category(self.judge, "third", valid_days=15)
        self.link(self.coach, self.athlete)

        self.as_role(self.federation, "federation")
        data = self.client.get("/api/v1/qualification-deadlines/").data
        by_person = {(item["kind"], item["person"]): item for item in data["items"]}
        self.assertEqual(set(by_person), {("rank", self.athlete.pk), ("rank", self.other.pk), ("judge_category", self.judge.pk)})
        self.assertEqual(by_person[("rank", self.athlete.pk)]["validity"], "expiring")
        self.assertEqual(by_person[("rank", self.athlete.pk)]["valid_until"], soon.valid_until.isoformat())
        self.assertEqual(by_person[("rank", self.other.pk)]["validity"], "expired")
        self.assertEqual([item["days_left"] for item in data["items"]], sorted(item["days_left"] for item in data["items"]))

        self.as_role(self.athlete, "athlete")
        self.assertEqual([i["person"] for i in self.client.get("/api/v1/qualification-deadlines/").data["items"]], [self.athlete.pk])
        self.as_role(self.coach, "coach")
        self.assertEqual([i["person"] for i in self.client.get("/api/v1/qualification-deadlines/").data["items"]], [self.athlete.pk])
        self.as_role(self.outsider, "coach")
        self.assertEqual(self.client.get("/api/v1/qualification-deadlines/").data["items"], [])
        self.as_role(self.judge, "judge")
        items = self.client.get("/api/v1/qualification-deadlines/").data["items"]
        self.assertEqual([(i["kind"], i["person"]) for i in items], [("judge_category", self.judge.pk)])
        self.as_role(self.other_judge, "judge")
        self.assertEqual(self.client.get("/api/v1/qualification-deadlines/").data["items"], [])

    def test_window_parameter_and_superseded_records(self):
        self.grant_rank(self.athlete, "adult_3", valid_days=-100, assigned_days_ago=900)
        self.grant_rank(self.athlete, "adult_2", valid_days=400)
        self.grant_rank(self.other, "adult_3", valid_days=100)
        self.as_role(self.federation, "federation")
        self.assertEqual(self.client.get("/api/v1/qualification-deadlines/").data["items"], [], "заменённая запись не даёт ложного предупреждения")
        wide = self.client.get("/api/v1/qualification-deadlines/?days=120").data
        self.assertEqual([i["person"] for i in wide["items"]], [self.other.pk])
        for bad in ("-1", "366", "x"):
            self.assertEqual(self.client.get(f"/api/v1/qualification-deadlines/?days={bad}").status_code, 400, bad)
        self.assertIn(APIClient().get("/api/v1/qualification-deadlines/").status_code, (401, 403))

    def test_options_catalog(self):
        self.as_role(self.athlete, "athlete")
        data = self.client.get("/api/v1/qualification-options/").data
        self.assertIn("cms", [item["value"] for item in data["ranks"]])
        self.assertIn("first", [item["value"] for item in data["categories"]])
        self.assertEqual({item["value"] for item in data["request_types"]}, {"assign", "confirm"})
