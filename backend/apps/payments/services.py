"""Offline payment flows (V1: cash + transfer).

TRANSFER: PENDING -> CLAIMED (passenger "I have paid", optional reference)
                  -> PAID (assigned driver or admin confirms receipt)
CASH:     PENDING -> PAID (driver confirms receipt)

An online gateway later adds its own initiate/webhook path to the same
model without touching these rules.
"""
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.pricing.models import FareSetting
from apps.realtime.events import broadcast_ride_event
from apps.rides.constants import RideEventType, RideStatus
from apps.rides.models import Ride, RideEvent

from .constants import PaymentMethod, PaymentStatus
from .models import Payment

TWO_DP = Decimal("0.01")


def _locked_payment(ride_id: int) -> Payment:
    try:
        return Payment.objects.select_for_update().select_related("ride").get(ride_id=ride_id)
    except Payment.DoesNotExist:
        raise NotFound("Payment record not found.")


def claim_payment(*, ride_id: int, passenger, reference: str = "") -> Payment:
    with transaction.atomic():
        payment = _locked_payment(ride_id)
        ride = payment.ride

        if ride.passenger_id != passenger.id:
            raise PermissionDenied("You are not the passenger on this ride.")
        if payment.method != PaymentMethod.TRANSFER:
            raise ValidationError("Only transfer payments can be marked as sent.")
        if ride.status not in (RideStatus.IN_PROGRESS, RideStatus.COMPLETED):
            raise ValidationError("You can mark the payment once the trip has started.")
        if payment.status == PaymentStatus.PAID:
            raise ValidationError("This payment has already been confirmed.")
        if payment.status == PaymentStatus.FAILED:
            raise ValidationError("This payment is marked failed. Contact support.")

        # Re-claiming while CLAIMED just updates the reference
        payment.status = PaymentStatus.CLAIMED
        payment.claimed_by = passenger
        payment.claimed_at = timezone.now()
        payment.reference = reference.strip()[:128]
        payment.save(
            update_fields=["status", "claimed_by", "claimed_at", "reference", "updated_at"]
        )
        RideEvent.objects.create(
            ride=ride,
            event_type=RideEventType.PAYMENT_CLAIMED,
            actor=passenger,
            metadata={"reference": payment.reference},
        )

    broadcast_ride_event(ride, RideEventType.PAYMENT_CLAIMED)
    return payment


def confirm_payment(*, ride_id: int, user) -> Payment:
    with transaction.atomic():
        payment = _locked_payment(ride_id)
        ride = payment.ride

        if not (user.is_admin_role or ride.driver_id == user.id):
            raise PermissionDenied("Only the assigned driver or an admin can confirm payment.")
        if ride.status != RideStatus.COMPLETED:
            raise ValidationError("Complete the trip before confirming payment.")
        if payment.status == PaymentStatus.PAID:
            raise ValidationError("This payment has already been confirmed.")
        if payment.status == PaymentStatus.FAILED:
            raise ValidationError("This payment is marked failed. Contact support.")

        if payment.amount is None:  # defensive: completion normally sets it
            payment.amount = ride.final_fare
        payment.status = PaymentStatus.PAID
        payment.confirmed_by = user
        payment.confirmed_at = timezone.now()
        payment.save(
            update_fields=["status", "amount", "confirmed_by", "confirmed_at", "updated_at"]
        )
        RideEvent.objects.create(
            ride=ride,
            event_type=RideEventType.PAYMENT_CONFIRMED,
            actor=user,
            metadata={"amount": str(payment.amount), "method": payment.method},
        )

    broadcast_ride_event(ride, RideEventType.PAYMENT_CONFIRMED)
    return payment


def earnings_summary(driver_user) -> dict:
    """Completed-trip earnings: gross vs paid, plus platform commission and
    the driver's net. Rides completed before the commission feature simply
    have no commission record and count as commission zero."""
    from apps.commissions.services import driver_outstanding

    completed = Ride.objects.filter(driver=driver_user, status=RideStatus.COMPLETED)

    def stats(qs) -> dict:
        agg = qs.aggregate(
            trips=Count("id"),
            gross=Sum("final_fare"),
            paid=Sum("final_fare", filter=Q(payment__status=PaymentStatus.PAID)),
            commission=Sum("commission__commission_amount"),
        )
        gross = (agg["gross"] or Decimal("0")).quantize(TWO_DP)
        paid = (agg["paid"] or Decimal("0")).quantize(TWO_DP)
        commission = (agg["commission"] or Decimal("0")).quantize(TWO_DP)
        return {
            "trips": agg["trips"],
            "gross": str(gross),
            "paid": str(paid),
            "unpaid": str((gross - paid).quantize(TWO_DP)),
            "commission": str(commission),
            "net": str((gross - commission).quantize(TWO_DP)),
        }

    fare_setting = FareSetting.get_active()
    return {
        "currency": fare_setting.currency if fare_setting else "NGN",
        "outstanding_commission": str(driver_outstanding(driver_user)),
        "today": stats(completed.filter(completed_at__date=timezone.localdate())),
        "last_7_days": stats(completed.filter(completed_at__gte=timezone.now() - timedelta(days=7))),
        "all_time": stats(completed),
    }
