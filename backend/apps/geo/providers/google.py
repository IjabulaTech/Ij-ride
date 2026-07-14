"""Google Maps place search: Places API (New) Text Search + Geocoding reverse.

Why Google: it has by far the richest POI coverage in Nigeria — hotels,
pharmacies, markets, studios, offices — that OSM and Mapbox simply don't have
mapped for Adamawa. Text Search returns full places (name, address, and
coordinates) in one call, which fits our suggestion model directly.

All queries are restricted to an Adamawa State rectangle so results stay
in-state. The local Yola POI dictionary still wins the top slots, and
routing/fare math runs in the background via road_route().

Requires GOOGLE_MAPS_API_KEY with "Places API (New)" and "Geocoding API"
enabled. The key lives server-side only (never shipped to the browser).
"""
from decimal import ROUND_HALF_UP, Decimal

import requests
from django.conf import settings

from ..base import (
    AddressNotFoundError,
    GeocodeResult,
    GeoProvider,
    GeoServiceError,
    Suggestion,
)
from ..routing import road_route
from ..yola_poi import match as poi_match

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
TIMEOUT_S = 10
_SIX_DP = Decimal("0.000001")
# Adamawa State rectangle (lat/lng) to keep results in-state.
ADAMAWA_LOW = {"latitude": 7.4, "longitude": 11.3}
ADAMAWA_HIGH = {"latitude": 11.4, "longitude": 13.7}
# Only the fields we use — keeps the request on Google's cheaper billing SKU.
FIELD_MASK = (
    "places.displayName,places.formattedAddress,places.location,"
    "places.primaryType,places.types"
)


def _decimal(value) -> Decimal:
    return Decimal(str(value)).quantize(_SIX_DP, rounding=ROUND_HALF_UP)


class GoogleGeoProvider(GeoProvider):
    def __init__(self):
        # Missing key isn't fatal here — calls degrade gracefully (suggest -> []),
        # so a mis-timed provider switch never 500s the app.
        self.key = settings.GOOGLE_MAPS_API_KEY
        self.session = requests.Session()

    def _text_search(self, query: str, limit: int) -> list[dict]:
        if not self.key:
            raise GeoServiceError("GOOGLE_MAPS_API_KEY is not configured.")
        body = {
            "textQuery": query,
            "languageCode": "en",
            "regionCode": "NG",
            "maxResultCount": max(1, min(20, limit)),
            "locationRestriction": {
                "rectangle": {"low": ADAMAWA_LOW, "high": ADAMAWA_HIGH}
            },
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.key,
            "X-Goog-FieldMask": FIELD_MASK,
        }
        try:
            resp = self.session.post(TEXT_SEARCH_URL, json=body, headers=headers, timeout=TIMEOUT_S)
        except requests.RequestException as exc:
            raise GeoServiceError() from exc
        if resp.status_code != 200:
            raise GeoServiceError()
        return resp.json().get("places") or []

    def _place_to_suggestion(self, place: dict) -> Suggestion | None:
        loc = place.get("location") or {}
        lat, lng = loc.get("latitude"), loc.get("longitude")
        if lat is None or lng is None:
            return None
        label = (place.get("displayName") or {}).get("text") or place.get("formattedAddress") or ""
        if not label:
            return None
        address = place.get("formattedAddress") or label
        place_type = place.get("primaryType") or (place.get("types") or [""])[0]
        return Suggestion(
            label=label,
            address=address,
            lat=_decimal(lat),
            lng=_decimal(lng),
            place_type=place_type,
            place_name=address,
        )

    def suggest(
        self,
        query: str,
        limit: int = 5,
        proximity: tuple[Decimal, Decimal] | None = None,
    ) -> list[Suggestion]:
        if not query.strip():
            return []

        # 1) Local Yola dictionary wins the top slots
        seen: set[str] = set()
        results: list[Suggestion] = []
        for poi in poi_match(query, limit=min(3, limit)):
            if poi.label.lower() in seen:
                continue
            seen.add(poi.label.lower())
            results.append(
                Suggestion(poi.label, poi.address, poi.lat, poi.lng, poi.place_type, poi.address)
            )

        remaining = max(0, limit - len(results))
        if not remaining:
            return results

        try:
            places = self._text_search(query, remaining + 3)
        except GeoServiceError:
            return results
        for place in places:
            s = self._place_to_suggestion(place)
            if not s:
                continue
            if s.label.lower() in seen or s.address.lower() in {
                r.address.lower() for r in results
            }:
                continue
            seen.add(s.label.lower())
            results.append(s)
            if len(results) >= limit:
                break
        return results

    def geocode(self, query: str) -> GeocodeResult:
        for place in self._text_search(query, 1):
            s = self._place_to_suggestion(place)
            if s:
                return GeocodeResult(address=s.address, lat=s.lat, lng=s.lng)
        raise AddressNotFoundError(query)

    def reverse_geocode(self, lat: Decimal, lng: Decimal) -> GeocodeResult:
        fallback = f"Pinned location ({lat}, {lng})"
        if not self.key:
            return GeocodeResult(address=fallback, lat=lat, lng=lng)
        params = {"latlng": f"{lat},{lng}", "key": self.key, "language": "en", "region": "ng"}
        try:
            resp = self.session.get(GEOCODE_URL, params=params, timeout=TIMEOUT_S)
            if resp.status_code != 200:
                raise GeoServiceError()
            data = resp.json()
        except (requests.RequestException, ValueError):
            return GeocodeResult(address=fallback, lat=lat, lng=lng)
        results = data.get("results") or []
        if results:
            return GeocodeResult(
                address=results[0].get("formatted_address", fallback), lat=lat, lng=lng
            )
        return GeocodeResult(address=fallback, lat=lat, lng=lng)

    def route(self, origin, destination):
        return road_route(origin, destination)
