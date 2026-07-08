"""Registration services. Profile rows are created here, explicitly and
atomically — views and serializers never create model rows themselves."""
from django.db import transaction

from apps.drivers.models import DriverAvailability, DriverProfile, VehicleCategory

from .models import PassengerProfile, User, UserRole


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
