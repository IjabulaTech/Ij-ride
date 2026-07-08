from django.conf import settings
from django.db import models

from .constants import PaymentMethod, PaymentStatus


class Payment(models.Model):
    """One payment record per ride, created with the ride.

    Offline V1 flow:
      CASH:     PENDING -> PAID (driver confirms receipt)
      TRANSFER: PENDING -> CLAIMED (passenger marks "I have paid")
                        -> PAID (driver or admin confirms)

    `provider` / `provider_ref` stay empty in V1; an online gateway later
    reuses this model (initiate -> webhook -> PAID/FAILED) without redesign.
    """

    ride = models.OneToOneField(
        "rides.Ride", on_delete=models.CASCADE, related_name="payment"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="NGN")
    method = models.CharField(max_length=16, choices=PaymentMethod.choices)
    status = models.CharField(
        max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.PENDING, db_index=True
    )

    # Passenger's "I have paid" intent (transfer flow)
    claimed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payments_claimed",
    )
    claimed_at = models.DateTimeField(null=True, blank=True)
    # Optional transfer reference/narration the passenger provides
    reference = models.CharField(max_length=128, blank=True, default="")

    # Driver/admin confirmation
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payments_confirmed",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)

    # Reserved for online gateway integration (Paystack/Flutterwave/...)
    provider = models.CharField(max_length=32, blank=True, default="")
    provider_ref = models.CharField(max_length=128, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment for ride #{self.ride_id} [{self.method}/{self.status}]"
