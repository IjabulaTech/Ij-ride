"""Shared road-distance routing for geo providers.

Place search (Google/OSM/Mapbox) and routing are independent concerns. This
helper gives every provider the same fare-distance logic: real road routing via
Mapbox Directions when a token is configured, else a straight-line estimate so
fares still work with no external routing dependency. Runs entirely in the
background off the coordinates a suggestion carries.
"""
from django.conf import settings

from .base import GeoServiceError, RouteResult
from .utils import haversine_m

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
