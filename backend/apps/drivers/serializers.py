import io
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from . import services
from .models import DriverAvailability, DriverProfile, Vehicle, VehicleCategory


MAX_PHOTO_BYTES = 15 * 1024 * 1024  # 15 MB raw upload (re-compressed below)
MAX_IMAGE_DIM = 1600  # cap the long edge — ample for profile/vehicle display


def process_image_upload(photo, *, label="Photo"):
    """Accept ANY picture the server can decode — JPEG, PNG, WebP, GIF, BMP,
    TIFF, and iPhone HEIC/HEIF — and normalize it to a web-safe JPEG that every
    browser renders. Also honours EXIF rotation (phone photos) and caps the
    dimensions. Returns a Django file ready for an ImageField, or None.
    """
    if photo is None:
        return photo
    size = getattr(photo, "size", 0)
    if size > MAX_PHOTO_BYTES:
        raise serializers.ValidationError(
            f"{label} is too large ({size // (1024 * 1024)} MB). Maximum is "
            f"{MAX_PHOTO_BYTES // (1024 * 1024)} MB."
        )
    try:
        img = Image.open(photo)
        img = ImageOps.exif_transpose(img)  # rotate to the orientation shot
        img = img.convert("RGB")
        img.thumbnail((MAX_IMAGE_DIM, MAX_IMAGE_DIM))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
    except Exception:
        raise serializers.ValidationError(f"{label} must be a valid image file.")
    base = (getattr(photo, "name", "") or "photo").rsplit("/", 1)[-1].rsplit(".", 1)[0]
    return ContentFile(buf.getvalue(), name=f"{base or 'photo'}.jpg")


def build_media_url(file_field, request) -> str | None:
    """Absolute URL for a media file — request-relative when we have one,
    else built from PUBLIC_BASE_URL (WebSocket / context-less payloads)."""
    if not file_field:
        return None
    url = file_field.url
    # Remote storages (Cloudinary/S3) already return an absolute URL — never
    # prefix a host onto it (that would break WebSocket-broadcast payloads).
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if request is not None:
        return request.build_absolute_uri(url)
    return f"{settings.PUBLIC_BASE_URL.rstrip('/')}{url}"


class DriverProfileSerializer(serializers.ModelSerializer):
    """Driver's own profile view. Only identity fields are writable —
    approval fields change exclusively through the management workflow."""

    # FileField (not ImageField) so any format is accepted; process_image_upload
    # validates it's a real image and converts it to a web-safe JPEG.
    photo = serializers.FileField(write_only=True, required=False, allow_null=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = DriverProfile
        fields = (
            "driver_category",
            "license_number",
            "photo",
            "photo_url",
            "approval_status",
            "approval_note",
            "approved_at",
            "created_at",
        )
        # driver_category is chosen once at signup and cannot be changed in V1
        read_only_fields = (
            "driver_category",
            "photo_url",
            "approval_status",
            "approval_note",
            "approved_at",
            "created_at",
        )

    def get_photo_url(self, profile) -> str | None:
        return build_media_url(profile.photo, self.context.get("request"))

    def validate_photo(self, photo):
        return process_image_upload(photo, label="Profile photo")

    def update(self, instance, validated_data):
        # License changes may trigger re-approval; that logic stays in the
        # service. A photo upload alone must NOT re-trigger approval.
        instance = services.update_driver_profile(
            instance,
            license_number=validated_data.get("license_number", instance.license_number),
        )
        if "photo" in validated_data and validated_data["photo"] is not None:
            instance.photo = validated_data["photo"]
            instance.save(update_fields=["photo", "updated_at"])
        return instance


# Fields a CAR must provide but a KEKE (tricycle) may leave blank.
CAR_ONLY_FIELDS = ("make", "model", "year", "color")


class VehicleSerializer(serializers.ModelSerializer):
    # Explicit so a category choice is REQUIRED on create/update
    category = serializers.ChoiceField(choices=VehicleCategory.choices)
    # Optional at the field level; required-for-CAR is enforced in validate()
    make = serializers.CharField(required=False, allow_blank=True, default="")
    model = serializers.CharField(required=False, allow_blank=True, default="")
    year = serializers.IntegerField(required=False, allow_null=True, min_value=1980)
    color = serializers.CharField(required=False, allow_blank=True, default="")
    # FileField (not ImageField) so any format is accepted; process_image_upload
    # validates it's a real image and converts it to a web-safe JPEG.
    photo = serializers.FileField(write_only=True, required=False, allow_null=True)
    photo_url = serializers.SerializerMethodField()

    def validate_photo(self, photo):
        return process_image_upload(photo, label="Vehicle photo")

    def validate(self, attrs):
        # A CAR needs full details; a KEKE only needs plate + photo. On update
        # (PATCH) fall back to the instance's current category/values.
        category = attrs.get("category") or getattr(self.instance, "category", None)
        if category == VehicleCategory.CAR:
            missing = {}
            for field in CAR_ONLY_FIELDS:
                value = attrs.get(field, getattr(self.instance, field, None))
                if value in (None, ""):
                    missing[field] = ["This field is required for cars."]
            if missing:
                raise serializers.ValidationError(missing)
        elif category == VehicleCategory.KEKE:
            # Keep keke rows clean — ignore any car-only values sent along
            for field in CAR_ONLY_FIELDS:
                attrs[field] = None if field == "year" else ""
        return attrs

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
        return build_media_url(vehicle.photo, self.context.get("request"))

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
    photo_url = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()
    active_vehicle = serializers.SerializerMethodField()

    class Meta:
        model = DriverProfile
        fields = (
            "id",
            "user",
            "driver_category",
            "license_number",
            "photo_url",
            "approval_status",
            "approval_note",
            "approved_at",
            "approved_by",
            "active_vehicle",
            "availability",
            "created_at",
        )
        read_only_fields = fields

    def get_photo_url(self, profile) -> str | None:
        return build_media_url(profile.photo, self.context.get("request"))

    def get_availability(self, profile):
        availability = getattr(profile, "availability", None)
        return DriverAvailabilitySerializer(availability).data if availability else None

    def get_active_vehicle(self, profile):
        # vehicles are prefetched by the management views
        vehicle = next((v for v in profile.vehicles.all() if v.is_active), None)
        return VehicleSerializer(vehicle, context=self.context).data if vehicle else None


class ApproveDriverSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class RejectDriverSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)
