from decimal import Decimal

from rest_framework import serializers

from apps.drivers.models import VehicleCategory

from .models import FareSetting

ZERO = Decimal("0")


class FareSettingSerializer(serializers.ModelSerializer):
    # Explicit so admins must say which category they are pricing
    vehicle_category = serializers.ChoiceField(choices=VehicleCategory.choices)
    base_fare = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=ZERO)
    per_km = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=ZERO)
    per_minute = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=ZERO)
    minimum_fare = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=ZERO)
    rounding_step = serializers.DecimalField(
        max_digits=6, decimal_places=2, min_value=ZERO, required=False
    )

    class Meta:
        model = FareSetting
        fields = (
            "id",
            "vehicle_category",
            "base_fare",
            "per_km",
            "per_minute",
            "minimum_fare",
            "rounding_step",
            "currency",
            "is_active",
            "created_by",
            "created_at",
        )
        read_only_fields = ("id", "is_active", "created_by", "created_at")
