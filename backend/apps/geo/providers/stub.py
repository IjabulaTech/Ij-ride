"""Development stub — works with zero API keys, clearly not for production.

Geocoding matches against the local Yola POI dictionary first, then falls
back to a deterministic hash-based pseudo-coordinate near the configured
proximity center. This keeps dev end-to-end without needing a Mapbox key.
"""
import hashlib
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

from ..base import GeocodeResult, GeoProvider, RouteResult, Suggestion
from ..utils import haversine_m
from ..yola_poi import YOLA_POIS, match as poi_match

ROAD_FACTOR = 1.4  # straight-line -> road distance
AVG_SPEED_KMH = 30  # Yola average
_SIX_DP = Decimal("0.000001")


class StubGeoProvider(GeoProvider):
    def _center(self) -> tuple[Decimal, Decimal]:
        # proximity is "lng,lat" (Mapbox convention)
        center_lng, center_lat = (Decimal(p) for p in settings.GEO_PROXIMITY.split(","))
        return center_lat, center_lng

    def _pseudo_point(self, query: str) -> tuple[Decimal, Decimal]:
        center_lat, center_lng = self._center()
        digest = hashlib.md5(query.strip().lower().encode()).digest()
        # spread within roughly +-0.09 degrees (~10 km) of the center
        lat_offset = Decimal(int.from_bytes(digest[:4], "big") % 18000 - 9000) / 100_000
        lng_offset = Decimal(int.from_bytes(digest[4:8], "big") % 18000 - 9000) / 100_000
        return (
            (center_lat + lat_offset).quantize(_SIX_DP, rounding=ROUND_HALF_UP),
            (center_lng + lng_offset).quantize(_SIX_DP, rounding=ROUND_HALF_UP),
        )

    def geocode(self, query: str) -> GeocodeResult:
        # Prefer a real POI hit if the query matches one — makes dev feel
        # closer to production behaviour when someone types "Jimeta…"
        hits = poi_match(query, limit=1)
        if hits:
            poi = hits[0]
            return GeocodeResult(address=poi.address, lat=poi.lat, lng=poi.lng)
        lat, lng = self._pseudo_point(query)
        return GeocodeResult(address=query.strip(), lat=lat, lng=lng)

    def route(self, origin, destination) -> RouteResult:
        straight = haversine_m(origin[0], origin[1], destination[0], destination[1])
        distance_m = round(straight * ROAD_FACTOR)
        duration_s = round(distance_m / (AVG_SPEED_KMH * 1000 / 3600))
        return RouteResult(distance_m=distance_m, duration_s=duration_s)

    def suggest(self, query: str, limit: int = 5, proximity=None) -> list[Suggestion]:
        if not query.strip():
            return []
        # Local Yola POIs first, then hash fallback if nothing matched
        hits = [
            Suggestion(
                label=poi.label,
                address=poi.address,
                lat=poi.lat,
                lng=poi.lng,
                place_type=poi.place_type,
                place_name=poi.address,
            )
            for poi in poi_match(query, limit=limit)
        ]
        if not hits:
            lat, lng = self._pseudo_point(query)
            hits.append(
                Suggestion(
                    label=query.strip(),
                    address=f"{query.strip()}, Yola, Adamawa",
                    lat=lat, lng=lng,
                    place_type="address",
                    place_name=f"{query.strip()}, Yola, Adamawa",
                )
            )
        return hits

    def reverse_geocode(self, lat: Decimal, lng: Decimal) -> GeocodeResult:
        nearest = min(YOLA_POIS, key=lambda p: haversine_m(lat, lng, p.lat, p.lng))
        distance_m = haversine_m(lat, lng, nearest.lat, nearest.lng)
        if distance_m <= 800:
            return GeocodeResult(address=f"Near {nearest.address}", lat=lat, lng=lng)
        return GeocodeResult(address=f"Pinned location ({lat}, {lng})", lat=lat, lng=lng)
