from django.http import JsonResponse


def health(request):
    """Liveness probe for the hosting platform."""
    return JsonResponse({"status": "ok", "service": "ij-ride-api"})
