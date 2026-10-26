from django.urls import path

from .views import DisciplineListView

urlpatterns = [path("", DisciplineListView.as_view())]
