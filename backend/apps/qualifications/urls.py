from django.urls import path

from . import views
from .corrections import QualificationCorrectionsView

urlpatterns = [
    path("qualification-history/<str:kind>/<int:pk>/corrections/", QualificationCorrectionsView.as_view()),
    path("qualification-options/", views.OptionsView.as_view()),
    path("qualification-rules/", views.QualificationRulesView.as_view()),
    path("qualification-deadlines/", views.DeadlinesView.as_view()),
    path("rank-results/", views.RankResultsView.as_view()),
    path("rank-applications/", views.RankApplicationsView.as_view()),
    path("rank-applications/<int:pk>/decision/", views.RankApplicationDecisionView.as_view()),
    path("rank-history/", views.RankHistoryView.as_view()),
    path("judge-category-applications/", views.CategoryApplicationsView.as_view()),
    path("judge-category-applications/<int:pk>/decision/", views.CategoryApplicationDecisionView.as_view()),
    path("judge-category-history/", views.CategoryHistoryView.as_view()),
]
