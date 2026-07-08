from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class CommissionType(models.TextChoices):
    PERCENTAGE = "PERCENTAGE", "Percentage of fare"
    FIXED = "FIXED", "Fixed amount per ride"


class RemittanceStatus(models.TextChoices):
    PENDING = "PENDING", "Pending remittance"
    REMITTED = "REMITTED", "Remitted"
    WAIVED = "WAIVED", "Waived"  # ops forgiveness, set via Django admin


class PlatformCommissionSetting(models.Model):
    """Platform commission rule. Same pattern as FareSetting: exactly one
    active row; changes create a new row so completed rides keep a reference
    to the rule that priced their commission."""

    commission_type = models.CharField(max_length=16, choices=CommissionType.choices)
    # PERCENTAGE: 15.00 means 15% of the fare. FIXED: naira amount per ride.
    commission_value = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    is_active = models.BooleanField(default=False, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="commission_settings_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=models.Q(is_active=True),
                name="commissions_single_active_setting",
            ),
        ]

    def clean(self):
        if (
            self.commission_type == CommissionType.PERCENTAGE
            and self.commission_value is not None
            and self.commission_value > 100
        ):
            raise ValidationError({"commission_value": "Percentage cannot exceed 100."})

    def __str__(self):
        flag = "ACTIVE" if self.is_active else "inactive"
        unit = "%" if self.commission_type == CommissionType.PERCENTAGE else " NGN/ride"
        return f"Commission #{self.pk} [{flag}] {self.commission_value}{unit}"

    @classmethod
    def get_active(cls) -> "PlatformCommissionSetting | None":
        return cls.objects.filter(is_active=True).first()


class RideCommission(models.Model):
    """The platform's cut of one completed ride, and whether the driver has
    remitted it. Created atomically with ride completion."""

    ride = models.OneToOneField(
        "rides.Ride", on_delete=models.CASCADE, related_name="commission"
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ride_commissions"
    )
    fare_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Snapshot of the rule applied (empty when no setting was active)
    commission_setting = models.ForeignKey(
        PlatformCommissionSetting,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ride_commissions",
    )
    commission_type = models.CharField(
        max_length=16, choices=CommissionType.choices, blank=True, default=""
    )
    commission_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))

    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    driver_earning = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(
        max_length=16,
        choices=RemittanceStatus.choices,
        default=RemittanceStatus.PENDING,
        db_index=True,
    )
    remitted_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="commissions_confirmed",
    )
    note = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["driver", "status"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(commission_amount__gte=0),
                name="commissions_amount_not_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(driver_earning__gte=0),
                name="commissions_earning_not_negative",
            ),
        ]

    def __str__(self):
        return (
            f"Commission for ride #{self.ride_id}: {self.commission_amount} [{self.status}]"
        )
