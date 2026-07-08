from rest_framework import serializers

from .models import RideCommission


class RideCommissionAdminSerializer(serializers.ModelSerializer):
    driver_phone = serializers.CharField(source="driver.phone", read_only=True)
    driver_name = serializers.SerializerMethodField()
    confirmed_by_phone = serializers.SerializerMethodField()

    class Meta:
        model = RideCommission
        fields = (
            "id",
            "ride_id",
            "driver_id",
            "driver_phone",
            "driver_name",
            "fare_amount",
            "commission_type",
            "commission_value",
            "commission_amount",
            "driver_earning",
            "status",
            "remitted_at",
            "confirmed_by_phone",
            "note",
            "created_at",
        )
        read_only_fields = fields

    def get_driver_name(self, obj):
        return " ".join(p for p in (obj.driver.first_name, obj.driver.last_name) if p)

    def get_confirmed_by_phone(self, obj):
        return obj.confirmed_by.phone if obj.confirmed_by else None


class RemitSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class SettleDriverSerializer(serializers.Serializer):
    driver_id = serializers.IntegerField(min_value=1)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
