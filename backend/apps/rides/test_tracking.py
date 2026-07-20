"""Live-tracking pipeline tests (Phase 1)."""
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase

from apps.accounts.services import register_driver, register_passenger
from apps.drivers.models import DriverApprovalStatus, DriverProfile, Vehicle
from apps.pricing.models import FareSetting

from .constants import RideStatus
from .models import Ride
from .tracking import (
    build_location_payload,
    current_target,
    record_driver_location,
    road_eta,
)

PASSWORD = "str0ng-Pass-2026"

# Yola reference points
AUN = (Decimal("9.334500"), Decimal("12.494400"))
MAU = (Decimal("9.202800"), Decimal("12.481000"))


class TrackingTests(TestCase):
    def setUp(self):
        cache.clear()
        FareSetting.objects.create(
            vehicle_category="CAR",
            base_fare=Decimal("500"),
            per_km=Decimal("120"),
            per_minute=Decimal("15"),
            minimum_fare=Decimal("700"),
            rounding_step=Decimal("50"),
            is_active=True,
        )
        self.passenger = register_passenger(phone="+2348031700001", password=PASSWORD)
        self.driver = register_driver(
            phone="+2348031700002", password=PASSWORD, driver_category="CAR"
        )
        profile = DriverProfile.objects.get(user=self.driver)
        profile.approval_status = DriverApprovalStatus.APPROVED
        profile.save(update_fields=["approval_status"])
        Vehicle.objects.create(
            driver=profile, category="CAR", make="Toyota", model="Corolla",
            year=2016, color="Black", plate_number="TRK001AA", is_active=True,
        )
        self.ride = Ride.objects.create(
            passenger=self.passenger,
            driver=self.driver,
            status=RideStatus.ACCEPTED,
            requested_vehicle_category="CAR",
            pickup_address="AUN", dropoff_address="MAU",
            pickup_lat=AUN[0], pickup_lng=AUN[1],
            dropoff_lat=MAU[0], dropoff_lng=MAU[1],
        )

    # ---- target selection ----
    def test_target_is_pickup_before_boarding(self):
        for status in (RideStatus.ACCEPTED, RideStatus.DRIVER_ARRIVED):
            self.ride.status = status
            self.assertEqual(current_target(self.ride)["kind"], "pickup")

    def test_target_switches_to_dropoff_after_pickup(self):
        self.ride.status = RideStatus.IN_PROGRESS
        target = current_target(self.ride)
        self.assertEqual(target["kind"], "dropoff")
        self.assertEqual(target["address"], "MAU")

    # ---- payload ----
    def test_payload_has_position_distance_and_eta(self):
        payload = build_location_payload(
            self.ride, lat=Decimal("9.300000"), lng=Decimal("12.490000"),
            heading=90.0, speed=8.5, accuracy=5.0,
        )
        self.assertEqual(payload["type"], "ride.driver_location")
        self.assertEqual(payload["ride_id"], self.ride.pk)
        self.assertEqual(payload["location"]["heading"], 90.0)
        self.assertEqual(payload["location"]["speed"], 8.5)
        self.assertEqual(payload["target"]["kind"], "pickup")
        # ~3.9 km straight line from that point to AUN
        self.assertGreater(payload["straight_line_m"], 3_000)
        self.assertLess(payload["straight_line_m"], 5_000)
        self.assertIn("distance_m", payload["eta"])
        self.assertGreater(payload["eta"]["duration_s"], 0)

    def test_eta_is_cached_between_calls(self):
        target = current_target(self.ride)
        with mock.patch("apps.geo.routing.road_route") as route:
            route.return_value = mock.Mock(distance_m=4200, duration_s=600)
            first = road_eta(self.ride, AUN[0], AUN[1], target)
            second = road_eta(self.ride, AUN[0], AUN[1], target)
        self.assertEqual(first["distance_m"], 4200)
        self.assertEqual(second, first)
        route.assert_called_once()  # throttled — one provider call, not two

    def test_eta_falls_back_when_routing_fails(self):
        target = current_target(self.ride)
        with mock.patch("apps.geo.routing.road_route", side_effect=RuntimeError("provider down")):
            eta = road_eta(self.ride, Decimal("9.300000"), Decimal("12.490000"), target)
        self.assertEqual(eta["source"], "estimate")
        self.assertGreater(eta["distance_m"], 0)
        self.assertGreater(eta["duration_s"], 0)

    # ---- record + broadcast ----
    def test_record_broadcasts_to_passenger_and_driver(self):
        with mock.patch("apps.rides.tracking.broadcast_location") as broadcast:
            payload = record_driver_location(
                self.driver, lat=Decimal("9.310000"), lng=Decimal("12.492000")
            )
        self.assertIsNotNone(payload)
        broadcast.assert_called_once()
        # Position persisted for dispatch as well
        availability = DriverProfile.objects.get(user=self.driver).availability
        self.assertEqual(availability.current_lat, Decimal("9.310000"))

    def test_no_broadcast_without_active_ride(self):
        self.ride.status = RideStatus.COMPLETED
        self.ride.save(update_fields=["status"])
        with mock.patch("apps.rides.tracking.broadcast_location") as broadcast:
            payload = record_driver_location(
                self.driver, lat=Decimal("9.310000"), lng=Decimal("12.492000")
            )
        self.assertIsNone(payload)
        broadcast.assert_not_called()
        # …but the fix is still stored so dispatch stays accurate
        availability = DriverProfile.objects.get(user=self.driver).availability
        self.assertEqual(availability.current_lng, Decimal("12.492000"))

    def test_passenger_is_not_a_driver_and_is_ignored(self):
        self.assertIsNone(
            record_driver_location(self.passenger, lat=AUN[0], lng=AUN[1])
        )
