import logging
from decimal import Decimal, InvalidOperation

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .events import dispatch_group, support_admin_group, user_group

logger = logging.getLogger(__name__)

CLOSE_UNAUTHORIZED = 4401


def _clean_number(value):
    """Optional numeric telemetry (heading/speed/accuracy) -> float or None."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None  # drop NaN


def _clean_coords(lat, lng):
    """Validate a GPS fix, returning (lat, lng) as Decimals or None."""
    try:
        lat_d, lng_d = Decimal(str(lat)), Decimal(str(lng))
    except (TypeError, ValueError, InvalidOperation):
        return None
    if not (-90 <= lat_d <= 90) or not (-180 <= lng_d <= 180):
        return None
    # Six decimal places matches the model columns (~0.1 m precision)
    return lat_d.quantize(Decimal("0.000001")), lng_d.quantize(Decimal("0.000001"))


class RideConsumer(AsyncJsonWebsocketConsumer):
    """One socket per signed-in user.

    Everyone joins their personal group (ride events about them). Approved
    online drivers also join the dispatch group — automatically on connect
    when already online (reconnects), or via {"action": "subscribe_dispatch"}
    after toggling online through the REST API.

    Client -> server: {"action": "ping" | "subscribe_dispatch" | "unsubscribe_dispatch"}
    Server -> client: {"type": "connection.ready" | "pong" | "ride.event"
                       | "dispatch.new_request" | "dispatch.request_closed"
                       | "dispatch.subscribed" | "dispatch.unsubscribed" | "error", ...}
    """

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=CLOSE_UNAUTHORIZED)
            return
        self.user_id = user.id
        self.user_group_name = user_group(user.id)
        self.dispatch_group_name: str | None = None
        # Admins also watch the shared support inbox
        self.support_group_name = support_admin_group() if user.is_admin_role else None

        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        if self.support_group_name:
            await self.channel_layer.group_add(self.support_group_name, self.channel_name)
        await self.accept()

        category = await self._dispatch_category()
        if category:
            await self._join_dispatch(category)
        await self.send_json(
            {
                "type": "connection.ready",
                "dispatch": self.dispatch_group_name is not None,
                "dispatch_category": category,
            }
        )

    async def disconnect(self, code):
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
        if getattr(self, "dispatch_group_name", None):
            await self.channel_layer.group_discard(self.dispatch_group_name, self.channel_name)
        if getattr(self, "support_group_name", None):
            await self.channel_layer.group_discard(self.support_group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        action = content.get("action")
        if action == "ping":
            await self.send_json({"type": "pong"})
        elif action == "subscribe_dispatch":
            category = await self._dispatch_category()
            if category:
                await self._join_dispatch(category)
                await self.send_json({"type": "dispatch.subscribed", "dispatch_category": category})
            else:
                await self.send_json(
                    {
                        "type": "error",
                        "detail": "Only approved, online drivers with a vehicle receive dispatch.",
                    }
                )
        elif action == "unsubscribe_dispatch":
            if self.dispatch_group_name:
                await self.channel_layer.group_discard(self.dispatch_group_name, self.channel_name)
            self.dispatch_group_name = None
            await self.send_json({"type": "dispatch.unsubscribed"})
        elif action == "location":
            await self._handle_location(content)

    async def _handle_location(self, content):
        """Driver streaming a GPS fix during an active trip. Streaming over the
        socket (rather than an HTTP POST per fix) keeps mobile data and battery
        use low. Silently ignored for non-drivers / drivers with no active ride."""
        coords = _clean_coords(content.get("lat"), content.get("lng"))
        if coords is None:
            await self.send_json({"type": "error", "detail": "Invalid coordinates."})
            return
        lat, lng = coords
        payload = await self._record_location(
            lat,
            lng,
            _clean_number(content.get("heading")),
            _clean_number(content.get("speed")),
            _clean_number(content.get("accuracy")),
        )
        if payload is None:
            # Stored for dispatch, but nothing to track — tell the client so it
            # can back off its GPS polling.
            await self.send_json({"type": "location.idle"})

    @database_sync_to_async
    def _record_location(self, lat, lng, heading, speed, accuracy):
        from apps.rides.tracking import record_driver_location

        user = self.scope["user"]
        if not user.is_driver:
            return None
        try:
            return record_driver_location(
                user, lat=lat, lng=lng, heading=heading, speed=speed, accuracy=accuracy
            )
        except Exception:
            logger.exception("Failed to record driver location for user %s", self.user_id)
            return None

    async def _join_dispatch(self, category: str):
        # Vehicle category may have changed since the last join — move groups
        group = dispatch_group(category)
        if self.dispatch_group_name and self.dispatch_group_name != group:
            await self.channel_layer.group_discard(self.dispatch_group_name, self.channel_name)
        await self.channel_layer.group_add(group, self.channel_name)
        self.dispatch_group_name = group

    @database_sync_to_async
    def _dispatch_category(self) -> str | None:
        """The vehicle category this driver may serve, or None if not
        eligible (unapproved / offline / no active vehicle)."""
        from apps.drivers.models import DriverApprovalStatus, DriverProfile, Vehicle

        eligible = DriverProfile.objects.filter(
            user_id=self.user_id,
            approval_status=DriverApprovalStatus.APPROVED,
            availability__is_online=True,
        ).first()
        if eligible is None:
            return None
        vehicle = Vehicle.objects.filter(driver=eligible, is_active=True).first()
        return vehicle.category if vehicle else None

    # ------ handlers for channel-layer messages (type "a.b" -> method a_b) ------

    async def ride_event(self, message):
        await self.send_json(
            {"type": "ride.event", "event": message["event"], "ride": message["ride"]}
        )

    async def dispatch_new_request(self, message):
        await self.send_json({"type": "dispatch.new_request", "ride": message["ride"]})

    async def dispatch_request_closed(self, message):
        await self.send_json(
            {"type": "dispatch.request_closed", "ride_id": message["ride_id"]}
        )

    async def ride_driver_location(self, message):
        await self.send_json(
            {
                "type": "ride.driver_location",
                "ride_id": message["ride_id"],
                "status": message["status"],
                "location": message["location"],
                "target": message["target"],
                "straight_line_m": message["straight_line_m"],
                "eta": message["eta"],
            }
        )

    async def support_message(self, message):
        await self.send_json(
            {
                "type": "support.message",
                "message": message["message"],
                "thread_id": message["thread_id"],
                "user_id": message["user_id"],
            }
        )
