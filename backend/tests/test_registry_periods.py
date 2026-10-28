from datetime import date
from threading import Barrier, Thread
from unittest import skipUnless

from django.db import (
    IntegrityError,
    OperationalError,
    close_old_connections,
    connection,
    transaction,
)
from django.test import TestCase, TransactionTestCase
from rest_framework.exceptions import ValidationError

from apps.accounts.models import AthleteProfile, User, UserRole
from apps.catalogs.models import Discipline, Organization
from apps.competitions.models import AuditEvent
from apps.registry.models import (
    DisciplinePeriod,
    OrganizationPeriod,
    ParticipationPeriod,
)
from apps.registry.services import add_period, transfer_organization


class RegistryPeriodTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user(email="federation@example.test", full_name="Fictional federation")
        self.athlete = User.objects.create_user(email="athlete@example.test", full_name="Fictional athlete")
        UserRole.objects.create(user=self.athlete, role=UserRole.Role.ATHLETE)
        self.first = Organization.objects.create(code="first", name="First")
        self.second = Organization.objects.create(code="second", name="Second")

    def test_inclusive_overlap_and_date_validation(self):
        add_period(actor=self.actor, model=ParticipationPeriod, athlete=self.athlete, starts_on=date(2024, 1, 1), ends_on=date(2024, 12, 31))
        with self.assertRaises(ValidationError):
            add_period(actor=self.actor, model=ParticipationPeriod, athlete=self.athlete, starts_on=date(2024, 12, 31))
        add_period(actor=self.actor, model=ParticipationPeriod, athlete=self.athlete, starts_on=date(2025, 1, 1))
        with self.assertRaises(ValidationError):
            add_period(actor=self.actor, model=ParticipationPeriod, athlete=self.athlete, starts_on=date(2027, 1, 1))
        with self.assertRaises(IntegrityError), transaction.atomic():
            ParticipationPeriod.objects.create(athlete=self.athlete, starts_on=date(2025, 2, 1), ends_on=date(2025, 1, 1))

    def test_different_disciplines_can_overlap_but_same_discipline_cannot(self):
        first = Discipline.objects.create(code="direct-a", name="Direct A")
        second = Discipline.objects.create(code="direct-b", name="Direct B")
        for discipline in (first, second):
            add_period(actor=self.actor, model=DisciplinePeriod, athlete=self.athlete, discipline=discipline, starts_on=date(2024, 1, 1))
        with self.assertRaises(ValidationError):
            add_period(actor=self.actor, model=DisciplinePeriod, athlete=self.athlete, discipline=first, starts_on=date(2025, 1, 1))
        self.assertEqual(DisciplinePeriod.objects.count(), 2)

    def test_transfer_preserves_history_current_profile_and_audit(self):
        AthleteProfile.objects.create(user=self.athlete, organization=self.first)
        old = add_period(actor=self.actor, model=OrganizationPeriod, athlete=self.athlete, organization=self.first, starts_on=date(2024, 1, 1))
        new = transfer_organization(actor=self.actor, athlete=self.athlete, organization=self.second, effective_on=date(2025, 1, 1))
        old.refresh_from_db()
        self.assertEqual(old.ends_on, date(2024, 12, 31))
        self.assertEqual(new.starts_on, date(2025, 1, 1))
        self.athlete.athlete_profile.refresh_from_db()
        self.assertEqual(self.athlete.athlete_profile.organization, self.second)
        self.assertEqual(AuditEvent.objects.filter(action__startswith="registry.").count(), 4)

    def test_transfer_refuses_to_invent_unknown_history(self):
        AthleteProfile.objects.create(user=self.athlete, organization=self.first)
        with self.assertRaises(ValidationError):
            transfer_organization(actor=self.actor, athlete=self.athlete, organization=self.second, effective_on=date(2025, 1, 1))
        self.assertFalse(OrganizationPeriod.objects.exists())
        self.athlete.athlete_profile.refresh_from_db()
        self.assertEqual(self.athlete.athlete_profile.organization, self.first)


@skipUnless(connection.vendor == "postgresql", "Row-lock concurrency requires PostgreSQL")
class RegistryConcurrencyTests(TransactionTestCase):
    def test_database_rejects_direct_overlap_and_allows_adjacent_and_other_discipline(self):
        athlete = User.objects.create_user(email="direct@example.test", full_name="Athlete")
        first = Discipline.objects.create(code="direct-a", name="Direct A")
        second = Discipline.objects.create(code="direct-b", name="Direct B")
        ParticipationPeriod.objects.create(athlete=athlete, starts_on=date(2024, 1, 1), ends_on=date(2024, 12, 31))
        ParticipationPeriod.objects.create(athlete=athlete, starts_on=date(2025, 1, 1))
        with self.assertRaises(IntegrityError), transaction.atomic():
            ParticipationPeriod.objects.create(athlete=athlete, starts_on=date(2024, 12, 31))
        DisciplinePeriod.objects.create(athlete=athlete, discipline=first, starts_on=date(2024, 1, 1))
        DisciplinePeriod.objects.create(athlete=athlete, discipline=second, starts_on=date(2024, 1, 1))
        with self.assertRaises(IntegrityError), transaction.atomic():
            DisciplinePeriod.objects.create(athlete=athlete, discipline=first, starts_on=date(2025, 1, 1))

    def test_concurrent_overlapping_periods_only_one_succeeds(self):
        actor = User.objects.create_user(email="actor@example.test", full_name="Actor")
        athlete = User.objects.create_user(email="person@example.test", full_name="Athlete")
        UserRole.objects.create(user=athlete, role=UserRole.Role.ATHLETE)
        barrier = Barrier(2)
        results = []

        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                add_period(actor=actor, model=ParticipationPeriod, athlete=athlete, starts_on=date(2025, 1, 1))
                results.append("created")
            except ValidationError:
                results.append("overlap")
            finally:
                close_old_connections()

        threads = [Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertCountEqual(results, ["created", "overlap"])
        self.assertEqual(ParticipationPeriod.objects.count(), 1)

    def test_direct_concurrent_overlaps_are_rejected_by_database(self):
        athlete = User.objects.create_user(email="direct-race@example.test", full_name="Athlete")
        barrier = Barrier(2)
        outcomes = []

        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                ParticipationPeriod.objects.create(athlete=athlete, starts_on=date(2025, 1, 1))
                outcomes.append("created")
            except IntegrityError:
                outcomes.append("overlap")
            except OperationalError as error:
                # Concurrent GiST exclusion inserts may deadlock; PostgreSQL
                # aborts one writer rather than allowing overlapping rows.
                if getattr(error.__cause__, "sqlstate", None) != "40P01":
                    raise
                outcomes.append("overlap")
            finally:
                close_old_connections()

        threads = [Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertCountEqual(outcomes, ["created", "overlap"])
