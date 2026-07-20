"""End-to-end WebSocket tests through the real ASGI app (JWT middleware,
consumer, and the broadcast fan-out triggered by the ride services).

TransactionTestCase (not TestCase) is required here: the consumer and
database_sync_to_async helpers run on other threads/connections, so data
must be really committed — which also lets transaction.on_commit broadcasts
fire exactly as they do in production.
"""
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User, UserRole
from apps.accounts.services import register_passenger
from apps.drivers.services import set_availability
from apps.rides.constants import RideEventType
from apps.rides.services import accept_ride, cancel_ride, create_ride, driver_transition
from apps.rides.tests import PASSWORD, create_fare_setting, make_ready_driver
from config.asgi import application

PICKUP = {"address": "Ikeja City Mall", "lat": "6.601800", "lng": "3.351500"}
DROPOFF = {"address": "Yaba Market", "lat": "6.509500", "lng": "3.371100"}


class RealtimeTests(TransactionTestCase):
    @database_sync_to_async
    def _setup_world(self):
        create_fare_setting()
        admin = User.objects.create_user("+2348031600000", PASSWORD, role=UserRole.ADMIN)
        passenger = register_passenger(phone="+2348031600001", password=PASSWORD)
        driver = make_ready_driver("+2348031600002", "RTA111AA")
        return admin, passenger, driver

    def _communicator(self, user=None):
        token = f"?token={RefreshToken.for_user(user).access_token}" if user else ""
        return WebsocketCommunicator(application, f"/ws/rides/{token}")

    async def _connect(self, user):
        comm = self._communicator(user)
        connected, _ = await comm.connect()
        assert connected, "WebSocket connection refused"
        ready = await comm.receive_json_from()
        assert ready["type"] == "connection.ready"
        return comm, ready

    @database_sync_to_async
    def _create_ride(self, passenger, vehicle_category="CAR"):
        return create_ride(
            passenger=passenger,
            pickup=dict(PICKUP),
            dropoff=dict(DROPOFF),
            vehicle_category=vehicle_category,
        )

    @database_sync_to_async
    def _accept(self, ride, driver):
        return accept_ride(ride_id=ride.pk, driver_user=driver)

    @database_sync_to_async
    def _transition(self, ride, driver, action):
        return driver_transition(ride_id=ride.pk, driver_user=driver, action=action)

    @database_sync_to_async
    def _cancel(self, ride, user):
        return cancel_ride(ride_id=ride.pk, user=user, reason="test")

    @database_sync_to_async
    def _set_online(self, driver, is_online):
        return set_availability(driver.driver_profile, is_online=is_online)

    async def test_unauthenticated_connection_rejected(self):
        comm = self._communicator()
        connected, close_code = await comm.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)

    async def test_full_dispatch_and_ride_event_flow(self):
        admin, passenger, driver = await self._setup_world()

        p_comm, p_ready = await self._connect(passenger)
        d_comm, d_ready = await self._connect(driver)
        self.assertFalse(p_ready["dispatch"])
        self.assertTrue(d_ready["dispatch"])  # online driver auto-subscribed

        # Passenger requests -> driver gets dispatch push, passenger gets echo
        ride = await self._create_ride(passenger)
        dispatch = await d_comm.receive_json_from()
        self.assertEqual(dispatch["type"], "dispatch.new_request")
        self.assertEqual(dispatch["ride"]["id"], ride.pk)
        echo = await p_comm.receive_json_from()
        self.assertEqual((echo["type"], echo["event"]), ("ride.event", RideEventType.REQUESTED))

        # Driver accepts -> passenger notified with driver details;
        # driver gets its ride.event and the dispatch retraction
        await self._accept(ride, driver)
        p_msg = await p_comm.receive_json_from()
        self.assertEqual(p_msg["event"], RideEventType.ACCEPTED)
        self.assertEqual(p_msg["ride"]["driver"]["id"], driver.pk)
        self.assertEqual(p_msg["ride"]["vehicle"]["plate_number"], "RTA111AA")
        d_msgs = {}
        for _ in range(2):
            msg = await d_comm.receive_json_from()
            d_msgs[msg["type"]] = msg
        self.assertIn("ride.event", d_msgs)
        self.assertEqual(d_msgs["dispatch.request_closed"]["ride_id"], ride.pk)

        # Status updates reach the passenger live
        for action, expected in [
            ("arrived", RideEventType.DRIVER_ARRIVED),
            ("start", RideEventType.TRIP_STARTED),
            ("complete", RideEventType.TRIP_COMPLETED),
        ]:
            await self._transition(ride, driver, action)
            msg = await p_comm.receive_json_from()
            self.assertEqual(msg["event"], expected)
            await d_comm.receive_json_from()  # driver's copy

        await p_comm.disconnect()
        await d_comm.disconnect()

    async def test_cancellation_retracts_dispatch(self):
        admin, passenger, driver = await self._setup_world()
        d_comm, _ = await self._connect(driver)

        ride = await self._create_ride(passenger)
        first = await d_comm.receive_json_from()
        self.assertEqual(first["type"], "dispatch.new_request")

        await self._cancel(ride, passenger)
        closed = await d_comm.receive_json_from()
        self.assertEqual(closed["type"], "dispatch.request_closed")
        self.assertEqual(closed["ride_id"], ride.pk)

        await d_comm.disconnect()

    async def test_offline_driver_cannot_subscribe_to_dispatch(self):
        admin, passenger, driver = await self._setup_world()
        await self._set_online(driver, False)

        d_comm, ready = await self._connect(driver)
        self.assertFalse(ready["dispatch"])

        await d_comm.send_json_to({"action": "subscribe_dispatch"})
        resp = await d_comm.receive_json_from()
        self.assertEqual(resp["type"], "error")

        # goes online via REST, then subscribes successfully
        await self._set_online(driver, True)
        await d_comm.send_json_to({"action": "subscribe_dispatch"})
        resp = await d_comm.receive_json_from()
        self.assertEqual(resp["type"], "dispatch.subscribed")

        await d_comm.disconnect()

    async def test_ping_pong(self):
        admin, passenger, driver = await self._setup_world()
        comm, _ = await self._connect(passenger)
        await comm.send_json_to({"action": "ping"})
        resp = await comm.receive_json_from()
        self.assertEqual(resp["type"], "pong")
        await comm.disconnect()

    async def test_dispatch_is_category_scoped(self):
        """A KEKE request must not reach a CAR driver's socket."""
        admin, passenger, driver = await self._setup_world()  # driver is CAR

        @database_sync_to_async
        def keke_world():
            from apps.rides.tests import create_keke_fare_setting

            create_keke_fare_setting()

        await keke_world()

        d_comm, ready = await self._connect(driver)
        self.assertEqual(ready["dispatch_category"], "CAR")

        await self._create_ride(passenger, vehicle_category="KEKE")
        # CAR driver receives nothing for the KEKE request
        self.assertTrue(await d_comm.receive_nothing(timeout=0.5))
        await d_comm.disconnect()

    async def test_driver_location_streams_to_passenger(self):
        """Phase 1 live tracking: a GPS fix sent by the driver over the socket
        reaches the passenger with target, distance and ETA attached."""
        admin, passenger, driver = await self._setup_world()

        p_comm, _ = await self._connect(passenger)
        d_comm, _ = await self._connect(driver)

        ride = await self._create_ride(passenger)
        await d_comm.receive_json_from()  # dispatch.new_request
        await p_comm.receive_json_from()  # ride.event REQUESTED
        await self._accept(ride, driver)
        await p_comm.receive_json_from()  # ride.event ACCEPTED
        for _ in range(2):
            await d_comm.receive_json_from()  # ride.event + dispatch.request_closed

        # Driver streams a position a little north of the pickup
        await d_comm.send_json_to(
            {"action": "location", "lat": "6.610000", "lng": "3.352000", "heading": 180, "speed": 8}
        )

        msg = await p_comm.receive_json_from()
        self.assertEqual(msg["type"], "ride.driver_location")
        self.assertEqual(msg["ride_id"], ride.pk)
        self.assertEqual(msg["location"]["lat"], "6.610000")
        self.assertEqual(msg["location"]["heading"], 180.0)
        # Before pickup the driver is heading to the passenger
        self.assertEqual(msg["target"]["kind"], "pickup")
        self.assertEqual(msg["target"]["address"], PICKUP["address"])
        self.assertGreater(msg["straight_line_m"], 0)
        self.assertGreater(msg["eta"]["duration_s"], 0)
        # The driver receives the same payload so both screens agree
        echo = await d_comm.receive_json_from()
        self.assertEqual(echo["type"], "ride.driver_location")
        self.assertEqual(echo["eta"], msg["eta"])

        await p_comm.disconnect()
        await d_comm.disconnect()

    async def test_location_target_switches_to_dropoff_after_pickup(self):
        admin, passenger, driver = await self._setup_world()
        p_comm, _ = await self._connect(passenger)
        d_comm, _ = await self._connect(driver)

        ride = await self._create_ride(passenger)
        await d_comm.receive_json_from()
        await p_comm.receive_json_from()
        await self._accept(ride, driver)
        await p_comm.receive_json_from()
        for _ in range(2):
            await d_comm.receive_json_from()

        for action in ("arrived", "start"):
            await self._transition(ride, driver, action)
            await p_comm.receive_json_from()
            await d_comm.receive_json_from()

        await d_comm.send_json_to({"action": "location", "lat": "6.560000", "lng": "3.360000"})
        msg = await p_comm.receive_json_from()
        self.assertEqual(msg["type"], "ride.driver_location")
        self.assertEqual(msg["status"], "IN_PROGRESS")
        self.assertEqual(msg["target"]["kind"], "dropoff")
        self.assertEqual(msg["target"]["address"], DROPOFF["address"])

        await p_comm.disconnect()
        await d_comm.disconnect()

    async def test_invalid_coordinates_rejected(self):
        admin, passenger, driver = await self._setup_world()
        d_comm, _ = await self._connect(driver)
        await d_comm.send_json_to({"action": "location", "lat": "999", "lng": "3.35"})
        msg = await d_comm.receive_json_from()
        self.assertEqual(msg["type"], "error")
        await d_comm.disconnect()

    async def test_location_without_active_ride_reports_idle(self):
        admin, passenger, driver = await self._setup_world()
        d_comm, _ = await self._connect(driver)
        await d_comm.send_json_to({"action": "location", "lat": "6.60", "lng": "3.35"})
        msg = await d_comm.receive_json_from()
        self.assertEqual(msg["type"], "location.idle")
        await d_comm.disconnect()
