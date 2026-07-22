"""Blocks the rider/driver API while maintenance mode is on.

Deliberately exempt so you can always switch it back off:
  * /healthz/            — Render's health check must keep passing
  * /admin/              — Django's own admin site
  * /api/v1/auth/        — logging in (an admin must be able to sign in)
  * /api/v1/management/  — the whole admin API, including the off switch
  * /api/v1/ops/         — the public status endpoint the app polls
CORS preflight (OPTIONS) is always allowed so the browser reports the real
503 instead of an opaque CORS error.
"""
from django.http import JsonResponse

from .services import get_state

EXEMPT_PREFIXES = (
    "/healthz",
    "/admin/",
    "/static/",
    "/media/",
    "/api/v1/auth/",
    "/api/v1/management/",
    "/api/v1/ops/",
)


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS" or request.path.startswith(EXEMPT_PREFIXES):
            return self.get_response(request)

        state = get_state()
        if not state["active"]:
            return self.get_response(request)

        return JsonResponse(
            {"detail": state["message"], "maintenance": True},
            status=503,
        )
