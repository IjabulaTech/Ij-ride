from decimal import Decimal

from django.conf import settings
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from . import services
from .models import DriverAvailability, DriverProfile, Vehicle, VehicleCategory


class DriverProfileSerializer(serializers.ModelSerializer):
    """Driver's own profile view. Only identity fields are writable —
    approval fields change exclusively through the management workflow."""

    class Meta:
        model = DriverProfile
        fields = (
            "driver_category",
            "license_number",
            "approval_status",
            "approval_note",
            "approved_at",
            "created_at",
        )
        # driver_category is chosen once at signup and cannot be changed in V1
        read_only_fields = (
            "driver_category",
            "approval_status",
            "approval_note",
            "approved_at",
            "created_at",
        )

    def update(self, instance, validated_data):
        return services.update_driver_profile(
            instance,
            license_number=validated_data.get("license_number", instance.license_number),
        )


MAX_VEHICLE_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_VEHICLE_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}


class VehicleSerializer(serializers.ModelSerializer):
    # Explicit so a category choice is REQUIRED on create/update
    category = serializers.ChoiceField(choices=VehicleCategory.choices)
    photo = serializers.ImageField(write_only=True, required=False, allow_null=True)
    photo_url = serializers.SerializerMethodField()

    def validate_photo(self, photo):
        if photo is None:
            return photo
        # Size cap — protect the disk / bandwidth from huge phone uploads
        size = getattr(photo, "size", 0)
        if size > MAX_VEHICLE_PHOTO_BYTES:
            raise serializers.ValidationError(
                f"Photo is too large ({size // 1024} KB). Maximum is "
                f"{MAX_VEHICLE_PHOTO_BYTES // (1024 * 1024)} MB."
            )
        # MIME type cap — reject GIF/SVG/PDF etc; Pillow already validates
        # that the file is a real image
        content_type = getattr(photo, "content_type", "") or ""
        if content_type and content_type not in ALLOWED_VEHICLE_PHOTO_TYPES:
            raise serializers.ValidationError(
                "Photo must be a JPEG, PNG, or WebP image."
            )
        return photo

    class Meta:
        model = Vehicle
        fields = (
            "id",
            "category",
            "make",
            "model",
            "year",
            "color",
            "plate_number",
            "photo",
            "photo_url",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "photo_url", "is_active", "created_at", "updated_at")

    def get_photo_url(self, vehicle) -> str | None:
        if not vehicle.photo:
            return None
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(vehicle.photo.url)
        # No request context (e.g. WebSocket payloads): build from settings
        return f"{settings.PUBLIC_BASE_URL.rstrip('/')}{vehicle.photo.url}"

    def update(self, instance, validated_data):
        # PUT without a new photo keeps the existing one
        if "photo" in validated_data and validated_data["photo"] is None:
            validated_data.pop("photo")
        return super().update(instance, validated_data)


class DriverAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverAvailability
        fields = ("is_online", "current_lat", "current_lng", "location_updated_at", "last_seen_at")
        read_only_fields = fields


class AvailabilityUpdateSerializer(serializers.Serializer):
    is_online = serializers.BooleanField()


class LocationUpdateSerializer(serializers.Serializer):
    lat = serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=Decimal("-90"), max_value=Decimal("90")
    )
    lng = serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=Decimal("-180"), max_value=Decimal("180")
    )


class DriverAdminSerializer(serializers.ModelSerializer):
    """Full driver picture for the management API."""

    user = UserSerializer(read_only=True)
    availability = serializers.SerializerMethodField()
    active_vehicle = serializers.SerializerMethodField()

    class Meta:
        model = DriverProfile
        fields = (
            "id",
            "user",
            "driver_category",
            "license_number",
            "approval_status",
            "approval_note",
            "approved_at",
            "approved_by",
            "active_vehicle",
            "availability",
            "created_at",
        )
        read_only_fields = fields

    def get_availability(self, profile):
        availability = getattr(profile, "availability", None)
        return DriverAvailabilitySerializer(availability).data if availability else None

    def get_active_vehicle(self, profile):
        # vehicles are prefetched by the management views
        vehicle = next((v for v in profile.vehicles.all() if v.is_active), None)
        return VehicleSerializer(vehicle).data if vehicle else None


class ApproveDriverSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class RejectDriverSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)
