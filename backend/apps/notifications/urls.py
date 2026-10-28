from django.urls import path

from .views import NotificationReadView, NotificationsView, ReportDeadlinesView

urlpatterns = [
    path("notifications/", NotificationsView.as_view()),
    path("notifications/<int:pk>/read/", NotificationReadView.as_view()),
    path("report-deadlines/", ReportDeadlinesView.as_view()),
]
