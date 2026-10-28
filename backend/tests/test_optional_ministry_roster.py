from django.contrib.auth.models import Permission

from apps.ratings.services import season_for_year
from apps.teams.models import RegionalTeam, TeamMembership

from .optional_helpers import OptionalCase


class MinistryRosterTests(OptionalCase):
    def test_published_roster_projection_excludes_email_and_minor_names(self):
        team = RegionalTeam.objects.create(
            name="Вымышленная сборная",
            season=season_for_year(self.competition.starts_at.year),
            discipline=self.discipline,
            age_group=self.age_group,
            created_by=self.federation,
            status="published",
        )
        TeamMembership.objects.create(
            team=team, athlete=self.athlete, selected_by=self.federation, position=1
        )
        self.other.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="extensions", codename="view_ministry_dashboard"
            )
        )
        self.login(self.other, "athlete")
        response = self.client.get("/api/v1/ministry/")
        self.assertIn(self.athlete.full_name, str(response.data))
        self.assertNotIn(self.athlete.email, str(response.data))
        self.athlete.date_of_birth = self.competition.starts_at.date().replace(
            year=self.competition.starts_at.year - 14
        )
        self.athlete.save(update_fields=["date_of_birth"])
        self.assertNotIn(
            self.athlete.full_name, str(self.client.get("/api/v1/ministry/").data)
        )
