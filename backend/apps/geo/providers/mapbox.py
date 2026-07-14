"""Mapbox implementation: Search Box API (forward + reverse) + Directions v5.

Yola-first strategy:
  1. Every autocomplete query first hits the local Yola POI dictionary.
     Real Yola landmarks (AUN, FMC, Jimeta, Bekaji…) that Mapbox indexes
     poorly always win the top slots.
  2. Mapbox's Search Box API fills the tail. Unlike the legacy Geocoding v5
     endpoint, Search Box indexes hotels, shops, restaurants and other POIs —
     which is what riders actually search for. Every call is constrained to
     Nigeria + an Adamawa State bounding box, biased to the rider's GPS (or the
     configured Yola centre).

Routing/fare math is untouched and runs entirely in the background off the
coordinates a suggestion carries (Directions API v5).
"""
from decimal import ROUND_HALF_UP, Decimal

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

SEARCHBOX_FORWARD_URL = "https://api.mapbox.com/search/searchbox/v1/forward"
SEARCHBOX_REVERSE_URL = "https://api.mapbox.com/search/searchbox/v1/reverse"
DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox/driving/{coords}"
TIMEOUT_S = 10
_SIX_DP = Decimal("0.000001")
# Adamawa State bounding box (approx.) as "minLng,minLat,maxLng,maxLat".
ADAMAWA_BBOX = "11.3,7.4,13.7,11.4"
# Search Box feature types that make useful ride-hailing suggestions. "poi"
# is what surfaces hotels, shops, restaurants, offices, etc.
SUGGEST_TYPES = "poi,address,street,neighborhood,locality,place,district"


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
        include_bbox: bool = True,
    ) -> dict:
        """Shared Nigeria + Adamawa + proximity constraints for Search Box."""
        params: dict = dict(extras or {})
        if settings.GEO_COUNTRY:
            params["country"] = settings.GEO_COUNTRY.lower()  # Search Box wants alpha-2
        if proximity is not None:
            # Rider's live GPS beats the static proximity center
            params["proximity"] = f"{proximity[1]},{proximity[0]}"  # lng,lat
        elif settings.GEO_PROXIMITY:
            params["proximity"] = settings.GEO_PROXIMITY
        if include_bbox:
            params["bbox"] = ADAMAWA_BBOX  # keep results inside Adamawa State
        params.setdefault("language", "en")
        return params

    @staticmethod
    def _coords(feature: dict):
        coords = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coords) != 2:
            return None
        return coords[0], coords[1]  # lng, lat

    @staticmethod
    def _address_of(props: dict, fallback: str = "") -> str:
        return props.get("full_address") or props.get("place_formatted") or props.get("name") or fallback

    def geocode(self, query: str) -> GeocodeResult:
        params = self._bias_params({"q": query, "limit": 1})
        data = self._get(SEARCHBOX_FORWARD_URL, params)
        features = data.get("features") or []
        if not features:
            raise AddressNotFoundError(query)
        feature = features[0]
        coords = self._coords(feature)
        if coords is None:
            raise AddressNotFoundError(query)
        lng, lat = coords
        return GeocodeResult(
            address=self._address_of(feature.get("properties") or {}, query),
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
        coords = self._coords(feature)
        if coords is None:
            return None
        lng, lat = coords
        props = feature.get("properties") or {}
        label = props.get("name") or props.get("name_preferred") or ""
        if not label:
            return None
        place_type = props.get("feature_type") or ""
        categories = props.get("poi_category") or []
        if categories:
            place_type = categories[0]  # e.g. "hotel", "restaurant"
        return Suggestion(
            label=label,
            address=self._address_of(props, label),
            lat=_decimal(lat),
            lng=_decimal(lng),
            place_type=place_type,
            place_name=self._address_of(props, label),
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

        # 2) Fill remaining slots with real Mapbox Search Box POIs/addresses
        remaining = max(0, limit - len(results))
        if remaining:
            params = self._bias_params(
                {"q": query, "limit": remaining, "types": SUGGEST_TYPES},
                proximity=proximity,
            )
            try:
                data = self._get(SEARCHBOX_FORWARD_URL, params)
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
        fallback = f"Pinned location ({lat}, {lng})"
        try:
            data = self._get(
                SEARCHBOX_REVERSE_URL,
                {"longitude": str(lng), "latitude": str(lat), "limit": 1, "language": "en"},
            )
        except GeoServiceError:
            return GeocodeResult(address=fallback, lat=lat, lng=lng)
        features = data.get("features") or []
        if not features:
            return GeocodeResult(address=fallback, lat=lat, lng=lng)
        return GeocodeResult(
            address=self._address_of(features[0].get("properties") or {}, fallback),
            lat=lat,
            lng=lng,
        )
