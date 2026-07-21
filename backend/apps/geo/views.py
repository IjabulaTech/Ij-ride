from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .base import GeoServiceError
from .serializers import ReverseGeocodeQuerySerializer, SuggestQuerySerializer
from .service import get_geo_provider


class SuggestView(APIView):
    """GET /api/v1/geo/suggest/?q=...&lat=&lng=&limit=

    Yola-biased autocomplete. When the caller supplies `lat`/`lng` (their
    live GPS), results are biased to those coordinates on top of the
    configured region. Empty or noisy queries return []. Provider failures
    also return [] rather than 5xx so the UI doesn't flash errors mid-typing.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = SuggestQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        proximity = None
        lat, lng = query.validated_data.get("lat"), query.validated_data.get("lng")
        if lat is not None and lng is not None:
            proximity = (lat, lng)
        provider = get_geo_provider()
        try:
            results = provider.suggest(
                query.validated_data["q"],
                limit=query.validated_data["limit"],
                proximity=proximity,
            )
        except GeoServiceError:
            results = []
        return Response(
            {
                "results": [
                    {
                        "label": s.label,
                        "address": s.address,
                        "place_name": s.place_name or s.address,
                        "place_type": s.place_type,
                        "lat": str(s.lat),
                        "lng": str(s.lng),
                    }
                    for s in results
                ]
            }
        )


class ReverseGeocodeView(APIView):
    """GET /api/v1/geo/reverse/?lat=&lng= — turn coordinates into a label
    for the "Current location" pill. Fare math never depends on this: the
    caller keeps using the coordinates it started with."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = ReverseGeocodeQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        provider = get_geo_provider()
        try:
            result = provider.reverse_geocode(
                query.validated_data["lat"], query.validated_data["lng"]
            )
        except GeoServiceError as exc:
            return Response({"detail": str(exc)}, status=exc.status_code)
        return Response({"address": result.address, "lat": str(result.lat), "lng": str(result.lng)})
