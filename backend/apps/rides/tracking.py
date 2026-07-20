"""Live driver-location tracking for an in-progress ride.

The driver's app streams GPS while a trip is active. For each fix we:
  1. persist it on DriverAvailability (also keeps dispatch fresh),
  2. work out what the driver is currently heading for — the pickup before the
     passenger is aboard, the dropoff after,
  3. attach a straight-line distance (free) and a *throttled* road ETA, and
  4. fan the result out to the passenger and the driver over the WebSocket.

The road ETA calls the geo provider, so it is recomputed at most once every
ETA_REFRESH_SECONDS per ride and cached in between — positions still stream at
full rate, only the ETA lags slightly. Straight-line distance is always current.
"""
import logging
from decimal import Decimal

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache

from apps.geo.utils import haversine_m
from apps.realtime.events import user_group

from .constants import RideStatus

logger = logging.getLogger(__name__)

# Statuses where a driver's position is meaningful to the passenger
TRACKED_STATUSES = (
    RideStatus.ACCEPTED,
    RideStatus.DRIVER_ARRIVED,
    RideStatus.IN_PROGRESS,
)
# Before pickup the driver heads to the passenger; after, to the destination
TO_PICKUP_STATUSES = (RideStatus.ACCEPTED, RideStatus.DRIVER_ARRIVED)

ETA_REFRESH_SECONDS = 25
# Rough city speed used if the routing provider is unavailable (~25 km/h)
FALLBACK_SPEED_MPS = 7.0


def active_tracked_ride(driver_user):
    """The ride this driver is currently running, or None."""
    from .models import Ride

    return (
        Ride.objects.select_related("passenger", "driver")
        .filter(driver=driver_user, status__in=TRACKED_STATUSES)
        .first()
    )


def current_target(ride) -> dict:
    """Where the driver is heading right now."""
    if ride.status in TO_PICKUP_STATUSES:
        return {
            "kind": "pickup",
            "lat": str(ride.pickup_lat),
            "lng": str(ride.pickup_lng),
            "address": ride.pickup_address,
        }
    return {
        "kind": "dropoff",
        "lat": str(ride.dropoff_lat),
        "lng": str(ride.dropoff_lng),
        "address": ride.dropoff_address,
    }


def _eta_cache_key(ride_id: int, kind: str) -> str:
    return f"ride:{ride_id}:eta:{kind}"


def road_eta(ride, origin_lat, origin_lng, target: dict) -> dict:
    """Road distance/duration from the driver to the target, throttled.

    Returns {"distance_m": int, "duration_s": int, "source": "route"|"estimate"}.
    Never raises — a routing outage degrades to a straight-line estimate.
    """
    key = _eta_cache_key(ride.pk, target["kind"])
    cached = cache.get(key)
    if cached:
        return cached

    target_lat, target_lng = Decimal(target["lat"]), Decimal(target["lng"])
    try:
        from apps.geo.routing import road_route

        result = road_route(
            (Decimal(str(origin_lat)), Decimal(str(origin_lng))), (target_lat, target_lng)
        )
        eta = {
            "distance_m": result.distance_m,
            "duration_s": result.duration_s,
            "source": "route",
        }
    except Exception:
        logger.warning("ETA routing failed for ride %s; using estimate", ride.pk, exc_info=True)
        straight = haversine_m(origin_lat, origin_lng, target_lat, target_lng)
        distance = round(straight * 1.4)
        eta = {
            "distance_m": distance,
            "duration_s": round(distance / FALLBACK_SPEED_MPS),
            "source": "estimate",
        }
    cache.set(key, eta, ETA_REFRESH_SECONDS)
    return eta


def build_location_payload(ride, *, lat, lng, heading=None, speed=None, accuracy=None) -> dict:
    target = current_target(ride)
    straight_m = haversine_m(lat, lng, Decimal(target["lat"]), Decimal(target["lng"]))
    return {
        "type": "ride.driver_location",
        "ride_id": ride.pk,
        "status": ride.status,
        "location": {
            "lat": str(lat),
            "lng": str(lng),
            "heading": heading,
            "speed": speed,
            "accuracy": accuracy,
        },
        "target": target,
        "straight_line_m": straight_m,
        "eta": road_eta(ride, lat, lng, target),
    }


def broadcast_location(ride, payload: dict) -> None:
    """Send to the passenger and back to the driver (keeps both maps in sync)."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    groups = {user_group(ride.passenger_id)}
    if ride.driver_id:
        groups.add(user_group(ride.driver_id))
    try:
        for group in groups:
            async_to_sync(channel_layer.group_send)(group, payload)
    except Exception:
        logger.exception("Failed to broadcast driver location for ride %s", ride.pk)


def record_driver_location(
    driver_user, *, lat, lng, heading=None, speed=None, accuracy=None
) -> dict | None:
    """Persist a GPS fix and, when a trip is running, broadcast it.

    Returns the broadcast payload, or None when the driver has no active ride
    (the fix is still stored so dispatch stays accurate).
    """
    from apps.drivers.models import DriverProfile
    from apps.drivers.services import update_location

    profile = DriverProfile.objects.filter(user=driver_user).first()
    if profile is None:
        return None
    update_location(profile, lat=lat, lng=lng)

    ride = active_tracked_ride(driver_user)
    if ride is None:
        return None
    payload = build_location_payload(
        ride, lat=lat, lng=lng, heading=heading, speed=speed, accuracy=accuracy
    )
    broadcast_location(ride, payload)
    return payload
