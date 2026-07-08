"""Driver onboarding and approval business rules."""
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import DriverApprovalStatus, DriverAvailability, DriverProfile, VehicleCategory


def enforce_driver_vehicle_category(profile: DriverProfile, vehicle_category: str) -> None:
    """V1 rule: KEKE drivers register KEKE vehicles, CAR drivers register CAR.
    Called from the vehicle upsert view before persisting."""
    if profile.driver_category and vehicle_category != profile.driver_category:
        driver_label = VehicleCategory(profile.driver_category).label
        vehicle_label = VehicleCategory(vehicle_category).label
        raise ValidationError(
            {
                "category": (
                    f"You registered as a {driver_label} driver, so your vehicle must be a "
                    f"{driver_label}. To operate a {vehicle_label} instead, contact support."
                )
            }
        )


def _force_offline(profile: DriverProfile) -> None:
    # Mutate the instance (not a queryset .update()) so callers holding a
    # select_related copy serialize the fresh state, not a stale cache.
    try:
        availability = profile.availability
    except DriverAvailability.DoesNotExist:
        return
    if availability.is_online:
        availability.is_online = False
        availability.save(update_fields=["is_online", "updated_at"])


def update_driver_profile(profile: DriverProfile, *, license_number: str) -> DriverProfile:
    """Changing the license after a review verdict re-queues the driver for
    approval — identity data must always match what the admin approved."""
    license_changed = license_number != profile.license_number
    profile.license_number = license_number
    if license_changed and profile.approval_status != DriverApprovalStatus.PENDING:
        profile.approval_status = DriverApprovalStatus.PENDING
        profile.approval_note = ""
        profile.approved_at = None
        profile.approved_by = None
        _force_offline(profile)
    profile.save()
    return profile


def set_availability(profile: DriverProfile, *, is_online: bool) -> DriverAvailability:
    availability = profile.availability
    if is_online:
        if not profile.is_approved:
            raise ValidationError("Your driver account has not been approved yet.")
        if not profile.vehicles.filter(is_active=True).exists():
            raise ValidationError("Register a vehicle before going online.")
    availability.is_online = is_online
    availability.last_seen_at = timezone.now()
    availability.save(update_fields=["is_online", "last_seen_at", "updated_at"])
    return availability


def update_location(profile: DriverProfile, *, lat, lng) -> DriverAvailability:
    availability = profile.availability
    now = timezone.now()
    availability.current_lat = lat
    availability.current_lng = lng
    availability.location_updated_at = now
    availability.last_seen_at = now
    availability.save(
        update_fields=["current_lat", "current_lng", "location_updated_at", "last_seen_at", "updated_at"]
    )
    return availability


def approve_driver(profile: DriverProfile, *, admin_user, note: str = "") -> DriverProfile:
    if profile.approval_status == DriverApprovalStatus.APPROVED:
        raise ValidationError("Driver is already approved.")
    profile.approval_status = DriverApprovalStatus.APPROVED
    profile.approval_note = note
    profile.approved_at = timezone.now()
    profile.approved_by = admin_user
    profile.save(
        update_fields=["approval_status", "approval_note", "approved_at", "approved_by", "updated_at"]
    )
    return profile


def reject_driver(profile: DriverProfile, *, admin_user, reason: str) -> DriverProfile:
    if profile.approval_status == DriverApprovalStatus.REJECTED:
        raise ValidationError("Driver is already rejected.")
    profile.approval_status = DriverApprovalStatus.REJECTED
    profile.approval_note = reason
    profile.approved_at = None
    profile.approved_by = admin_user
    profile.save(
        update_fields=["approval_status", "approval_note", "approved_at", "approved_by", "updated_at"]
    )
    _force_offline(profile)
    return profile
