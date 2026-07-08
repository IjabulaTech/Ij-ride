from decimal import Decimal

from rest_framework import serializers


class SuggestQuerySerializer(serializers.Serializer):
    q = serializers.CharField(max_length=128)
    limit = serializers.IntegerField(required=False, default=5, min_value=1, max_value=10)
    # Optional live-GPS bias — when the rider has already granted location,
    # bias results toward where they are (falls back to configured centre).
    lat = serializers.DecimalField(
        max_digits=9, decimal_places=6,
        min_value=Decimal("-90"), max_value=Decimal("90"),
        required=False, allow_null=True,
    )
    lng = serializers.DecimalField(
        max_digits=9, decimal_places=6,
        min_value=Decimal("-180"), max_value=Decimal("180"),
        required=False, allow_null=True,
    )

    def validate(self, attrs):
        # lat + lng only meaningful together
        if (attrs.get("lat") is None) != (attrs.get("lng") is None):
            raise serializers.ValidationError(
                "Provide both lat and lng, or neither, for proximity bias."
            )
        return attrs


class ReverseGeocodeQuerySerializer(serializers.Serializer):
    lat = serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=Decimal("-90"), max_value=Decimal("90")
    )
    lng = serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=Decimal("-180"), max_value=Decimal("180")
    )
