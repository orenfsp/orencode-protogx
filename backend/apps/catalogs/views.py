from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from .models import Discipline
from .serializers import DisciplineSerializer


class DisciplineListView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = DisciplineSerializer
    queryset = Discipline.objects.filter(is_active=True)
