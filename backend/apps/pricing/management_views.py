"""Admin-only fare configuration (mounted under /api/v1/management/)."""
from rest_framework import generics

from apps.accounts.permissions import IsAdminRole

from . import services
from .models import FareSetting
from .serializers import FareSettingSerializer


class FareSettingListCreateView(generics.ListCreateAPIView):
    """GET: fare-setting history, newest first (the active row included).
    POST: create AND activate a new fare setting in one step."""

    serializer_class = FareSettingSerializer
    permission_classes = [IsAdminRole]
    queryset = FareSetting.objects.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.instance = services.activate_new_fare_setting(
            created_by=self.request.user, **serializer.validated_data
        )
