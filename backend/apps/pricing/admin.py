from django.contrib import admin

from .models import FareSetting


@admin.register(FareSetting)
class FareSettingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "vehicle_category",
        "is_active",
        "base_fare",
        "per_km",
        "per_minute",
        "minimum_fare",
        "rounding_step",
        "currency",
        "created_by",
        "created_at",
    )
    list_filter = ("vehicle_category", "is_active")
    readonly_fields = ("created_at", "updated_at")
