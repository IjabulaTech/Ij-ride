from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PhoneTokenObtainPairView,
    RegisterDriverView,
    RegisterPassengerView,
)

app_name = "accounts"

urlpatterns = [
    path("register/passenger/", RegisterPassengerView.as_view(), name="register-passenger"),
    path("register/driver/", RegisterDriverView.as_view(), name="register-driver"),
    path("token/", PhoneTokenObtainPairView.as_view(), name="token"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path(
        "password/reset/request/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
]
