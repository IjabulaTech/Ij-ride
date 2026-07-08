from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .forms import AdminUserChangeForm, AdminUserCreationForm
from .models import PassengerProfile, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = AdminUserCreationForm
    form = AdminUserChangeForm
    model = User

    list_display = ("phone", "first_name", "last_name", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("phone", "email", "first_name", "last_name")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        ("Role", {"fields": ("role",)}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("phone", "role", "password1", "password2")}),
    )


@admin.register(PassengerProfile)
class PassengerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "default_payment_method", "created_at")
    search_fields = ("user__phone", "user__first_name", "user__last_name")
    readonly_fields = ("created_at", "updated_at")
