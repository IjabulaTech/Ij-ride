"""Fare math and fare-setting administration."""
from decimal import ROUND_CEILING, Decimal

from django.db import transaction
from django.utils import timezone

from .models import FareSetting

TWO_DP = Decimal("0.01")


@transaction.atomic
def activate_new_fare_setting(*, created_by, vehicle_category, **fields) -> FareSetting:
    """Fare changes create a new active row FOR THAT CATEGORY (old rows keep
    pricing history for the rides that reference them)."""
    FareSetting.objects.filter(is_active=True, vehicle_category=vehicle_category).update(
        is_active=False, updated_at=timezone.now()
    )
    return FareSetting.objects.create(
        is_active=True, created_by=created_by, vehicle_category=vehicle_category, **fields
    )


def calculate_fare(
    *, distance_m: int, duration_s: int, fare_setting: FareSetting
) -> tuple[Decimal, dict]:
    """fare = max(minimum, base + per_km*km + per_minute*min), rounded UP to
    the configured step. Returns (fare, breakdown)."""
    km = Decimal(distance_m) / 1000
    minutes = Decimal(duration_s) / 60

    distance_fare = (fare_setting.per_km * km).quantize(TWO_DP)
    time_fare = (fare_setting.per_minute * minutes).quantize(TWO_DP)
    raw = fare_setting.base_fare + distance_fare + time_fare

    minimum_applied = raw < fare_setting.minimum_fare
    fare = max(raw, fare_setting.minimum_fare)

    step = fare_setting.rounding_step
    if step and step > 0:
        fare = (fare / step).to_integral_value(rounding=ROUND_CEILING) * step
    fare = fare.quantize(TWO_DP)

    breakdown = {
        "base_fare": str(fare_setting.base_fare),
        "distance_fare": str(distance_fare),
        "time_fare": str(time_fare),
        "minimum_fare_applied": minimum_applied,
        "rounding_step": str(step),
    }
    return fare, breakdown
