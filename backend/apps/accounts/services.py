"""Registration + password-reset services. Profile rows are created here,
explicitly and atomically — views and serializers never create model rows
themselves."""
from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.drivers.models import DriverAvailability, DriverProfile, VehicleCategory

from . import otp as otp_lib
from .models import PassengerProfile, PhoneOTP, User, UserRole


@transaction.atomic
def register_passenger(
    *, phone: str, password: str, first_name: str = "", last_name: str = "", email: str = ""
) -> User:
    user = User.objects.create_user(
        phone,
        password,
        role=UserRole.PASSENGER,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    PassengerProfile.objects.create(user=user)
    return user


@transaction.atomic
def register_driver(
    *,
    phone: str,
    password: str,
    driver_category: str = VehicleCategory.CAR,
    first_name: str = "",
    last_name: str = "",
    email: str = "",
) -> User:
    user = User.objects.create_user(
        phone,
        password,
        role=UserRole.DRIVER,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    profile = DriverProfile.objects.create(
        user=user, driver_category=driver_category
    )  # approval_status defaults to PENDING
    DriverAvailability.objects.create(driver=profile)
    return user


# ---------------------------------------------------------------------------
# Password reset (phone OTP)
# ---------------------------------------------------------------------------


def request_password_reset(*, phone: str) -> None:
    """Issue and deliver a reset code IF an account exists for `phone`.

    Callers must always respond the same way regardless of whether the phone
    exists — this function never signals existence. Silently no-ops for
    unknown phones and for resend attempts inside the cooldown window.
    """
    if not User.objects.filter(phone=phone, is_active=True).exists():
        return

    recent = (
        PhoneOTP.objects.filter(
            phone=phone,
            purpose=PhoneOTP.Purpose.PASSWORD_RESET,
            consumed=False,
            created_at__gt=timezone.now() - timedelta(seconds=otp_lib.RESEND_COOLDOWN_SECONDS),
        )
        .order_by("-created_at")
        .first()
    )
    if recent is not None:
        return  # too soon since the last code; don't spam

    # New code supersedes any older un-consumed ones.
    PhoneOTP.objects.filter(
        phone=phone, purpose=PhoneOTP.Purpose.PASSWORD_RESET, consumed=False
    ).update(consumed=True)

    code = otp_lib.generate_code()
    PhoneOTP.objects.create(
        phone=phone,
        purpose=PhoneOTP.Purpose.PASSWORD_RESET,
        code_hash=otp_lib.hash_code(code),
        expires_at=otp_lib.expiry(),
    )
    otp_lib.send_code(phone, code)


class PasswordResetError(Exception):
    """Reset confirmation failed (bad/expired code). Maps to HTTP 400."""


def confirm_password_reset(*, phone: str, code: str, new_password: str) -> None:
    # NB: failed-attempt bookkeeping uses queryset .update() (autocommit) so
    # it survives the exception we raise — wrapping this in a transaction that
    # rolls back on raise would silently lose the attempt counter.
    otp = (
        PhoneOTP.objects.filter(
            phone=phone, purpose=PhoneOTP.Purpose.PASSWORD_RESET, consumed=False
        )
        .order_by("-created_at")
        .first()
    )
    if otp is None or otp.expires_at < timezone.now():
        raise PasswordResetError("This code has expired. Please request a new one.")
    if otp.attempts >= otp_lib.MAX_ATTEMPTS:
        PhoneOTP.objects.filter(pk=otp.pk).update(consumed=True)
        raise PasswordResetError("Too many attempts. Please request a new code.")

    if not otp_lib.code_matches(code, otp.code_hash):
        PhoneOTP.objects.filter(pk=otp.pk).update(attempts=F("attempts") + 1)
        raise PasswordResetError("Incorrect code. Please check and try again.")

    # Correct code — set the password and consume the OTP atomically.
    with transaction.atomic():
        user = User.objects.select_for_update().get(phone=phone)
        user.set_password(new_password)
        user.save(update_fields=["password"])
        PhoneOTP.objects.filter(pk=otp.pk).update(consumed=True)
