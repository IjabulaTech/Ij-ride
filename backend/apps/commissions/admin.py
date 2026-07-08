from django.contrib import admin
from django.utils import timezone

from .models import PlatformCommissionSetting, RemittanceStatus, RideCommission


@admin.register(PlatformCommissionSetting)
class PlatformCommissionSettingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "is_active",
        "commission_type",
        "commission_value",
        "created_by",
        "created_at",
    )
    list_filter = ("is_active", "commission_type")
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if obj.created_by is None:
            obj.created_by = request.user
        # Activating this row deactivates any other active one
        if obj.is_active:
            PlatformCommissionSetting.objects.filter(is_active=True).exclude(
                pk=obj.pk
            ).update(is_active=False, updated_at=timezone.now())
        super().save_model(request, obj, form, change)


@admin.register(RideCommission)
class RideCommissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "ride",
        "driver",
        "fare_amount",
        "commission_amount",
        "driver_earning",
        "status",
        "remitted_at",
        "confirmed_by",
    )
    list_filter = ("status", "commission_type")
    search_fields = ("driver__phone", "driver__first_name", "driver__last_name", "ride__id")
    readonly_fields = (
        "ride",
        "driver",
        "fare_amount",
        "commission_setting",
        "commission_type",
        "commission_value",
        "commission_amount",
        "driver_earning",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"
    actions = ("mark_remitted", "mark_waived")

    @admin.action(description="Mark selected as REMITTED")
    def mark_remitted(self, request, queryset):
        updated = queryset.filter(status=RemittanceStatus.PENDING).update(
            status=RemittanceStatus.REMITTED,
            remitted_at=timezone.now(),
            confirmed_by=request.user,
            updated_at=timezone.now(),
        )
        self.message_user(request, f"{updated} commission(s) marked remitted.")

    @admin.action(description="Mark selected as WAIVED")
    def mark_waived(self, request, queryset):
        updated = queryset.filter(status=RemittanceStatus.PENDING).update(
            status=RemittanceStatus.WAIVED,
            remitted_at=timezone.now(),
            confirmed_by=request.user,
            updated_at=timezone.now(),
        )
        self.message_user(request, f"{updated} commission(s) waived.")
