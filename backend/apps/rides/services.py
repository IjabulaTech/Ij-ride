"""Ride orchestration: estimation (Module 5) and the full trip lifecycle
(Module 6). All state transitions run under select_for_update row locks so
concurrent actions (two drivers accepting, double taps) resolve cleanly;
the partial unique constraints from Module 2 are the second safety net.
"""
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.commissions.services import record_commission_for_ride
from apps.geo.service import get_geo_provider
from apps.payments.constants import PaymentMethod
from apps.payments.models import Payment
from apps.pricing.models import FareSetting
from apps.pricing.services import calculate_fare
from apps.realtime.events import broadcast_ride_event

from .constants import (
    ACTIVE_RIDE_STATUSES,
    DRIVER_BUSY_STATUSES,
    TERMINAL_RIDE_STATUSES,
    CancelledByRole,
    RideEventType,
    RideStatus,
)
from .models import Ride, RideEvent

# ---------------------------------------------------------------------------
# Estimation (Module 5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedLocation:
    address: str
    lat: Decimal
    lng: Decimal


@dataclass(frozen=True)
class RideEstimate:
    vehicle_category: str
    pickup: ResolvedLocation
    dropoff: ResolvedLocation
    distance_m: int
    duration_s: int
    fare: Decimal
    currency: str
    breakdown: dict
    fare_setting: FareSetting


def resolve_location(*, address: str = "", lat=None, lng=None) -> ResolvedLocation:
    """Coordinates win when provided (frontend map/GPS pick); otherwise the
    address text is geocoded through the configured provider."""
    if lat is not None and lng is not None:
        return ResolvedLocation(address=address or f"{lat},{lng}", lat=lat, lng=lng)
    result = get_geo_provider().geocode(address)
    return ResolvedLocation(address=result.address, lat=result.lat, lng=result.lng)


def estimate_ride(*, pickup: dict, dropoff: dict, vehicle_category: str) -> RideEstimate:
    resolved_pickup = resolve_location(**pickup)
    resolved_dropoff = resolve_location(**dropoff)

    route = get_geo_provider().route(
        (resolved_pickup.lat, resolved_pickup.lng),
        (resolved_dropoff.lat, resolved_dropoff.lng),
    )

    fare_setting = FareSetting.get_active(vehicle_category)
    if fare_setting is None:
        raise ValidationError(
            f"Fares are not configured for {vehicle_category} rides yet. Please try again later."
        )

    fare, breakdown = calculate_fare(
        distance_m=route.distance_m, duration_s=route.duration_s, fare_setting=fare_setting
    )
    return RideEstimate(
        vehicle_category=vehicle_category,
        pickup=resolved_pickup,
        dropoff=resolved_dropoff,
        distance_m=route.distance_m,
        duration_s=route.duration_s,
        fare=fare,
        currency=fare_setting.currency,
        breakdown=breakdown,
        fare_setting=fare_setting,
    )


# ---------------------------------------------------------------------------
# Lifecycle helpers
# ---------------------------------------------------------------------------


def _search_cutoff():
    return timezone.now() - timedelta(minutes=settings.RIDE_SEARCH_TIMEOUT_MINUTES)


def _locked_ride(ride_id: int) -> Ride:
    try:
        return Ride.objects.select_for_update().get(pk=ride_id)
    except Ride.DoesNotExist:
        raise NotFound("Ride not found.")


def _expire(ride: Ride) -> None:
    """Caller must hold the row lock."""
    ride.status = RideStatus.EXPIRED
    ride.expired_at = timezone.now()
    ride.save(update_fields=["status", "expired_at", "updated_at"])
    RideEvent.objects.create(ride=ride, event_type=RideEventType.EXPIRED)
    broadcast_ride_event(ride, RideEventType.EXPIRED)


def _is_stale_searching(ride: Ride) -> bool:
    return ride.status == RideStatus.SEARCHING and ride.created_at < _search_cutoff()


# ---------------------------------------------------------------------------
# Passenger: request a ride
# ---------------------------------------------------------------------------


def create_ride(
    *, passenger, pickup: dict, dropoff: dict, vehicle_category: str, payment_method: str = ""
) -> Ride:
    if Ride.objects.filter(passenger=passenger, status__in=ACTIVE_RIDE_STATUSES).exists():
        raise ValidationError("You already have an active ride.")

    estimate = estimate_ride(pickup=pickup, dropoff=dropoff, vehicle_category=vehicle_category)

    if not payment_method:
        profile = getattr(passenger, "passenger_profile", None)
        payment_method = profile.default_payment_method if profile else PaymentMethod.CASH

    try:
        with transaction.atomic():
            ride = Ride.objects.create(
                passenger=passenger,
                requested_vehicle_category=vehicle_category,
                pickup_address=estimate.pickup.address[:255],
                dropoff_address=estimate.dropoff.address[:255],
                pickup_lat=estimate.pickup.lat,
                pickup_lng=estimate.pickup.lng,
                dropoff_lat=estimate.dropoff.lat,
                dropoff_lng=estimate.dropoff.lng,
                estimated_distance_m=estimate.distance_m,
                estimated_duration_s=estimate.duration_s,
                estimated_fare=estimate.fare,
                fare_setting=estimate.fare_setting,
                payment_method=payment_method,
            )
            Payment.objects.create(ride=ride, method=payment_method, currency=estimate.currency)
            RideEvent.objects.create(
                ride=ride, event_type=RideEventType.REQUESTED, actor=passenger
            )
    except IntegrityError:
        # lost a race with another request from the same passenger
        raise ValidationError("You already have an active ride.")

    broadcast_ride_event(ride, RideEventType.REQUESTED)
    return ride


# ---------------------------------------------------------------------------
# Driver: accept / reject
# ---------------------------------------------------------------------------


def accept_ride(*, ride_id: int, driver_user) -> Ride:
    profile = driver_user.driver_profile
    if not profile.availability.is_online:
        raise ValidationError("Go online to accept ride requests.")
    vehicle = profile.vehicles.filter(is_active=True).first()
    if vehicle is None:
        raise ValidationError("Register a vehicle before accepting rides.")
    if Ride.objects.filter(driver=driver_user, status__in=DRIVER_BUSY_STATUSES).exists():
        raise ValidationError("You already have an active trip.")

    expired = False
    try:
        with transaction.atomic():
            ride = _locked_ride(ride_id)
            if _is_stale_searching(ride):
                _expire(ride)
                expired = True
            elif ride.status != RideStatus.SEARCHING:
                raise ValidationError("This ride is no longer available.")
            elif ride.requested_vehicle_category != vehicle.category:
                raise ValidationError(
                    f"This ride requires a {ride.get_requested_vehicle_category_display()}."
                )
            else:
                ride.driver = driver_user
                ride.vehicle = vehicle
                ride.status = RideStatus.ACCEPTED
                ride.accepted_at = timezone.now()
                ride.save(
                    update_fields=["driver", "vehicle", "status", "accepted_at", "updated_at"]
                )
                RideEvent.objects.create(
                    ride=ride, event_type=RideEventType.ACCEPTED, actor=driver_user
                )
    except IntegrityError:
        # lost a race against our own concurrent accept on another ride
        raise ValidationError("You already have an active trip.")

    if expired:
        raise ValidationError("This ride request has expired.")

    broadcast_ride_event(ride, RideEventType.ACCEPTED)
    return ride


def reject_ride(*, ride_id: int, driver_user) -> None:
    """Broadcast dispatch: a rejection only hides the ride from this driver's
    open feed. The ride stays SEARCHING for everyone else."""
    try:
        ride = Ride.objects.get(pk=ride_id)
    except Ride.DoesNotExist:
        raise NotFound("Ride not found.")
    if ride.status != RideStatus.SEARCHING:
        raise ValidationError("This ride is no longer open.")
    if not RideEvent.objects.filter(
        ride=ride, event_type=RideEventType.REJECTED, actor=driver_user
    ).exists():
        RideEvent.objects.create(ride=ride, event_type=RideEventType.REJECTED, actor=driver_user)


# ---------------------------------------------------------------------------
# Driver: trip progression
# ---------------------------------------------------------------------------

_TRANSITIONS = {
    "arrived": (RideStatus.ACCEPTED, RideStatus.DRIVER_ARRIVED, "arrived_at", RideEventType.DRIVER_ARRIVED),
    "start": (RideStatus.DRIVER_ARRIVED, RideStatus.IN_PROGRESS, "started_at", RideEventType.TRIP_STARTED),
    "complete": (RideStatus.IN_PROGRESS, RideStatus.COMPLETED, "completed_at", RideEventType.TRIP_COMPLETED),
}


def driver_transition(*, ride_id: int, driver_user, action: str) -> Ride:
    expected, target, ts_field, event_type = _TRANSITIONS[action]
    with transaction.atomic():
        ride = _locked_ride(ride_id)
        if ride.driver_id != driver_user.id:
            raise PermissionDenied("You are not the driver for this ride.")
        if ride.status != expected:
            raise ValidationError(
                f"Cannot {action} a ride in status {ride.get_status_display()!r}."
            )
        ride.status = target
        setattr(ride, ts_field, timezone.now())
        update_fields = ["status", ts_field, "updated_at"]
        metadata = {}

        if action == "complete":
            ride.final_fare = ride.estimated_fare  # V1: no en-route re-pricing
            update_fields.append("final_fare")
            try:
                payment = ride.payment
            except Payment.DoesNotExist:
                payment = Payment.objects.create(ride=ride, method=ride.payment_method)
            payment.amount = ride.final_fare
            payment.save(update_fields=["amount", "updated_at"])
            metadata = {"final_fare": str(ride.final_fare)}
            # Platform commission record, atomic with completion
            commission = record_commission_for_ride(ride)
            metadata["commission"] = str(commission.commission_amount)

        ride.save(update_fields=update_fields)
        RideEvent.objects.create(
            ride=ride, event_type=event_type, actor=driver_user, metadata=metadata
        )

    broadcast_ride_event(ride, event_type)
    return ride


# ---------------------------------------------------------------------------
# Cancellation (tightened rules) and expiry
# ---------------------------------------------------------------------------


def cancel_ride(*, ride_id: int, user, reason: str = "") -> Ride:
    reason = reason.strip()
    with transaction.atomic():
        ride = _locked_ride(ride_id)

        if user.is_admin_role:
            role = CancelledByRole.ADMIN
        elif ride.passenger_id == user.id:
            role = CancelledByRole.PASSENGER
        elif ride.driver_id == user.id:
            role = CancelledByRole.DRIVER
        else:
            raise PermissionDenied("You are not part of this ride.")

        if ride.status in TERMINAL_RIDE_STATUSES:
            raise ValidationError("This ride is already finished.")
        # V1 rule: passengers may only cancel while the search is still open.
        # Once a driver has accepted, only the driver or an admin can cancel.
        if role == CancelledByRole.PASSENGER and ride.status != RideStatus.SEARCHING:
            raise ValidationError(
                "You can no longer cancel this ride because a driver has already accepted it."
            )
        if ride.status == RideStatus.IN_PROGRESS and role != CancelledByRole.ADMIN:
            raise ValidationError(
                "A trip in progress cannot be cancelled. Contact support if something is wrong."
            )
        if role == CancelledByRole.DRIVER and not reason:
            raise ValidationError({"reason": "Please provide a reason for cancelling."})

        ride.status = RideStatus.CANCELLED
        ride.cancelled_at = timezone.now()
        ride.cancelled_by_role = role
        ride.cancelled_by_user = user
        ride.cancellation_reason = reason[:255]
        ride.save(
            update_fields=[
                "status",
                "cancelled_at",
                "cancelled_by_role",
                "cancelled_by_user",
                "cancellation_reason",
                "updated_at",
            ]
        )
        RideEvent.objects.create(
            ride=ride,
            event_type=RideEventType.CANCELLED,
            actor=user,
            metadata={"role": role, "reason": reason},
        )

    broadcast_ride_event(ride, RideEventType.CANCELLED)
    return ride


def expire_stale_rides() -> int:
    """Expire all overdue SEARCHING rides. Called by the expire_rides
    management command (cron in production) and opportunistically."""
    stale_ids = list(
        Ride.objects.filter(
            status=RideStatus.SEARCHING, created_at__lt=_search_cutoff()
        ).values_list("id", flat=True)
    )
    count = 0
    for ride_id in stale_ids:
        with transaction.atomic():
            ride = Ride.objects.select_for_update().get(pk=ride_id)
            if _is_stale_searching(ride):  # recheck under lock
                _expire(ride)
                count += 1
    return count


# ---------------------------------------------------------------------------
# Queries: active ride, history, open feed
# ---------------------------------------------------------------------------

_RIDE_RELATED = ("passenger", "driver", "vehicle", "payment")


def active_ride_for(user) -> Ride | None:
    if user.is_driver:
        qs = Ride.objects.filter(driver=user, status__in=DRIVER_BUSY_STATUSES)
    else:
        qs = Ride.objects.filter(passenger=user, status__in=ACTIVE_RIDE_STATUSES)
    ride = qs.select_related(*_RIDE_RELATED).first()
    if ride is not None and _is_stale_searching(ride):
        with transaction.atomic():
            locked = Ride.objects.select_for_update().get(pk=ride.pk)
            if _is_stale_searching(locked):
                _expire(locked)
        return None
    return ride


def history_for(user):
    """Terminal rides only — active rides live at /rides/active/."""
    if user.is_passenger:
        qs = Ride.objects.filter(passenger=user)
    elif user.is_driver:
        qs = Ride.objects.filter(driver=user)
    else:
        raise PermissionDenied("Use the management API to browse ride records.")
    return qs.filter(status__in=TERMINAL_RIDE_STATUSES).select_related(*_RIDE_RELATED)


def open_rides_for(driver_user):
    """Fresh SEARCHING rides matching the driver's active vehicle category,
    excluding ones they rejected, oldest first."""
    active_vehicle = driver_user.driver_profile.vehicles.filter(is_active=True).first()
    if active_vehicle is None:
        return Ride.objects.none()
    return (
        Ride.objects.filter(
            status=RideStatus.SEARCHING,
            created_at__gte=_search_cutoff(),
            requested_vehicle_category=active_vehicle.category,
        )
        .exclude(events__event_type=RideEventType.REJECTED, events__actor=driver_user)
        .select_related("passenger")
        .order_by("created_at")
    )
