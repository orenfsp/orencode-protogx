from django.urls import path

from .views import (
    ActiveRoleView,
    CsrfView,
    DashboardView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
)

urlpatterns = [
    path("csrf/", CsrfView.as_view()),
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("me/", MeView.as_view()),
    path("dashboard/", DashboardView.as_view()),
    path("active-role/", ActiveRoleView.as_view()),
]
