from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from . import services
from .serializers import (
    MeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PhoneTokenObtainPairSerializer,
    RegisterDriverSerializer,
    RegisterPassengerSerializer,
    UserSerializer,
)
from .services import PasswordResetError


class BaseRegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class RegisterPassengerView(BaseRegisterView):
    serializer_class = RegisterPassengerSerializer


class RegisterDriverView(BaseRegisterView):
    serializer_class = RegisterDriverSerializer


class PhoneTokenObtainPairView(TokenObtainPairView):
    serializer_class = PhoneTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH the authenticated user's own account (role-aware profile)."""

    serializer_class = MeSerializer
    http_method_names = ["get", "patch", "options", "head"]

    def get_object(self):
        return self.request.user


# Generic message — identical whether or not the phone has an account, so the
# endpoint can't be used to discover which phone numbers are registered.
_RESET_SENT_MESSAGE = (
    "If an account exists for that phone number, a reset code has been sent."
)


class PasswordResetRequestView(generics.GenericAPIView):
    """POST {phone} -> sends a one-time reset code by SMS (or the server log
    in console mode). Always 200 with a generic message."""

    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(phone=serializer.validated_data["phone"])
        return Response({"detail": _RESET_SENT_MESSAGE})


class PasswordResetConfirmView(generics.GenericAPIView):
    """POST {phone, code, new_password} -> sets the new password."""

    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.confirm_password_reset(**serializer.validated_data)
        except PasswordResetError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Your password has been reset. You can now log in."})
