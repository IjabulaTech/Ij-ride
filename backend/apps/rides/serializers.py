from decimal import Decimal

from rest_framework import serializers

from apps.drivers.models import VehicleCategory
from apps.drivers.serializers import VehicleSerializer
from apps.payments.constants import PaymentMethod
from apps.payments.models import Payment

from .models import Ride
from .services import RideEstimate

# ---------------------------------------------------------------------------
# Estimation (Module 5)
# ---------------------------------------------------------------------------


class LocationInputSerializer(serializers.Serializer):
    """Either coordinates (both lat and lng) or a non-empty address."""

    address = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    lat = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True, default=None,
        min_value=Decimal("-90"), max_value=Decimal("90"),
    )
    lng = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True, default=None,
        min_value=Decimal("-180"), max_value=Decimal("180"),
    )

    def validate(self, attrs):
        has_coords = attrs["lat"] is not None and attrs["lng"] is not None
        if (attrs["lat"] is None) != (attrs["lng"] is None):
            raise serializers.ValidationError("Provide both lat and lng, or neither.")
        if not has_coords and not attrs["address"].strip():
            raise serializers.ValidationError("Provide an address or coordinates.")
        return attrs


class EstimateRequestSerializer(serializers.Serializer):
    vehicle_category = serializers.ChoiceField(choices=VehicleCategory.choices)
    pickup = LocationInputSerializer()
    dropoff = LocationInputSerializer()


def serialize_estimate(estimate: RideEstimate) -> dict:
    def location(loc):
        return {"address": loc.address, "lat": str(loc.lat), "lng": str(loc.lng)}

    return {
        "vehicle_category": estimate.vehicle_category,
        "pickup": location(estimate.pickup),
        "dropoff": location(estimate.dropoff),
        "distance_m": estimate.distance_m,
        "duration_s": estimate.duration_s,
        "fare": str(estimate.fare),
        "currency": estimate.currency,
        "breakdown": estimate.breakdown,
    }


# ---------------------------------------------------------------------------
# Ride lifecycle (Module 6)
# ---------------------------------------------------------------------------


class RideUserSerializer(serializers.Serializer):
    """Counterparty contact card — enough to identify and call each other.
    `photo_url` is the driver's personal profile photo (null for passengers,
    who have no driver profile in V1)."""

    id = serializers.IntegerField(read_only=True)
    phone = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    photo_url = serializers.SerializerMethodField()

    def get_photo_url(self, user) -> str | None:
        from apps.drivers.serializers import build_media_url

        profile = getattr(user, "driver_profile", None)
        if profile is None or not profile.photo:
            return None
        return build_media_url(profile.photo, self.context.get("request"))


class RidePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "method",
            "status",
            "amount",
            "currency",
            "reference",
            "claimed_at",
            "confirmed_at",
        )
        read_only_fields = fields


class RideDetailSerializer(serializers.ModelSerializer):
    passenger = RideUserSerializer(read_only=True)
    driver = RideUserSerializer(read_only=True)
    vehicle = VehicleSerializer(read_only=True)
    payment = RidePaymentSerializer(read_only=True)

    class Meta:
        model = Ride
        fields = (
            "id",
            "status",
            "requested_vehicle_category",
            "passenger",
            "driver",
            "vehicle",
            "pickup_address",
            "pickup_lat",
            "pickup_lng",
            "dropoff_address",
            "dropoff_lat",
            "dropoff_lng",
            "estimated_distance_m",
            "estimated_duration_s",
            "estimated_fare",
            "final_fare",
            "payment_method",
            "payment",
            "accepted_at",
            "arrived_at",
            "started_at",
            "completed_at",
            "cancelled_at",
            "expired_at",
            "cancelled_by_role",
            "cancellation_reason",
            "created_at",
        )
        read_only_fields = fields


class RideListSerializer(serializers.ModelSerializer):
    """Compact row for history lists."""

    class Meta:
        model = Ride
        fields = (
            "id",
            "status",
            "requested_vehicle_category",
            "pickup_address",
            "dropoff_address",
            "estimated_fare",
            "final_fare",
            "payment_method",
            "created_at",
            "completed_at",
            "cancelled_at",
        )
        read_only_fields = fields


class OpenRideSerializer(serializers.ModelSerializer):
    """What a driver sees in the open-requests feed."""

    passenger_first_name = serializers.CharField(source="passenger.first_name", read_only=True)

    class Meta:
        model = Ride
        fields = (
            "id",
            "requested_vehicle_category",
            "pickup_address",
            "pickup_lat",
            "pickup_lng",
            "dropoff_address",
            "dropoff_lat",
            "dropoff_lng",
            "estimated_distance_m",
            "estimated_duration_s",
            "estimated_fare",
            "payment_method",
            "passenger_first_name",
            "created_at",
        )
        read_only_fields = fields


class CreateRideSerializer(serializers.Serializer):
    vehicle_category = serializers.ChoiceField(choices=VehicleCategory.choices)
    pickup = LocationInputSerializer()
    dropoff = LocationInputSerializer()
    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices, required=False, allow_blank=True, default=""
    )


class CancelRideSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
