from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.drivers.models import VehicleCategory


class FareSetting(models.Model):
    """Fare configuration, one per vehicle category. Exactly one row may be
    active PER CATEGORY (partial unique constraint); changing fares means
    creating a new active row so completed rides keep a reference to the
    config that priced them."""

    vehicle_category = models.CharField(
        max_length=16,
        choices=VehicleCategory.choices,
        default=VehicleCategory.CAR,  # pre-category configs priced car rides
        db_index=True,
    )
    base_fare = models.DecimalField(max_digits=10, decimal_places=2)
    per_km = models.DecimalField(max_digits=10, decimal_places=2)
    per_minute = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_fare = models.DecimalField(max_digits=10, decimal_places=2)
    # Estimates are rounded UP to this step (e.g. NGN 50)
    rounding_step = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("50.00")
    )
    currency = models.CharField(max_length=3, default="NGN")
    is_active = models.BooleanField(default=False, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fare_settings_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehicle_category"],
                condition=models.Q(is_active=True),
                name="pricing_single_active_fare_per_category",
            ),
        ]

    def __str__(self):
        flag = "ACTIVE" if self.is_active else "inactive"
        return (
            f"FareSetting #{self.pk} [{flag}] {self.vehicle_category}: base {self.base_fare}"
            f" + {self.per_km}/km + {self.per_minute}/min (min {self.minimum_fare})"
        )

    @classmethod
    def get_active(cls, category: str | None = None) -> "FareSetting | None":
        """Active setting for a category; with no category, any active row
        (used only for currency lookup)."""
        qs = cls.objects.filter(is_active=True)
        if category:
            qs = qs.filter(vehicle_category=category)
        return qs.first()
