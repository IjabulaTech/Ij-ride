"""Provider-neutral geo types and interface. Nothing here knows about HTTP
or any specific vendor — implementations live in apps/geo/providers/."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class GeocodeResult:
    address: str
    lat: Decimal
    lng: Decimal


@dataclass(frozen=True)
class Suggestion:
    """One autocomplete result. `label` is short for the picker UI; `address`
    (aka `place_name`) is the fuller string stored on the ride. `place_type`
    is a category hint (poi | hospital | neighborhood | road | …) that the
    frontend can use to pick an icon or filter suggestions."""

    label: str
    address: str
    lat: Decimal
    lng: Decimal
    place_type: str = ""
    place_name: str = ""  # equal to `address` for Mapbox; kept for API symmetry


@dataclass(frozen=True)
class RouteResult:
    distance_m: int
    duration_s: int


class GeoServiceError(Exception):
    """Provider failure (network, quota, bad response). Maps to HTTP 502."""

    status_code = 502

    def __init__(self, message="Location service is temporarily unavailable."):
        super().__init__(message)


class AddressNotFoundError(GeoServiceError):
    """The query produced no result. Maps to HTTP 400 — a user input problem."""

    status_code = 400

    def __init__(self, query: str):
        super(GeoServiceError, self).__init__(
            f"Could not find a location for '{query}'. Try a more specific address."
        )


class GeoProvider(ABC):
    @abstractmethod
    def geocode(self, query: str) -> GeocodeResult:
        """Resolve free-text address to coordinates."""

    @abstractmethod
    def route(
        self, origin: tuple[Decimal, Decimal], destination: tuple[Decimal, Decimal]
    ) -> RouteResult:
        """Driving distance and duration between two (lat, lng) points."""

    @abstractmethod
    def suggest(
        self,
        query: str,
        limit: int = 5,
        proximity: tuple[Decimal, Decimal] | None = None,
    ) -> list[Suggestion]:
        """Autocomplete suggestions biased to the configured region.

        When `proximity` is provided (rider's live GPS), results should be
        biased to those coordinates on top of the region config. Returns an
        empty list (never raises AddressNotFoundError) so a typo mid-typing
        doesn't produce noisy errors.
        """

    @abstractmethod
    def reverse_geocode(self, lat: Decimal, lng: Decimal) -> GeocodeResult:
        """Turn coordinates into a readable address (for 'Current location'
        labels). Never blocks fare calculation — a failure returns a
        coordinate-string address instead."""
