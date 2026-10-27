from django.urls import path

from . import views

urlpatterns = [
    path("rating-options/", views.RatingOptionsView.as_view()),
    path("ratings/", views.RatingsView.as_view()),
    path("rating-rules/", views.RatingRulesView.as_view()),
    path("ratings/recalculate/", views.RatingRecalculateView.as_view()),
    path("rating-restrictions/", views.RatingRestrictionsView.as_view()),
]
