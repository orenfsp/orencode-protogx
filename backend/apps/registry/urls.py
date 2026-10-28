from django.urls import path

from . import views

urlpatterns = [
    path("athletes/", views.AthletesList.as_view()),
    path("athletes/<int:pk>/", views.AthleteDetail.as_view()),
    path("coaches/", views.CoachesList.as_view()),
    path("coaches/<int:pk>/", views.CoachDetail.as_view()),
    path("judges/", views.JudgesList.as_view()),
    path("judges/<int:pk>/", views.JudgeDetail.as_view()),
    path("organizations/", views.Organizations.as_view()),
    path("organizations/<int:pk>/", views.OrganizationDetail.as_view()),
    path("athletes/<int:pk>/history/<str:kind>/", views.PeriodView.as_view()),
    path("athletes/<int:pk>/history/<str:kind>/<int:period_id>/close/", views.ClosePeriodView.as_view()),
    path("athletes/<int:pk>/transfer/", views.TransferView.as_view()),
    path("analytics/participation/", views.ParticipationReport.as_view()),
    path("analytics/participation/export/", views.ParticipationExport.as_view()),
]
