"""Fan-out of ride lifecycle events to WebSocket groups.

Called by the ride/payment services on every transition. Sends are deferred
with transaction.on_commit so sockets never see uncommitted state, and any
broadcast failure is logged, never raised — realtime must not break the API.
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

logger = logging.getLogger(__name__)

def dispatch_group(vehicle_category: str) -> str:
    """Per-category dispatch: KEKE requests only reach KEKE drivers."""
    return f"dispatch_{vehicle_category}"


def user_group(user_id: int) -> str:
    return f"user_{user_id}"


def broadcast_ride_event(ride, event_type: str) -> None:
    ride_id = ride.pk
    transaction.on_commit(lambda: _send_ride_event(ride_id, event_type))


def _send_ride_event(ride_id: int, event_type: str) -> None:
    # Imports stay local: rides.services imports this module at load time,
    # and rides.serializers imports rides.services — top-level imports here
    # would create a cycle.
    from apps.rides.constants import RideEventType
    from apps.rides.models import Ride
    from apps.rides.serializers import OpenRideSerializer, RideDetailSerializer

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    try:
        ride = Ride.objects.select_related(
            "passenger", "driver", "driver__driver_profile", "vehicle", "payment"
        ).get(
            pk=ride_id
        )
    except Ride.DoesNotExist:
        return

    try:
        message = {
            "type": "ride.event",
            "event": event_type,
            "ride": RideDetailSerializer(ride).data,
        }
        groups = {user_group(ride.passenger_id)}
        if ride.driver_id:
            groups.add(user_group(ride.driver_id))
        for group in groups:
            async_to_sync(channel_layer.group_send)(group, message)

        # Keep driver dispatch feeds current (per vehicle category)
        category_group = dispatch_group(ride.requested_vehicle_category)
        if event_type == RideEventType.REQUESTED:
            async_to_sync(channel_layer.group_send)(
                category_group,
                {"type": "dispatch.new_request", "ride": OpenRideSerializer(ride).data},
            )
        elif event_type in (
            RideEventType.ACCEPTED,
            RideEventType.CANCELLED,
            RideEventType.EXPIRED,
        ):
            async_to_sync(channel_layer.group_send)(
                category_group,
                {"type": "dispatch.request_closed", "ride_id": ride.pk},
            )
    except Exception:
        logger.exception("Failed to broadcast ride event %s for ride %s", event_type, ride_id)
