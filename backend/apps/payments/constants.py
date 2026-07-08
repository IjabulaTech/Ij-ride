from django.db import models


class PaymentMethod(models.TextChoices):
    """V1 supports offline methods only. CARD/gateway values slot in later."""

    CASH = "CASH", "Cash"
    TRANSFER = "TRANSFER", "Bank transfer"


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    # Passenger has claimed they sent a transfer; awaiting confirmation
    CLAIMED = "CLAIMED", "Claimed by passenger"
    # Confirmed received by driver or admin
    PAID = "PAID", "Paid"
    FAILED = "FAILED", "Failed"
