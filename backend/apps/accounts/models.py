from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from apps.payments.constants import PaymentMethod

from .managers import UserManager


class UserRole(models.TextChoices):
    PASSENGER = "PASSENGER", "Passenger"
    DRIVER = "DRIVER", "Driver"
    ADMIN = "ADMIN", "Admin"


phone_validator = RegexValidator(
    regex=r"^\+\d{10,15}$",
    message="Phone number must be in international format, e.g. +2348031234567.",
)

nin_validator = RegexValidator(
    regex=r"^\d{11}$",
    message="NIN must be exactly 11 digits.",
)


class User(AbstractUser):
    """Phone number is the primary login identifier; email is optional.

    Password login for V1. The phone-first design leaves room for OTP
    login later without changing the identifier.
    """

    username = None
    phone = models.CharField(
        "phone number", max_length=16, unique=True, validators=[phone_validator]
    )
    email = models.EmailField("email address", blank=True, default="")
    role = models.CharField(
        max_length=16,
        choices=UserRole.choices,
        default=UserRole.PASSENGER,
        db_index=True,
    )
    # National Identification Number (11 digits). Optional; captured on the
    # user's profile. `nin_verified` is set by an admin after review (and, in
    # future, an automated NIMC + face-match check — see nin_verification.py).
    nin = models.CharField(max_length=11, blank=True, default="", validators=[nin_validator])
    nin_verified = models.BooleanField(default=False)
    nin_verified_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        constraints = [
            # email stays optional, but no two users may share one
            models.UniqueConstraint(
                fields=["email"],
                condition=~models.Q(email=""),
                name="accounts_user_unique_email_when_set",
            ),
            # NIN optional, but no two users may share one once provided
            models.UniqueConstraint(
                fields=["nin"],
                condition=~models.Q(nin=""),
                name="accounts_user_unique_nin_when_set",
            ),
        ]

    def __str__(self):
        return f"{self.phone} ({self.get_role_display()})"

    @property
    def is_passenger(self) -> bool:
        return self.role == UserRole.PASSENGER

    @property
    def is_driver(self) -> bool:
        return self.role == UserRole.DRIVER

    @property
    def is_admin_role(self) -> bool:
        return self.role == UserRole.ADMIN


class PassengerProfile(models.Model):
    """Passenger-specific data. Created explicitly at registration (Module 3)."""

    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="passenger_profile"
    )
    default_payment_method = models.CharField(
        max_length=16, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Passenger {self.user.phone}"


class PhoneOTP(models.Model):
    """One-time code for phone-based flows (V1: password reset). The code is
    stored hashed, is single-use, expires, and locks after too many wrong
    guesses. A new request for the same phone/purpose supersedes older ones."""

    class Purpose(models.TextChoices):
        PASSWORD_RESET = "PASSWORD_RESET", "Password reset"

    phone = models.CharField(max_length=16, db_index=True)
    purpose = models.CharField(
        max_length=32, choices=Purpose.choices, default=Purpose.PASSWORD_RESET
    )
    code_hash = models.CharField(max_length=64)  # sha256 hex
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["phone", "purpose", "consumed"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP {self.purpose} for {self.phone} ({'used' if self.consumed else 'active'})"
