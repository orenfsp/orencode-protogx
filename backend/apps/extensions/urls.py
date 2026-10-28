from django.urls import path

from .notifications import NotificationsView

urlpatterns = [path("notifications/", NotificationsView.as_view())]
