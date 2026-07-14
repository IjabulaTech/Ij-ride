"""OpenStreetMap place search via Photon (photon.komoot.io by default).

Why OSM: Mapbox's Geocoding/Search Box coverage for Adamawa State is nearly
empty — landmarks like AUN, hotels, and Jimeta all return nothing. OSM is
community-mapped and has real Adamawa POIs (hotels, universities, markets…),
and Photon is a free, keyless autocomplete service over that data.

Design:
  1. Local Yola POI dictionary still wins the top slots (guaranteed landmarks).
  2. Photon fills the rest, biased to Yola and constrained to an Adamawa
     bounding box; results are then post-filtered to Nigeria + Adamawa so the
     Cameroon border towns the bbox clips don't leak in.
  3. Routing (distance/duration for the fare) stays on Mapbox Directions when a
     token is configured, else falls back to a straight-line road estimate —
     all in the background, off the coordinates a suggestion carries.

The Photon base URL is configurable via GEO_OSM_BASE_URL so a self-hosted or
commercial (LocationIQ-style) instance can be swapped in for scale.
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

TIMEOUT_S = 10
_SIX_DP = Decimal("0.000001")
# Adamawa State bounding box (approx.) as minLng,minLat,maxLng,maxLat.
ADAMAWA_BBOX = (11.3, 7.4, 13.7, 11.4)


def _decimal(value) -> Decimal:
    return Decimal(str(value)).quantize(_SIX_DP, rounding=ROUND_HALF_UP)


class OsmGeoProvider(GeoProvider):
    def __init__(self):
        self.base = settings.GEO_OSM_BASE_URL.rstrip("/")
        self.session = requests.Session()
        # Photon's public instance asks callers to identify themselves.
        self.session.headers["User-Agent"] = "IJRide/1.0 (+https://ijrides.com)"

    # ---- HTTP ----
    def _get(self, path: str, params: dict) -> dict:
        try:
            resp = self.session.get(f"{self.base}{path}", params=params, timeout=TIMEOUT_S)
        except requests.RequestException as exc:
            raise GeoServiceError() from exc
        if resp.status_code != 200:
            raise GeoServiceError()
        return resp.json()

    @staticmethod
    def _bbox_param() -> str:
        return ",".join(str(v) for v in ADAMAWA_BBOX)

    # ---- parsing / filtering ----
    @staticmethod
    def _in_adamawa(props: dict) -> bool:
        """Keep Nigeria + Adamawa only. The bbox clips into Cameroon near the
        border, so drop anything whose country/state says otherwise. Missing
        state is tolerated (many POIs omit it) as long as the country is NG."""
        country = (props.get("countrycode") or "").upper()
        if country and country != "NG":
            return False
        state = (props.get("state") or "").lower()
        if state and "adamawa" not in state:
            return False
        return True

    def _feature_to_suggestion(self, feature: dict) -> Suggestion | None:
        coords = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coords) != 2:
            return None
        props = feature.get("properties") or {}
        if not self._in_adamawa(props):
            return None
        lng, lat = coords
        name = props.get("name") or props.get("street") or props.get("city") or ""
        if not name:
            return None
        # Build a readable address from the OSM address parts, skipping repeats.
        parts = [name]
        for key in ("street", "district", "city", "county", "state"):
            value = props.get(key)
            if value and value not in parts:
                parts.append(value)
        if "Nigeria" not in parts:
            parts.append("Nigeria")
        address = ", ".join(parts)
        place_type = props.get("osm_value") or props.get("type") or ""
        return Suggestion(
            label=name,
            address=address,
            lat=_decimal(lat),
            lng=_decimal(lng),
            place_type=place_type,
            place_name=address,
        )

    # ---- GeoProvider interface ----
    def suggest(
        self,
        query: str,
        limit: int = 5,
        proximity: tuple[Decimal, Decimal] | None = None,
    ) -> list[Suggestion]:
        if not query.strip():
            return []

        # 1) Local Yola dictionary wins the top slots
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

        remaining = max(0, limit - len(results))
        if not remaining:
            return results

        lat, lng = (proximity or (Decimal(settings.GEO_PROXIMITY.split(",")[1]),
                                  Decimal(settings.GEO_PROXIMITY.split(",")[0])))
        params = {
            "q": query,
            # Over-fetch: some results get dropped by the Adamawa filter.
            "limit": min(15, remaining * 2 + 3),
            "lang": "en",
            "lat": str(lat),
            "lon": str(lng),
            "bbox": self._bbox_param(),
        }
        try:
            data = self._get("/api/", params)
        except GeoServiceError:
            return results
        for feature in data.get("features") or []:
            s = self._feature_to_suggestion(feature)
            if not s:
                continue
            if s.label.lower() in seen_labels or s.address.lower() in {
                r.address.lower() for r in results
            }:
                continue
            seen_labels.add(s.label.lower())
            results.append(s)
            if len(results) >= limit:
                break
        return results

    def geocode(self, query: str) -> GeocodeResult:
        lng_c, lat_c = settings.GEO_PROXIMITY.split(",")
        params = {
            "q": query,
            "limit": 5,
            "lang": "en",
            "lat": lat_c,
            "lon": lng_c,
            "bbox": self._bbox_param(),
        }
        data = self._get("/api/", params)
        for feature in data.get("features") or []:
            s = self._feature_to_suggestion(feature)
            if s:
                return GeocodeResult(address=s.address, lat=s.lat, lng=s.lng)
        raise AddressNotFoundError(query)

    def reverse_geocode(self, lat: Decimal, lng: Decimal) -> GeocodeResult:
        fallback = f"Pinned location ({lat}, {lng})"
        try:
            data = self._get("/reverse/", {"lat": str(lat), "lon": str(lng), "lang": "en"})
        except GeoServiceError:
            return GeocodeResult(address=fallback, lat=lat, lng=lng)
        for feature in data.get("features") or []:
            props = feature.get("properties") or {}
            name = props.get("name") or props.get("street") or props.get("city")
            if not name:
                continue
            parts = [name]
            for key in ("street", "district", "city", "county", "state"):
                value = props.get(key)
                if value and value not in parts:
                    parts.append(value)
            return GeocodeResult(address=", ".join(parts), lat=lat, lng=lng)
        return GeocodeResult(address=fallback, lat=lat, lng=lng)

    def route(self, origin, destination):
        return road_route(origin, destination)
