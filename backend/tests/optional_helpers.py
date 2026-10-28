from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import PersonalDataConsent, User, UserRole
from apps.catalogs.models import Discipline
from apps.competitions.models import (
    AgeGroup,
    Application,
    Competition,
    JudgeAssignment,
    ProtocolTemplate,
    Result,
)
from apps.competitions.services import publish_protocol


class OptionalCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        def user(slug, role):
            u = User.objects.create_user(
                email=f"optional-{slug}@example.test",
                password="FictionalTest2048!",
                full_name=f"Вымышленный {slug}",
                date_of_birth=date(2000, 1, 1),
            )
            UserRole.objects.create(user=u, role=role)
            PersonalDataConsent.objects.create(user=u, text_version="fictional-test")
            return u

        cls.federation, cls.athlete, cls.other, cls.coach, cls.judge = [
            user(slug, role)
            for slug, role in [
                ("federation", "federation"),
                ("athlete", "athlete"),
                ("other", "athlete"),
                ("coach", "coach"),
                ("judge", "judge"),
            ]
        ]
        cls.discipline = Discipline.objects.get(code="algorithmic")
        cls.age_group = AgeGroup.objects.get(name="Демо: 18+")
        now = timezone.now()
        cls.competition = Competition.objects.create(
            title="Вымышленный кубок расширений",
            discipline=cls.discipline,
            template=ProtocolTemplate.objects.get(discipline=cls.discipline, version=1),
            level="regional",
            competition_type="cup",
            format="online",
            starts_at=now - timedelta(days=3),
            ends_at=now - timedelta(days=2),
            registration_deadline=now - timedelta(days=5),
            location="Демо",
            regulations="Демонстрация",
            state="published",
            created_by=cls.federation,
        )
        cls.competition.age_groups.add(cls.age_group)
        cls.application = Application.objects.create(
            competition=cls.competition,
            athlete=cls.athlete,
            submitted_by=cls.athlete,
            age_group=cls.age_group,
            status="approved",
        )
        cls.result = Result.objects.create(
            application=cls.application,
            status="classified",
            place=1,
            score=100,
            metrics={"solved_tasks": 3},
            updated_by=cls.federation,
            validated_by=cls.federation,
        )
        cls.assignment = JudgeAssignment.objects.create(
            competition=cls.competition,
            judge=cls.judge,
            role_label="Главный судья",
            assigned_by=cls.federation,
        )
        cls.publication = publish_protocol(cls.competition, cls.federation)

    def setUp(self):
        self.client = APIClient()

    def login(self, user, role):
        self.client.force_login(user)
        session = self.client.session
        session["active_role"] = role
        session.save()

    def post(self, path, data=None):
        return self.client.post(f"/api/v1/{path}", data or {}, format="json")
