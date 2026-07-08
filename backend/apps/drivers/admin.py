from django.contrib import admin

from .models import DriverAvailability, DriverProfile, Vehicle


class VehicleInline(admin.TabularInline):
    model = Vehicle
    extra = 0


class DriverAvailabilityInline(admin.StackedInline):
    model = DriverAvailability
    extra = 0
    readonly_fields = ("updated_at",)


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "driver_category",
        "license_number",
        "approval_status",
        "approved_at",
        "created_at",
    )
    list_filter = ("driver_category", "approval_status")
    search_fields = ("user__phone", "user__first_name", "user__last_name", "license_number")
    readonly_fields = ("created_at", "updated_at")
    inlines = [DriverAvailabilityInline, VehicleInline]


@admin.register(DriverAvailability)
class DriverAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("driver", "is_online", "location_updated_at", "last_seen_at")
    list_filter = ("is_online",)
    search_fields = ("driver__user__phone",)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        "plate_number",
        "category",
        "driver",
        "make",
        "model",
        "year",
        "color",
        "has_photo",
        "is_active",
    )
    list_filter = ("category", "is_active", "make")
    search_fields = ("plate_number", "driver__user__phone", "make", "model")

    @admin.display(boolean=True, description="Photo")
    def has_photo(self, vehicle):
        return bool(vehicle.photo)
