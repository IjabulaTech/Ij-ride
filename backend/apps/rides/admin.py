from django.contrib import admin

from .models import Ride, RideEvent


class RideEventInline(admin.TabularInline):
    model = RideEvent
    extra = 0
    readonly_fields = ("event_type", "actor", "metadata", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "passenger",
        "driver",
        "pickup_address",
        "dropoff_address",
        "estimated_fare",
        "final_fare",
        "payment_method",
        "created_at",
    )
    list_filter = ("status", "requested_vehicle_category", "payment_method")
    search_fields = ("passenger__phone", "driver__phone", "pickup_address", "dropoff_address")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    inlines = [RideEventInline]


@admin.register(RideEvent)
class RideEventAdmin(admin.ModelAdmin):
    list_display = ("ride", "event_type", "actor", "created_at")
    list_filter = ("event_type",)
    search_fields = ("ride__id",)
    readonly_fields = ("ride", "event_type", "actor", "metadata", "created_at")
