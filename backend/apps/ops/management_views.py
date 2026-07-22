"""Admin on/off switch for maintenance mode (/api/v1/management/maintenance/)."""
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole

from .services import get_state, set_state


class MaintenanceUpdateSerializer(serializers.Serializer):
    active = serializers.BooleanField()
    message = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=500
    )


class MaintenanceAdminView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        state = get_state(refresh=True)
        return Response({"maintenance": state["active"], "message": state["message"]})

    def post(self, request):
        serializer = MaintenanceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        state = set_state(
            active=serializer.validated_data["active"],
            message=serializer.validated_data.get("message", ""),
            admin_user=request.user,
        )
        return Response(
            {"maintenance": state["active"], "message": state["message"]},
            status=status.HTTP_200_OK,
        )
