"""Provider selection. Swap providers via the GEO_PROVIDER env var —
no caller anywhere imports a concrete provider class."""
from functools import lru_cache

from django.conf import settings

from .base import GeoProvider


@lru_cache(maxsize=4)
def _provider_for(name: str) -> GeoProvider:
    if name == "stub":
        from .providers.stub import StubGeoProvider

        return StubGeoProvider()
    if name == "mapbox":
        from .providers.mapbox import MapboxGeoProvider

        return MapboxGeoProvider()
    if name == "osm":
        from .providers.osm import OsmGeoProvider

        return OsmGeoProvider()
    if name == "google":
        from .providers.google import GoogleGeoProvider

        return GoogleGeoProvider()
    raise ValueError(
        f"Unknown GEO_PROVIDER '{name}'. Expected 'stub', 'mapbox', 'osm', or 'google'."
    )


def get_geo_provider() -> GeoProvider:
    return _provider_for(settings.GEO_PROVIDER.lower())
