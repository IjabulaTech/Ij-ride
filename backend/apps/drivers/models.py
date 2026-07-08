from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class DriverApprovalStatus(models.TextChoices):
    PENDING = "PENDING", "Pending review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class VehicleCategory(models.TextChoices):
    """Ride categories. Extend here for BIKE/BUS/DELIVERY/PREMIUM later —
    pricing, dispatch, and the APIs are all keyed off these values."""

    KEKE = "KEKE", "Keke (tricycle)"
    CAR = "CAR", "Car"


class DriverProfile(models.Model):
    """Identity and approval data for a driver. Operational online/location
    state deliberately lives in DriverAvailability, not here."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="driver_profile"
    )
    # V1: a driver commits to one operating category at signup. The active
    # Vehicle's category must match this; enforced in the service layer.
    driver_category = models.CharField(
        max_length=16,
        choices=VehicleCategory.choices,
        default=VehicleCategory.CAR,
        db_index=True,
    )
    license_number = models.CharField(max_length=64, blank=True, default="")
    approval_status = models.CharField(
        max_length=16,
        choices=DriverApprovalStatus.choices,
        default=DriverApprovalStatus.PENDING,
        db_index=True,
    )
    approval_note = models.TextField(blank=True, default="")  # e.g. rejection reason
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="drivers_approved",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # optional during onboarding, but unique once provided
            models.UniqueConstraint(
                fields=["license_number"],
                condition=~models.Q(license_number=""),
                name="drivers_unique_license_when_set",
            ),
        ]

    def __str__(self):
        return f"Driver {self.user.phone} [{self.get_approval_status_display()}]"

    @property
    def is_approved(self) -> bool:
        return self.approval_status == DriverApprovalStatus.APPROVED


class DriverAvailability(models.Model):
    """Live operational state: online flag and last known location.
    One row per driver, created together with the profile."""

    driver = models.OneToOneField(
        DriverProfile, on_delete=models.CASCADE, related_name="availability"
    )
    is_online = models.BooleanField(default=False, db_index=True)
    current_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_updated_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "driver availabilities"

    def __str__(self):
        state = "online" if self.is_online else "offline"
        return f"{self.driver.user.phone} ({state})"


class Vehicle(models.Model):
    """A driver's vehicle. FK (not OneToOne) so fleet/multi-vehicle support
    is a data change later; V1 allows exactly one ACTIVE vehicle per driver,
    enforced by the partial unique constraint below plus service-layer checks."""

    driver = models.ForeignKey(
        DriverProfile, on_delete=models.CASCADE, related_name="vehicles"
    )
    category = models.CharField(
        max_length=16,
        choices=VehicleCategory.choices,
        default=VehicleCategory.CAR,  # pre-category vehicles were all cars
        db_index=True,
    )
    make = models.CharField(max_length=64)
    model = models.CharField(max_length=64)
    year = models.PositiveSmallIntegerField(validators=[MinValueValidator(1980)])
    color = models.CharField(max_length=32)
    plate_number = models.CharField(max_length=20, unique=True)
    photo = models.ImageField(upload_to="vehicles/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["driver"],
                condition=models.Q(is_active=True),
                name="drivers_one_active_vehicle_per_driver",
            ),
        ]

    def __str__(self):
        return f"{self.make} {self.model} ({self.plate_number})"
