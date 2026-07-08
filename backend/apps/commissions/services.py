"""Commission math and remittance operations.

V1 business rules:
- Fixed commission is capped at the fare (driver earning never negative).
- Completing a ride with NO active commission setting records a zero
  commission already marked REMITTED, so reporting has no gaps and the
  driver owes nothing for that ride.
- Remittance is manual in V1: an admin confirms a driver's transfer either
  per ride or for everything the driver owes at once.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import CommissionType, PlatformCommissionSetting, RemittanceStatus, RideCommission

TWO_DP = Decimal("0.01")
ZERO = Decimal("0.00")


def compute_commission(fare: Decimal, setting: PlatformCommissionSetting) -> Decimal:
    if setting.commission_type == CommissionType.PERCENTAGE:
        amount = fare * setting.commission_value / Decimal("100")
    else:
        amount = setting.commission_value
    amount = amount.quantize(TWO_DP, rounding=ROUND_HALF_UP)
    return max(min(amount, fare), ZERO)


def record_commission_for_ride(ride) -> RideCommission:
    """Called inside the ride-completion transaction. Idempotent."""
    fare = ride.final_fare or ZERO
    setting = PlatformCommissionSetting.get_active()

    if setting is None:
        defaults = dict(
            driver=ride.driver,
            fare_amount=fare,
            commission_setting=None,
            commission_type="",
            commission_value=ZERO,
            commission_amount=ZERO,
            driver_earning=fare,
            status=RemittanceStatus.REMITTED,  # nothing owed, auto-settled
            remitted_at=timezone.now(),
            note="No active commission setting at completion",
        )
    else:
        commission = compute_commission(fare, setting)
        defaults = dict(
            driver=ride.driver,
            fare_amount=fare,
            commission_setting=setting,
            commission_type=setting.commission_type,
            commission_value=setting.commission_value,
            commission_amount=commission,
            driver_earning=fare - commission,
        )

    record, _created = RideCommission.objects.get_or_create(ride=ride, defaults=defaults)
    return record


def mark_remitted(commission: RideCommission, *, admin_user, note: str = "") -> RideCommission:
    if commission.status != RemittanceStatus.PENDING:
        raise ValidationError(
            f"This commission is already {commission.get_status_display().lower()}."
        )
    commission.status = RemittanceStatus.REMITTED
    commission.remitted_at = timezone.now()
    commission.confirmed_by = admin_user
    commission.note = note.strip()[:255]
    commission.save(
        update_fields=["status", "remitted_at", "confirmed_by", "note", "updated_at"]
    )
    return commission


@transaction.atomic
def settle_driver(*, driver_id: int, admin_user, note: str = "") -> dict:
    """Mark ALL of a driver's pending commissions remitted (the usual case:
    one bank transfer covering several rides)."""
    pending = RideCommission.objects.select_for_update().filter(
        driver_id=driver_id, status=RemittanceStatus.PENDING
    )
    totals = pending.aggregate(count=Count("id"), amount=Sum("commission_amount"))
    if not totals["count"]:
        raise ValidationError("This driver has no outstanding commission.")
    pending.update(
        status=RemittanceStatus.REMITTED,
        remitted_at=timezone.now(),
        confirmed_by=admin_user,
        note=note.strip()[:255],
        updated_at=timezone.now(),
    )
    return {"settled_count": totals["count"], "settled_amount": str(totals["amount"] or ZERO)}


def driver_outstanding(driver_user) -> Decimal:
    total = RideCommission.objects.filter(
        driver=driver_user, status=RemittanceStatus.PENDING
    ).aggregate(total=Sum("commission_amount"))["total"]
    return (total or ZERO).quantize(TWO_DP)


def platform_summary() -> dict:
    totals = RideCommission.objects.aggregate(
        total=Sum("commission_amount"),
        outstanding=Sum("commission_amount", filter=Q(status=RemittanceStatus.PENDING)),
        remitted=Sum("commission_amount", filter=Q(status=RemittanceStatus.REMITTED)),
        waived=Sum("commission_amount", filter=Q(status=RemittanceStatus.WAIVED)),
        rides=Count("id"),
    )
    drivers_owing = list(
        RideCommission.objects.filter(status=RemittanceStatus.PENDING)
        .values("driver_id", "driver__phone", "driver__first_name", "driver__last_name")
        .annotate(outstanding=Sum("commission_amount"), pending_rides=Count("id"))
        .order_by("-outstanding")
    )
    return {
        "totals": {
            "commission_total": str((totals["total"] or ZERO).quantize(TWO_DP)),
            "outstanding": str((totals["outstanding"] or ZERO).quantize(TWO_DP)),
            "remitted": str((totals["remitted"] or ZERO).quantize(TWO_DP)),
            "waived": str((totals["waived"] or ZERO).quantize(TWO_DP)),
            "rides_with_commission": totals["rides"],
        },
        "drivers_owing": [
            {
                "driver_id": row["driver_id"],
                "phone": row["driver__phone"],
                "name": " ".join(
                    p for p in (row["driver__first_name"], row["driver__last_name"]) if p
                ),
                "outstanding": str(row["outstanding"].quantize(TWO_DP)),
                "pending_rides": row["pending_rides"],
            }
            for row in drivers_owing
        ],
    }
