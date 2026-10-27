from django.urls import path

from . import views

urlpatterns = [
    path("teams/options/", views.TeamOptionsView.as_view()),
    path("teams/", views.TeamsView.as_view()),
    path("teams/<int:pk>/", views.TeamDetailView.as_view()),
    path("teams/<int:pk>/candidates/", views.TeamCandidatesView.as_view()),
    path("teams/<int:pk>/members/", views.TeamMembersView.as_view()),
    path("teams/<int:pk>/members/<int:membership_id>/remove/", views.TeamMemberRemoveView.as_view()),
    path("teams/<int:pk>/reorder/", views.TeamReorderView.as_view()),
    path("teams/<int:pk>/history/", views.TeamHistoryView.as_view()),
    path("teams/<int:pk>/publish/", views.TeamPublishView.as_view()),
    path("teams/<int:pk>/documents/", views.TeamDocumentsView.as_view()),
]
