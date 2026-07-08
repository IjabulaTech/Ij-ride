"""Mapbox implementation: Geocoding API v5 + Directions API v5.

Yola-first strategy:
  1. Every autocomplete query first hits the local Yola POI dictionary.
     Real Yola landmarks (AUN, FMC, Jimeta, Bekaji…) that Mapbox indexes
     poorly always win the top slots.
  2. Mapbox fills the tail with `types=poi,address,neighborhood,locality,place`,
     `country=NG`, `bbox=<Adamawa envelope>`, and either a live GPS
     proximity or the configured Yola centre.
"""
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import quote

import requests
from django.conf import settings

from ..base import (
    AddressNotFoundError,
    GeocodeResult,
    GeoProvider,
    GeoServiceError,
    RouteResult,
    Suggestion,
)
from ..yola_poi import match as poi_match

GEOCODE_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json"
DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox/driving/{coords}"
TIMEOUT_S = 10
_SIX_DP = Decimal("0.000001")
# Adamawa State bounding box (approx.) — south,west,north,east in lng,lat pairs.
# Mapbox bbox is "minLng,minLat,maxLng,maxLat".
ADAMAWA_BBOX = "11.3,7.4,13.7,11.4"
# Feature types that produce useful ride-hailing suggestions.
SUGGEST_TYPES = "poi,address,neighborhood,locality,place,region"


def _decimal(value) -> Decimal:
    return Decimal(str(value)).quantize(_SIX_DP, rounding=ROUND_HALF_UP)


class MapboxGeoProvider(GeoProvider):
    def __init__(self):
        if not settings.MAPBOX_ACCESS_TOKEN:
            raise GeoServiceError("MAPBOX_ACCESS_TOKEN is not configured.")
        self.session = requests.Session()

    def _get(self, url: str, params: dict) -> dict:
        try:
            resp = self.session.get(
                url,
                params={"access_token": settings.MAPBOX_ACCESS_TOKEN, **params},
                timeout=TIMEOUT_S,
            )
        except requests.RequestException as exc:
            raise GeoServiceError() from exc
        if resp.status_code != 200:
            raise GeoServiceError()
        return resp.json()

    def _bias_params(
        self,
        extras: dict | None = None,
        *,
        proximity: tuple[Decimal, Decimal] | None = None,
        include_bbox: bool = False,
    ) -> dict:
        params: dict = dict(extras or {})
        if settings.GEO_COUNTRY:
            params["country"] = settings.GEO_COUNTRY
        if proximity is not None:
            # Rider's live GPS beats the static proximity center
            params["proximity"] = f"{proximity[1]},{proximity[0]}"  # lng,lat
        elif settings.GEO_PROXIMITY:
            params["proximity"] = settings.GEO_PROXIMITY
        if include_bbox:
            params["bbox"] = ADAMAWA_BBOX
        params.setdefault("language", "en")
        return params

    def geocode(self, query: str) -> GeocodeResult:
        params = self._bias_params({"limit": 1}, include_bbox=True)
        data = self._get(GEOCODE_URL.format(query=quote(query)), params)
        features = data.get("features") or []
        if not features:
            raise AddressNotFoundError(query)
        feature = features[0]
        lng, lat = feature["center"]
        return GeocodeResult(
            address=feature.get("place_name", query),
            lat=_decimal(lat),
            lng=_decimal(lng),
        )

    def route(self, origin, destination) -> RouteResult:
        coords = f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"  # lng,lat pairs
        data = self._get(DIRECTIONS_URL.format(coords=coords), {"overview": "false"})
        routes = data.get("routes") or []
        if data.get("code") != "Ok" or not routes:
            raise GeoServiceError("Could not calculate a route between those points.")
        return RouteResult(
            distance_m=round(routes[0]["distance"]), duration_s=round(routes[0]["duration"])
        )

    def _feature_to_suggestion(self, feature: dict) -> Suggestion | None:
        center = feature.get("center") or []
        if len(center) != 2:
            return None
        lng, lat = center
        place_type = ""
        types = feature.get("place_type") or []
        if types:
            place_type = types[0]
        # Prefer the specific POI category if Mapbox gave us one
        for prop in (feature.get("properties") or {}).get("category", "").split(",")[:1]:
            if prop.strip():
                place_type = prop.strip()
        return Suggestion(
            label=feature.get("text") or feature.get("place_name", ""),
            address=feature.get("place_name", ""),
            lat=_decimal(lat),
            lng=_decimal(lng),
            place_type=place_type,
            place_name=feature.get("place_name", ""),
        )

    def suggest(
        self,
        query: str,
        limit: int = 5,
        proximity: tuple[Decimal, Decimal] | None = None,
    ) -> list[Suggestion]:
        if not query.strip():
            return []

        # 1) Local Yola dictionary always wins the top slots
        local_hits = poi_match(query, limit=min(3, limit))
        seen_labels: set[str] = set()
        results: list[Suggestion] = []
        for poi in local_hits:
            key = poi.label.lower()
            if key in seen_labels:
                continue
            seen_labels.add(key)
            results.append(
                Suggestion(
                    label=poi.label,
                    address=poi.address,
                    lat=poi.lat,
                    lng=poi.lng,
                    place_type=poi.place_type,
                    place_name=poi.address,
                )
            )

        # 2) Fill remaining slots with real Mapbox results
        remaining = max(0, limit - len(results))
        if remaining:
            params = self._bias_params(
                {
                    "limit": remaining,
                    "autocomplete": "true",
                    "types": SUGGEST_TYPES,
                },
                proximity=proximity,
                include_bbox=True,
            )
            try:
                data = self._get(GEOCODE_URL.format(query=quote(query)), params)
            except GeoServiceError:
                return results
            for feature in data.get("features") or []:
                s = self._feature_to_suggestion(feature)
                if not s:
                    continue
                # Deduplicate against local hits by label AND address
                if s.label.lower() in seen_labels or s.address.lower() in {
                    r.address.lower() for r in results
                }:
                    continue
                seen_labels.add(s.label.lower())
                results.append(s)
                if len(results) >= limit:
                    break
        return results

    def reverse_geocode(self, lat: Decimal, lng: Decimal) -> GeocodeResult:
        query = f"{lng},{lat}"
        try:
            data = self._get(GEOCODE_URL.format(query=quote(query)), {"limit": 1})
        except GeoServiceError:
            return GeocodeResult(address=f"Pinned location ({lat}, {lng})", lat=lat, lng=lng)
        features = data.get("features") or []
        if not features:
            return GeocodeResult(address=f"Pinned location ({lat}, {lng})", lat=lat, lng=lng)
        feature = features[0]
        return GeocodeResult(
            address=feature.get("place_name", f"Pinned location ({lat}, {lng})"),
            lat=lat,
            lng=lng,
        )
