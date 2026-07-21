"""Shared road-distance routing for geo providers.

Place search (Google/OSM/Mapbox) and routing are independent concerns. This
helper gives every provider the same fare-distance logic: real road routing via
Mapbox Directions when a token is configured, else a straight-line estimate so
fares still work with no external routing dependency. Runs entirely in the
background off the coordinates a suggestion carries.
"""
import logging

import requests
from django.conf import settings

from .base import GeoServiceError, RouteResult
from .utils import haversine_m

logger = logging.getLogger(__name__)

_ROAD_FACTOR = 1.4  # straight-line → road distance multiplier
_FALLBACK_SPEED_MPS = 8.3  # ~30 km/h assumed city speed for the no-router case


def road_route(origin, destination) -> RouteResult:
    if settings.MAPBOX_ACCESS_TOKEN:
        try:
            from .providers.mapbox import MapboxGeoProvider

            return MapboxGeoProvider().route(origin, destination)
        except GeoServiceError:
            pass
    straight = haversine_m(origin[0], origin[1], destination[0], destination[1])
    road = round(straight * _ROAD_FACTOR)
    return RouteResult(distance_m=road, duration_s=round(road / _FALLBACK_SPEED_MPS))


DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox/driving/{coords}"
TIMEOUT_S = 10


def route_geometry(origin, destination) -> dict:
    """Road path between two (lat, lng) points for drawing on the map.

    Returns {"points": [[lat, lng], …], "distance_m": int, "duration_s": int,
    "source": "route"|"straight"}. Uses Mapbox Directions (the token we already
    have) so the line follows real roads without needing Google billing. If the
    provider is unavailable the caller still gets a straight two-point line —
    the map degrades rather than breaking.
    """
    straight_points = [
        [float(origin[0]), float(origin[1])],
        [float(destination[0]), float(destination[1])],
    ]
    if settings.MAPBOX_ACCESS_TOKEN:
        coords = f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"  # lng,lat
        try:
            resp = requests.get(
                DIRECTIONS_URL.format(coords=coords),
                params={
                    "access_token": settings.MAPBOX_ACCESS_TOKEN,
                    "geometries": "geojson",
                    "overview": "simplified",
                },
                timeout=TIMEOUT_S,
            )
            if resp.status_code == 200:
                data = resp.json()
                route = (data.get("routes") or [None])[0]
                if route:
                    # GeoJSON is [lng, lat]; Leaflet wants [lat, lng]
                    points = [[c[1], c[0]] for c in route["geometry"]["coordinates"]]
                    if points:
                        return {
                            "points": points,
                            "distance_m": round(route["distance"]),
                            "duration_s": round(route["duration"]),
                            "source": "route",
                        }
        except (requests.RequestException, ValueError, KeyError, IndexError):
            logger.warning("Route geometry lookup failed; using a straight line", exc_info=True)

    estimate = road_route(origin, destination)
    return {
        "points": straight_points,
        "distance_m": estimate.distance_m,
        "duration_s": estimate.duration_s,
        "source": "straight",
    }
