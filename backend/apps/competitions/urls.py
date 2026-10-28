from django.urls import path

from . import views
from .link_lifecycle import LinkLifecycleView
from .registration import RegistrationView, RegulationsDownloadView
from .reports import AthleteReportView, PersonalProtocolView
from .types import CompetitionTypeDetailView, CompetitionTypesView

urlpatterns = [
    path("age-groups/", views.AgeGroupsView.as_view()),
    path("calendar-entries/", views.CalendarEntriesView.as_view()),
    path("templates/", views.TemplatesView.as_view()),
    path("competition-types/", CompetitionTypesView.as_view()),
    path("competition-types/<int:pk>/", CompetitionTypeDetailView.as_view()),
    path("competitions/", views.CompetitionsView.as_view()),
    path("competitions/<int:pk>/", views.CompetitionDetailView.as_view()),
    path("competitions/<int:pk>/publish/", views.CompetitionPublishView.as_view()),
    path("competitions/<int:pk>/registration/", RegistrationView.as_view()),
    path("competitions/<int:pk>/regulations/", RegulationsDownloadView.as_view()),
    path("competitions/<int:pk>/protocol-preview/", views.ProtocolPreviewView.as_view()),
    path("competitions/<int:pk>/protocol-publish/", views.ProtocolPublishView.as_view()),
    path("competitions/<int:pk>/protocols/", views.ProtocolsView.as_view()),
    path("competitions/<int:pk>/protocols/<int:version>/download/", views.ProtocolDownloadView.as_view()),
    path("applications/", views.ApplicationsView.as_view()),
    path("applications/<int:pk>/decision/", views.ApplicationDecisionView.as_view()),
    path("judge-assignments/", views.JudgeAssignmentsView.as_view()),
    path("results/", views.ResultsView.as_view()),
    path("results/<int:pk>/validate/", views.ResultValidateView.as_view()),
    path("history/", views.AthleteHistoryView.as_view()),
    path("history/<int:pk>/protocols/<int:version>/", PersonalProtocolView.as_view()),
    path("reports/athlete-participation/", AthleteReportView.as_view()),
    path("coach-links/", views.CoachLinksView.as_view()),
    path("coach-links/<int:pk>/decision/", views.CoachLinkDecisionView.as_view()),
    path("coach-links/<int:pk>/status/", LinkLifecycleView.as_view()),
    path("judge-choices/", views.JudgeChoicesView.as_view()),
]
