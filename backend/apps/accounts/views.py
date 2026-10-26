from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import UserRole
from .serializers import (
    ActiveRoleSerializer,
    AuthResponseSerializer,
    CsrfSerializer,
    EmptySerializer,
    LoginSerializer,
    MeSerializer,
    RegisterSerializer,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: CsrfSerializer})
    def get(self, request):
        return Response({"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=RegisterSerializer, responses={201: AuthResponseSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        request.session["active_role"] = UserRole.Role.ATHLETE
        return Response({"user": MeSerializer(user, context={"request": request}).data}, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(request=LoginSerializer, responses={200: AuthResponseSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        request.session["active_role"] = user.role_assignments.values_list("role", flat=True).first()
        return Response({"user": MeSerializer(user, context={"request": request}).data})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: MeSerializer})
    def get(self, request):
        return Response(MeSerializer(request.user, context={"request": request}).data)


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmptySerializer

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_protect, name="dispatch")
class ActiveRoleView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ActiveRoleSerializer, responses={200: MeSerializer})
    def post(self, request):
        serializer = ActiveRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]
        if not request.user.role_assignments.filter(role=role).exists():
            return Response({"detail": "Role is not assigned"}, status=status.HTTP_403_FORBIDDEN)
        request.session["active_role"] = role
        return Response(MeSerializer(request.user, context={"request": request}).data)
