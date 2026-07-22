"""Public maintenance status — the app polls this to decide whether to show
the maintenance screen. Unauthenticated and never blocked by the middleware."""
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import get_state


class MaintenanceStatusView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        state = get_state()
        return Response({"maintenance": state["active"], "message": state["message"]})
