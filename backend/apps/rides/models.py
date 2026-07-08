from django.conf import settings
from django.db import models

from apps.drivers.models import VehicleCategory
from apps.payments.constants import PaymentMethod

from .constants import (
    ACTIVE_RIDE_STATUSES,
    DRIVER_BUSY_STATUSES,
    CancelledByRole,
    RideEventType,
    RideStatus,
)


class Ride(models.Model):
    passenger = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="rides_as_passenger"
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="rides_as_driver",
    )
    # Snapshot of the vehicle that served the trip, set on accept
    vehicle = models.ForeignKey(
        "drivers.Vehicle",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="rides",
    )
    status = models.CharField(
        max_length=16, choices=RideStatus.choices, default=RideStatus.SEARCHING, db_index=True
    )
    # What the passenger asked for; dispatch and accept enforce it
    requested_vehicle_category = models.CharField(
        max_length=16,
        choices=VehicleCategory.choices,
        default=VehicleCategory.CAR,  # pre-category rides were car rides
        db_index=True,
    )

    pickup_address = models.CharField(max_length=255)
    dropoff_address = models.CharField(max_length=255)
    pickup_lat = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_lng = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_lat = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_lng = models.DecimalField(max_digits=9, decimal_places=6)

    estimated_distance_m = models.PositiveIntegerField(null=True, blank=True)
    estimated_duration_s = models.PositiveIntegerField(null=True, blank=True)
    estimated_fare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_fare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # Which fare config priced this ride (audit)
    fare_setting = models.ForeignKey(
        "pricing.FareSetting",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="rides",
    )
    payment_method = models.CharField(
        max_length=16, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )

    # Lifecycle transition timestamps (created_at doubles as requested_at)
    accepted_at = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)

    cancelled_by_role = models.CharField(
        max_length=16, choices=CancelledByRole.choices, blank=True, default=""
    )
    cancelled_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rides_cancelled",
    )
    cancellation_reason = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["passenger", "-created_at"]),
            models.Index(fields=["driver", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["passenger"],
                condition=models.Q(status__in=ACTIVE_RIDE_STATUSES),
                name="rides_one_active_ride_per_passenger",
            ),
            models.UniqueConstraint(
                fields=["driver"],
                condition=models.Q(status__in=DRIVER_BUSY_STATUSES, driver__isnull=False),
                name="rides_one_active_ride_per_driver",
            ),
        ]

    def __str__(self):
        return f"Ride #{self.pk} [{self.status}] {self.pickup_address} -> {self.dropoff_address}"

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_RIDE_STATUSES


class RideEvent(models.Model):
    """Append-only audit trail of everything that happened to a ride."""

    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=20, choices=RideEventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ride_events",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["ride", "created_at"])]

    def __str__(self):
        return f"Ride #{self.ride_id}: {self.event_type} @ {self.created_at:%Y-%m-%d %H:%M:%S}"
