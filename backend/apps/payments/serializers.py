from rest_framework import serializers

from .models import Payment


class ClaimPaymentSerializer(serializers.Serializer):
    reference = serializers.CharField(
        max_length=128, required=False, allow_blank=True, default=""
    )


class PaymentAdminSerializer(serializers.ModelSerializer):
    """Management view: payment plus enough ride context to reconcile."""

    ride_id = serializers.IntegerField(read_only=True)
    ride_status = serializers.CharField(source="ride.status", read_only=True)
    passenger_phone = serializers.CharField(source="ride.passenger.phone", read_only=True)
    driver_phone = serializers.SerializerMethodField()
    pickup_address = serializers.CharField(source="ride.pickup_address", read_only=True)
    dropoff_address = serializers.CharField(source="ride.dropoff_address", read_only=True)
    confirmed_by_phone = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            "id",
            "ride_id",
            "ride_status",
            "passenger_phone",
            "driver_phone",
            "pickup_address",
            "dropoff_address",
            "amount",
            "currency",
            "method",
            "status",
            "reference",
            "claimed_at",
            "confirmed_by_phone",
            "confirmed_at",
            "provider",
            "provider_ref",
            "created_at",
        )
        read_only_fields = fields

    def get_driver_phone(self, payment):
        driver = payment.ride.driver
        return driver.phone if driver else None

    def get_confirmed_by_phone(self, payment):
        return payment.confirmed_by.phone if payment.confirmed_by else None
