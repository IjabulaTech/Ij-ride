from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.drivers.models import VehicleCategory
from apps.payments.constants import PaymentMethod

from . import services
from .models import PassengerProfile, User
from .utils import normalize_phone


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "phone", "first_name", "last_name", "email", "role", "date_joined")
        read_only_fields = fields


class PassengerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PassengerProfile
        fields = ("default_payment_method",)


class DriverProfileSummarySerializer(serializers.Serializer):
    """Light driver info for /auth/me/. Full onboarding API lives in Module 4."""

    driver_category = serializers.CharField(read_only=True)
    license_number = serializers.CharField(read_only=True)
    approval_status = serializers.CharField(read_only=True)
    approval_note = serializers.CharField(read_only=True)


class MeSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    # Writable for passengers only; ignored for other roles
    default_payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices, write_only=True, required=False
    )

    class Meta:
        model = User
        fields = (
            "id",
            "phone",
            "first_name",
            "last_name",
            "email",
            "role",
            "date_joined",
            "profile",
            "default_payment_method",
        )
        read_only_fields = ("id", "phone", "role", "date_joined")

    def get_profile(self, user):
        if user.is_passenger and hasattr(user, "passenger_profile"):
            return PassengerProfileSerializer(user.passenger_profile).data
        if user.is_driver and hasattr(user, "driver_profile"):
            return DriverProfileSummarySerializer(user.driver_profile).data
        return None

    def validate_email(self, value):
        if value and User.objects.exclude(pk=self.instance.pk).filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def update(self, user, validated_data):
        method = validated_data.pop("default_payment_method", None)
        user = super().update(user, validated_data)
        if method and user.is_passenger and hasattr(user, "passenger_profile"):
            user.passenger_profile.default_payment_method = method
            user.passenger_profile.save(update_fields=["default_payment_method", "updated_at"])
        return user


class BaseRegisterSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")

    def validate_phone(self, value):
        try:
            value = normalize_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0])
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value


class RegisterPassengerSerializer(BaseRegisterSerializer):
    def create(self, validated_data):
        return services.register_passenger(**validated_data)


class RegisterDriverSerializer(BaseRegisterSerializer):
    """Driver signup captures the operating category — KEKE or CAR. V1 rule:
    the driver's active vehicle must match this category."""

    driver_category = serializers.ChoiceField(choices=VehicleCategory.choices)

    def create(self, validated_data):
        return services.register_driver(**validated_data)


class PasswordResetRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)

    def validate_phone(self, value):
        # Normalize so "0803…" and "+234…" resolve to the same account. Never
        # reveal whether the phone exists — that check lives in the service.
        try:
            return normalize_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0])


class PasswordResetConfirmSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    code = serializers.CharField(max_length=12)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_phone(self, value):
        try:
            return normalize_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0])

    def validate_new_password(self, value):
        validate_password(value)
        return value


class PhoneTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Accepts local ('0803...') or international phone formats and adds the
    user payload to the login response."""

    def validate(self, attrs):
        try:
            attrs[self.username_field] = normalize_phone(attrs[self.username_field])
        except DjangoValidationError:
            pass  # let authentication fail with the generic credentials error
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
