"""Role-based permission classes used across the whole API."""
from rest_framework.permissions import BasePermission

from apps.drivers.models import DriverProfile


class IsPassenger(BasePermission):
    message = "Only passengers can perform this action."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_passenger)


class IsDriver(BasePermission):
    message = "Only drivers can perform this action."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_driver)


class IsAdminRole(BasePermission):
    message = "Only admins can perform this action."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin_role)


class IsApprovedDriver(IsDriver):
    """Driver whose profile has been approved by an admin. Gate for going
    online and accepting rides (Modules 4 and 6)."""

    message = "Your driver account has not been approved yet."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        try:
            return request.user.driver_profile.is_approved
        except DriverProfile.DoesNotExist:
            return False
