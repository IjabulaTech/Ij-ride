from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "ride",
        "amount",
        "currency",
        "method",
        "status",
        "claimed_at",
        "confirmed_by",
        "confirmed_at",
    )
    list_filter = ("method", "status")
    search_fields = ("ride__id", "ride__passenger__phone", "reference", "provider_ref")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
