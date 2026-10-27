from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest import skipUnless

from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from rest_framework.exceptions import ValidationError

from apps.accounts.models import PersonalDataConsent, User, UserRole
from apps.catalogs.models import Discipline
from apps.competitions.models import AgeGroup
from apps.ratings.models import RatingSeason
from apps.teams.models import RegionalTeam, TeamMembership
from apps.teams.services import add_member, publish_team, remove_member, reorder_members


@skipUnless(connection.vendor == "postgresql", "requires PostgreSQL row locks")
class TeamConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.actor = User.objects.create_user(email="fed@concurrency.test", password="pass", full_name="Federation")
        UserRole.objects.create(user=self.actor, role="federation")
        self.athletes = []
        for index in range(3):
            user = User.objects.create_user(email=f"a{index}@concurrency.test", password="pass", full_name=f"Athlete {index}", date_of_birth=date(2000, 1, 1))
            UserRole.objects.create(user=user, role="athlete")
            PersonalDataConsent.objects.create(user=user, text_version="test")
            self.athletes.append(user)
        season = RatingSeason.objects.create(year=2026, name="Season 2026")
        discipline, _ = Discipline.objects.get_or_create(code="algorithmic", defaults={"name": "Algorithmic"})
        self.team = RegionalTeam.objects.create(name="Team", season=season, discipline=discipline, age_group=AgeGroup.objects.create(name="Concurrent adults", min_age=18, max_age=40), created_by=self.actor)

    def race(self, *operations):
        barrier = Barrier(len(operations))
        def run(operation):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    operation()
                    return "ok"
                except ValidationError:
                    return "invalid"
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            return list(pool.map(run, operations))

    def test_simultaneous_additions_and_duplicate_protection(self):
        results = self.race(*[lambda: add_member(actor=self.actor, team=self.team, athlete=self.athletes[0]) for _ in range(2)])
        self.assertCountEqual(results, ["ok", "invalid"])
        self.race(*[lambda athlete=athlete: add_member(actor=self.actor, team=self.team, athlete=athlete) for athlete in self.athletes[1:]])
        self.assertEqual(list(self.team.memberships.filter(removed_at__isnull=True).order_by("position").values_list("position", flat=True)), [1, 2, 3])
        self.assertEqual(self.team.decision_history.filter(action="member_added").count(), 3)

    def test_reorder_remove_and_finalize_races_preserve_integrity(self):
        members = [add_member(actor=self.actor, team=self.team, athlete=athlete) for athlete in self.athletes]
        ids = [member.pk for member in members]
        self.assertEqual(self.race(lambda: reorder_members(actor=self.actor, team=self.team, member_ids=ids[::-1]), lambda: reorder_members(actor=self.actor, team=self.team, member_ids=[ids[1], ids[0], ids[2]])), ["ok", "ok"])
        results = self.race(lambda: remove_member(actor=self.actor, membership=members[0]), lambda: reorder_members(actor=self.actor, team=self.team, member_ids=ids[::-1]))
        self.assertIn("ok", results)
        self.assertEqual(self.team.memberships.filter(removed_at__isnull=True).count(), 2)
        positions = list(self.team.memberships.filter(removed_at__isnull=True).values_list("position", flat=True))
        self.assertEqual(len(positions), len(set(positions)))
        remaining = TeamMembership.objects.filter(team=self.team, removed_at__isnull=True).first()
        self.race(lambda: publish_team(actor=self.actor, team=self.team), lambda: remove_member(actor=self.actor, membership=remaining))
        self.team.refresh_from_db()
        if self.team.status == "published":
            self.assertTrue(self.team.decision_history.filter(action="published").exists())
        self.assertEqual(self.team.decision_history.filter(action="member_removed").count(), 2)
