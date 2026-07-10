import tempfile
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.accounts.services import register_driver, register_passenger
from apps.drivers.models import Vehicle
from apps.drivers.services import approve_driver, set_availability
from apps.payments.constants import PaymentMethod, PaymentStatus
from apps.pricing.models import FareSetting

from .constants import RideEventType, RideStatus
from .models import Ride, RideEvent
from .services import expire_stale_rides

PASSWORD = "str0ng-Pass-2026"

# American University of Nigeria → Modibbo Adama University, both in Yola
RIDE_PAYLOAD = {
    "vehicle_category": "CAR",
    "pickup": {"address": "American University of Nigeria", "lat": "9.334500", "lng": "12.494400"},
    "dropoff": {"address": "Modibbo Adama University", "lat": "9.202800", "lng": "12.481000"},
}


def create_fare_setting(**overrides):
    defaults = dict(
        vehicle_category="CAR",
        base_fare=Decimal("500"),
        per_km=Decimal("120"),
        per_minute=Decimal("15"),
        minimum_fare=Decimal("700"),
        rounding_step=Decimal("50"),
        is_active=True,
    )
    defaults.update(overrides)
    return FareSetting.objects.create(**defaults)


def create_keke_fare_setting(**overrides):
    defaults = dict(
        vehicle_category="KEKE",
        base_fare=Decimal("300"),
        per_km=Decimal("80"),
        per_minute=Decimal("10"),
        minimum_fare=Decimal("400"),
        rounding_step=Decimal("50"),
        is_active=True,
    )
    defaults.update(overrides)
    return FareSetting.objects.create(**defaults)


def make_ready_driver(phone: str, plate: str, category: str = "CAR"):
    """Registered, approved, vehicled, online. Driver signs up under the
    given category so the vehicle-alignment rule is satisfied."""
    admin = User.objects.filter(role=UserRole.ADMIN).first()
    driver = register_driver(
        phone=phone, password=PASSWORD, first_name="Driver", driver_category=category
    )
    approve_driver(driver.driver_profile, admin_user=admin)
    Vehicle.objects.create(
        driver=driver.driver_profile, category=category, make="Toyota", model="Corolla",
        year=2016, color="Black", plate_number=plate,
    )
    set_availability(driver.driver_profile, is_online=True)
    return driver


class RideTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        create_fare_setting()
        self.admin = User.objects.create_user("+2348031400000", PASSWORD, role=UserRole.ADMIN)
        self.passenger = register_passenger(
            phone="+2348031400001", password=PASSWORD, first_name="Ada"
        )
        self.driver = make_ready_driver("+2348031400002", "AAA111AA")

    def login(self, user):
        self.client.force_authenticate(user=User.objects.get(pk=user.pk))

    def request_ride(self, passenger=None, **extra):
        self.login(passenger or self.passenger)
        resp = self.client.post(
            reverse("rides:list-create"), {**RIDE_PAYLOAD, **extra}, format="json"
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        return resp.data

    def act(self, user, ride_id, action, payload=None):
        self.login(user)
        return self.client.post(reverse(f"rides:{action}", args=[ride_id]), payload or {})


# ---------------------------------------------------------------------------
# Estimation (Module 5)
# ---------------------------------------------------------------------------


class EstimateEndpointTests(APITestCase):
    """Runs against the stub geo provider (the test/default GEO_PROVIDER)."""

    def setUp(self):
        cache.clear()
        self.passenger = register_passenger(phone="+2348031300001", password=PASSWORD)
        self.client.force_authenticate(user=self.passenger)
        create_fare_setting()

    def estimate(self, payload):
        return self.client.post(reverse("rides:estimate"), payload, format="json")

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        resp = self.estimate({"pickup": {"address": "A"}, "dropoff": {"address": "B"}})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_estimate_with_coordinates(self):
        resp = self.estimate(RIDE_PAYLOAD)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertGreater(resp.data["distance_m"], 10_000)
        fare = Decimal(resp.data["fare"])
        self.assertGreaterEqual(fare, Decimal("700"))
        self.assertEqual(fare % Decimal("50"), 0)
        self.assertEqual(resp.data["currency"], "NGN")

    def test_estimate_with_addresses_uses_geocoder(self):
        resp = self.estimate(
            {
                "vehicle_category": "CAR",
                "pickup": {"address": "Ikeja City Mall"},
                "dropoff": {"address": "Yaba Market"},
            }
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertNotEqual(resp.data["pickup"]["lat"], resp.data["dropoff"]["lat"])

    def test_estimate_requires_vehicle_category(self):
        payload = {k: v for k, v in RIDE_PAYLOAD.items() if k != "vehicle_category"}
        resp = self.estimate(payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("vehicle_category", resp.data)

    def test_keke_and_car_use_different_fares(self):
        create_keke_fare_setting()
        car = self.estimate(RIDE_PAYLOAD)
        keke = self.estimate({**RIDE_PAYLOAD, "vehicle_category": "KEKE"})
        self.assertEqual(car.status_code, status.HTTP_200_OK, car.data)
        self.assertEqual(keke.status_code, status.HTTP_200_OK, keke.data)
        self.assertEqual(car.data["vehicle_category"], "CAR")
        self.assertEqual(keke.data["vehicle_category"], "KEKE")
        # same route, cheaper keke pricing -> lower fare
        self.assertLess(Decimal(keke.data["fare"]), Decimal(car.data["fare"]))

    def test_estimate_fails_when_category_has_no_fare(self):
        resp = self.estimate({**RIDE_PAYLOAD, "vehicle_category": "KEKE"})  # no KEKE fare
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("KEKE", str(resp.data))

    def test_location_without_address_or_coords_rejected(self):
        resp = self.estimate({"pickup": {"address": ""}, "dropoff": {"address": "Yaba"}})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_partial_coordinates_rejected(self):
        resp = self.estimate({"pickup": {"lat": "6.601800"}, "dropoff": {"address": "Yaba"}})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_active_fare_setting_gives_clear_error(self):
        FareSetting.objects.update(is_active=False)
        resp = self.estimate(RIDE_PAYLOAD)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not configured", str(resp.data))


# ---------------------------------------------------------------------------
# Ride creation
# ---------------------------------------------------------------------------


class CreateRideTests(RideTestCase):
    def test_passenger_creates_ride(self):
        data = self.request_ride()
        self.assertEqual(data["status"], RideStatus.SEARCHING)
        self.assertEqual(data["requested_vehicle_category"], "CAR")
        self.assertEqual(
            Ride.objects.get(pk=data["id"]).requested_vehicle_category, "CAR"
        )
        self.assertIsNone(data["driver"])
        self.assertEqual(data["payment"]["status"], PaymentStatus.PENDING)
        self.assertEqual(data["payment_method"], PaymentMethod.CASH)  # profile default
        self.assertIsNotNone(data["estimated_fare"])
        ride = Ride.objects.get(pk=data["id"])
        self.assertIsNotNone(ride.fare_setting)
        self.assertTrue(
            ride.events.filter(event_type=RideEventType.REQUESTED, actor=self.passenger).exists()
        )

    def test_explicit_payment_method(self):
        data = self.request_ride(payment_method=PaymentMethod.TRANSFER)
        self.assertEqual(data["payment_method"], PaymentMethod.TRANSFER)
        self.assertEqual(data["payment"]["method"], PaymentMethod.TRANSFER)

    def test_second_active_ride_rejected(self):
        self.request_ride()
        resp = self.client.post(reverse("rides:list-create"), RIDE_PAYLOAD, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("active ride", str(resp.data))

    def test_driver_cannot_create_ride(self):
        self.login(self.driver)
        resp = self.client.post(reverse("rides:list-create"), RIDE_PAYLOAD, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Accept / reject
# ---------------------------------------------------------------------------


class AcceptRideTests(RideTestCase):
    def test_online_approved_driver_accepts(self):
        ride = self.request_ride()
        resp = self.act(self.driver, ride["id"], "accept")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["status"], RideStatus.ACCEPTED)
        self.assertEqual(resp.data["driver"]["id"], self.driver.pk)
        self.assertEqual(resp.data["vehicle"]["plate_number"], "AAA111AA")
        self.assertIsNotNone(resp.data["accepted_at"])
        # No photo uploaded -> passenger sees null, frontend shows a fallback
        self.assertIsNone(resp.data["driver"]["photo_url"])

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_passenger_sees_driver_photo_after_acceptance(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.drivers.tests import TINY_PNG

        profile = self.driver.driver_profile
        profile.photo = SimpleUploadedFile("d.png", TINY_PNG, content_type="image/png")
        profile.save(update_fields=["photo"])

        ride = self.request_ride()
        self.act(self.driver, ride["id"], "accept")

        # Passenger pulls their active ride and sees the driver's photo
        self.login(self.passenger)
        resp = self.client.get(reverse("rides:active"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertIsNotNone(resp.data["driver"]["photo_url"])
        self.assertIn("/media/drivers/", resp.data["driver"]["photo_url"])

    def test_offline_driver_cannot_accept(self):
        ride = self.request_ride()
        set_availability(self.driver.driver_profile, is_online=False)
        resp = self.act(self.driver, ride["id"], "accept")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("online", str(resp.data))

    def test_second_driver_loses_the_race(self):
        ride = self.request_ride()
        other = make_ready_driver("+2348031400003", "BBB222BB")
        self.act(self.driver, ride["id"], "accept")
        resp = self.act(other, ride["id"], "accept")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("no longer available", str(resp.data))

    def test_busy_driver_cannot_accept_another(self):
        first = self.request_ride()
        self.act(self.driver, first["id"], "accept")
        second_passenger = register_passenger(phone="+2348031400010", password=PASSWORD)
        second = self.request_ride(passenger=second_passenger)
        resp = self.act(self.driver, second["id"], "accept")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("active trip", str(resp.data))

    def test_accepting_stale_ride_expires_it(self):
        ride = self.request_ride()
        Ride.objects.filter(pk=ride["id"]).update(
            created_at=timezone.now() - timedelta(minutes=30)
        )
        resp = self.act(self.driver, ride["id"], "accept")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expired", str(resp.data))
        self.assertEqual(Ride.objects.get(pk=ride["id"]).status, RideStatus.EXPIRED)

    def test_category_matching_enforced(self):
        """KEKE rides only for KEKE drivers, and vice versa."""
        create_keke_fare_setting()
        keke_driver = make_ready_driver("+2348031400020", "KEK111AA", category="KEKE")
        keke_ride = self.request_ride(vehicle_category="KEKE")

        # CAR driver: ride absent from feed, accept rejected
        self.login(self.driver)
        resp = self.client.get(reverse("rides:open"))
        self.assertEqual(resp.data["results"], [])
        resp = self.act(self.driver, keke_ride["id"], "accept")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Keke", str(resp.data))

        # KEKE driver: sees it and accepts it
        self.login(keke_driver)
        resp = self.client.get(reverse("rides:open"))
        self.assertEqual([r["id"] for r in resp.data["results"]], [keke_ride["id"]])
        resp = self.act(keke_driver, keke_ride["id"], "accept")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["vehicle"]["category"], "KEKE")

    def test_reject_hides_ride_from_open_feed(self):
        ride = self.request_ride()
        self.login(self.driver)
        resp = self.client.get(reverse("rides:open"))
        self.assertEqual([r["id"] for r in resp.data["results"]], [ride["id"]])

        self.act(self.driver, ride["id"], "reject")
        resp = self.client.get(reverse("rides:open"))
        self.assertEqual(resp.data["results"], [])
        # ride itself unaffected
        self.assertEqual(Ride.objects.get(pk=ride["id"]).status, RideStatus.SEARCHING)


# ---------------------------------------------------------------------------
# Trip progression
# ---------------------------------------------------------------------------


class TripProgressionTests(RideTestCase):
    def accepted_ride(self):
        ride = self.request_ride()
        self.act(self.driver, ride["id"], "accept")
        return ride["id"]

    def test_full_happy_path(self):
        ride_id = self.accepted_ride()

        resp = self.act(self.driver, ride_id, "arrived")
        self.assertEqual(resp.data["status"], RideStatus.DRIVER_ARRIVED)
        self.assertIsNotNone(resp.data["arrived_at"])

        resp = self.act(self.driver, ride_id, "start")
        self.assertEqual(resp.data["status"], RideStatus.IN_PROGRESS)

        resp = self.act(self.driver, ride_id, "complete")
        self.assertEqual(resp.data["status"], RideStatus.COMPLETED)
        self.assertEqual(resp.data["final_fare"], resp.data["estimated_fare"])
        self.assertEqual(resp.data["payment"]["amount"], resp.data["final_fare"])

        events = list(
            RideEvent.objects.filter(ride_id=ride_id).values_list("event_type", flat=True)
        )
        self.assertEqual(
            events,
            [
                RideEventType.REQUESTED,
                RideEventType.ACCEPTED,
                RideEventType.DRIVER_ARRIVED,
                RideEventType.TRIP_STARTED,
                RideEventType.TRIP_COMPLETED,
            ],
        )

    def test_cannot_start_before_arrived(self):
        ride_id = self.accepted_ride()
        resp = self.act(self.driver, ride_id, "start")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_driver_cannot_progress_ride(self):
        ride_id = self.accepted_ride()
        other = make_ready_driver("+2348031400004", "CCC333CC")
        resp = self.act(other, ride_id, "arrived")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


class CancellationTests(RideTestCase):
    def test_passenger_cancels_searching_ride(self):
        ride = self.request_ride()
        resp = self.act(self.passenger, ride["id"], "cancel", {"reason": "Changed my mind"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["status"], RideStatus.CANCELLED)
        self.assertEqual(resp.data["cancelled_by_role"], "PASSENGER")
        self.assertEqual(resp.data["cancellation_reason"], "Changed my mind")
        self.assertIsNotNone(resp.data["cancelled_at"])
        db_ride = Ride.objects.get(pk=ride["id"])
        self.assertEqual(db_ride.cancelled_by_user, self.passenger)

    def test_passenger_cannot_cancel_after_driver_accepts(self):
        ride = self.request_ride()
        self.act(self.driver, ride["id"], "accept")
        resp = self.act(self.passenger, ride["id"], "cancel")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("You can no longer cancel this ride", str(resp.data))
        self.assertEqual(Ride.objects.get(pk=ride["id"]).status, RideStatus.ACCEPTED)

    def test_passenger_cannot_cancel_when_driver_arrived(self):
        ride = self.request_ride()
        self.act(self.driver, ride["id"], "accept")
        self.act(self.driver, ride["id"], "arrived")
        resp = self.act(self.passenger, ride["id"], "cancel")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("You can no longer cancel this ride", str(resp.data))

    def test_passenger_cannot_cancel_in_progress_trip(self):
        ride = self.request_ride()
        self.act(self.driver, ride["id"], "accept")
        self.act(self.driver, ride["id"], "arrived")
        self.act(self.driver, ride["id"], "start")
        resp = self.act(self.passenger, ride["id"], "cancel")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # Message now flags driver acceptance; still a 400 with a clear reason
        self.assertIn("You can no longer cancel this ride", str(resp.data))

    def test_driver_cancel_requires_reason(self):
        ride = self.request_ride()
        self.act(self.driver, ride["id"], "accept")
        resp = self.act(self.driver, ride["id"], "cancel")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        resp = self.act(self.driver, ride["id"], "cancel", {"reason": "Flat tyre"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["cancelled_by_role"], "DRIVER")

    def test_admin_can_cancel_in_progress_trip(self):
        ride = self.request_ride()
        self.act(self.driver, ride["id"], "accept")
        self.act(self.driver, ride["id"], "arrived")
        self.act(self.driver, ride["id"], "start")
        resp = self.act(self.admin, ride["id"], "cancel", {"reason": "Ops intervention"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["cancelled_by_role"], "ADMIN")

    def test_stranger_cannot_cancel(self):
        ride = self.request_ride()
        stranger = register_passenger(phone="+2348031400011", password=PASSWORD)
        resp = self.act(stranger, ride["id"], "cancel")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cancelled_ride_cannot_be_accepted(self):
        ride = self.request_ride()
        self.act(self.passenger, ride["id"], "cancel")
        resp = self.act(self.driver, ride["id"], "accept")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Active ride, history, expiry
# ---------------------------------------------------------------------------


class ActiveAndHistoryTests(RideTestCase):
    def test_active_ride_for_both_parties(self):
        ride = self.request_ride()

        self.login(self.passenger)
        resp = self.client.get(reverse("rides:active"))
        self.assertEqual(resp.data["id"], ride["id"])

        # driver has no active trip until accepting
        self.login(self.driver)
        self.assertEqual(
            self.client.get(reverse("rides:active")).status_code, status.HTTP_404_NOT_FOUND
        )
        self.act(self.driver, ride["id"], "accept")
        self.login(self.driver)
        resp = self.client.get(reverse("rides:active"))
        self.assertEqual(resp.data["id"], ride["id"])

    def test_stale_searching_ride_expires_on_active_poll(self):
        ride = self.request_ride()
        Ride.objects.filter(pk=ride["id"]).update(
            created_at=timezone.now() - timedelta(minutes=30)
        )
        self.login(self.passenger)
        resp = self.client.get(reverse("rides:active"))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Ride.objects.get(pk=ride["id"]).status, RideStatus.EXPIRED)

    def test_history_shows_terminal_rides_only(self):
        active = self.request_ride()
        self.act(self.passenger, active["id"], "cancel")
        second = self.request_ride()  # allowed now: first is CANCELLED

        self.login(self.passenger)
        resp = self.client.get(reverse("rides:list-create"))
        ids = [r["id"] for r in resp.data["results"]]
        self.assertIn(active["id"], ids)
        self.assertNotIn(second["id"], ids)  # still SEARCHING -> not history

    def test_expire_stale_rides_service(self):
        ride = self.request_ride()
        Ride.objects.filter(pk=ride["id"]).update(
            created_at=timezone.now() - timedelta(minutes=30)
        )
        self.assertEqual(expire_stale_rides(), 1)
        db_ride = Ride.objects.get(pk=ride["id"])
        self.assertEqual(db_ride.status, RideStatus.EXPIRED)
        self.assertIsNotNone(db_ride.expired_at)
        self.assertTrue(db_ride.events.filter(event_type=RideEventType.EXPIRED).exists())

    def test_ride_detail_hidden_from_strangers(self):
        ride = self.request_ride()
        stranger = register_passenger(phone="+2348031400012", password=PASSWORD)
        self.login(stranger)
        resp = self.client.get(reverse("rides:detail", args=[ride["id"]]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_management_rides_list_with_status_filter(self):
        ride = self.request_ride()
        self.act(self.passenger, ride["id"], "cancel")
        second = self.request_ride()

        self.login(self.admin)
        resp = self.client.get(reverse("management:ride-list"), {"status": "searching"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in resp.data["results"]]
        self.assertEqual(ids, [second["id"]])

        # non-admin blocked
        self.login(self.passenger)
        resp = self.client.get(reverse("management:ride-list"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
