import tempfile

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.accounts.services import register_driver, register_passenger

from .models import DriverApprovalStatus

PASSWORD = "str0ng-Pass-2026"

VEHICLE = {
    "category": "CAR",
    "make": "Toyota",
    "model": "Corolla",
    "year": 2016,
    "color": "Black",
    "plate_number": "ABC123XY",
}

# Smallest valid GIF — used in the type-rejection test
TINY_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04"
    b"\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)

# Real 1x1 PNG generated with Pillow — valid, decodes cleanly
def _tiny_png() -> bytes:
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (1, 1), "white").save(buf, format="PNG")
    return buf.getvalue()


TINY_PNG = _tiny_png()


class DriverOnboardingTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.driver = register_driver(phone="+2348031200001", password=PASSWORD, first_name="Driver")
        self.passenger = register_passenger(phone="+2348031200002", password=PASSWORD)
        self.admin = User.objects.create_user(
            "+2348031200003", PASSWORD, role=UserRole.ADMIN, is_staff=True
        )

    def login(self, user):
        # Re-fetch to mirror real requests: JWT auth loads the user (and its
        # related profile) fresh per request, never from a cached instance.
        self.client.force_authenticate(user=User.objects.get(pk=user.pk))

    def approve(self, driver_user=None):
        driver_user = driver_user or self.driver
        self.login(self.admin)
        resp = self.client.post(
            reverse("management:driver-approve", args=[driver_user.driver_profile.pk]), {}
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        return resp


class OnboardingTests(DriverOnboardingTestCase):
    def test_driver_updates_profile_license(self):
        self.login(self.driver)
        resp = self.client.put(
            reverse("drivers:my-profile"), {"license_number": "LAG-2026-777"}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["license_number"], "LAG-2026-777")
        self.assertEqual(resp.data["approval_status"], DriverApprovalStatus.PENDING)

    def test_passenger_cannot_access_driver_endpoints(self):
        self.login(self.passenger)
        resp = self.client.get(reverse("drivers:my-profile"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_vehicle_get_before_creation_is_404(self):
        self.login(self.driver)
        resp = self.client.get(reverse("drivers:my-vehicle"))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_vehicle_put_creates_then_updates(self):
        self.login(self.driver)
        resp = self.client.put(reverse("drivers:my-vehicle"), VEHICLE)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        vehicle_id = resp.data["id"]

        resp = self.client.put(reverse("drivers:my-vehicle"), {**VEHICLE, "color": "Red"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["id"], vehicle_id)  # same vehicle, updated
        self.assertEqual(resp.data["color"], "Red")

    def test_duplicate_plate_number_rejected(self):
        other = register_driver(phone="+2348031200009", password=PASSWORD)
        self.login(other)
        self.client.put(reverse("drivers:my-vehicle"), VEHICLE)

        self.login(self.driver)
        resp = self.client.put(reverse("drivers:my-vehicle"), VEHICLE)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("plate_number", resp.data)

    def test_vehicle_requires_category(self):
        self.login(self.driver)
        payload = {k: v for k, v in VEHICLE.items() if k != "category"}
        resp = self.client.put(reverse("drivers:my-vehicle"), payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", resp.data)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_vehicle_photo_type_rejected(self):
        self.login(self.driver)
        gif_upload = SimpleUploadedFile("keke.gif", TINY_GIF, content_type="image/gif")
        resp = self.client.put(
            reverse("drivers:my-vehicle"),
            {**VEHICLE, "plate_number": "REJ001AA", "photo": gif_upload},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("photo", resp.data)
        self.assertIn("JPEG", str(resp.data["photo"]))

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_vehicle_photo_size_rejected(self):
        """Uploading > 5 MB is rejected before the file lands on disk."""
        self.login(self.driver)
        # Real 6 MB PNG (2000x2000 solid image compresses beyond the cap).
        from io import BytesIO
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (2500, 2500), "red").save(buf, format="PNG")
        blob = buf.getvalue()
        # Pad if Pillow's PNG was smaller than 5 MB (varies by version)
        if len(blob) <= 5 * 1024 * 1024:
            blob = blob + b"\x00" * (5 * 1024 * 1024 + 1024 - len(blob))
        big_upload = SimpleUploadedFile("big.png", blob, content_type="image/png")
        resp = self.client.put(
            reverse("drivers:my-vehicle"),
            {**VEHICLE, "plate_number": "BIG001AA", "photo": big_upload},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("photo", resp.data)
        self.assertIn("too large", str(resp.data["photo"]))

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_vehicle_with_category_and_photo_upload(self):
        keke_driver = register_driver(
            phone="+2348031200011", password=PASSWORD, driver_category="KEKE"
        )
        self.login(keke_driver)
        photo = SimpleUploadedFile("keke.png", TINY_PNG, content_type="image/png")
        resp = self.client.put(
            reverse("drivers:my-vehicle"),
            {**VEHICLE, "category": "KEKE", "plate_number": "KEK987AB", "photo": photo},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["category"], "KEKE")
        self.assertIsNotNone(resp.data["photo_url"])
        self.assertIn("/media/vehicles/", resp.data["photo_url"])
        self.assertTrue(resp.data["photo_url"].startswith("http"))

        # update WITHOUT a new photo keeps the existing one
        resp = self.client.put(
            reverse("drivers:my-vehicle"),
            {**VEHICLE, "category": "KEKE", "plate_number": "KEK987AB", "color": "Yellow"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["color"], "Yellow")
        self.assertIsNotNone(resp.data["photo_url"])

    def test_car_driver_cannot_register_keke_vehicle(self):
        """V1 alignment rule: a CAR driver cannot register a KEKE and vice-versa."""
        self.login(self.driver)  # self.driver defaults to CAR at registration
        resp = self.client.put(
            reverse("drivers:my-vehicle"),
            {**VEHICLE, "category": "KEKE", "plate_number": "MIX123XY"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Car driver", str(resp.data))

    def test_keke_driver_cannot_register_car_vehicle(self):
        keke_driver = register_driver(
            phone="+2348031200012", password=PASSWORD, driver_category="KEKE"
        )
        self.login(keke_driver)
        resp = self.client.put(
            reverse("drivers:my-vehicle"),
            {**VEHICLE, "category": "CAR", "plate_number": "MIX456XY"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # Choices label is "Keke (tricycle)"
        self.assertIn("Keke", str(resp.data))
        self.assertIn("must be a", str(resp.data))


class AvailabilityTests(DriverOnboardingTestCase):
    def test_unapproved_driver_cannot_go_online(self):
        self.login(self.driver)
        resp = self.client.post(reverse("drivers:my-availability"), {"is_online": True})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_approved_driver_without_vehicle_cannot_go_online(self):
        self.approve()
        self.login(self.driver)
        resp = self.client.post(reverse("drivers:my-availability"), {"is_online": True})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approved_driver_with_vehicle_goes_online_and_offline(self):
        self.approve()
        self.login(self.driver)
        self.client.put(reverse("drivers:my-vehicle"), VEHICLE)

        resp = self.client.post(reverse("drivers:my-availability"), {"is_online": True})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertTrue(resp.data["is_online"])

        resp = self.client.post(reverse("drivers:my-availability"), {"is_online": False})
        self.assertFalse(resp.data["is_online"])

    def test_location_update_stores_coordinates(self):
        self.approve()
        self.login(self.driver)
        self.client.put(reverse("drivers:my-vehicle"), VEHICLE)
        resp = self.client.post(
            reverse("drivers:my-location"), {"lat": "6.524400", "lng": "3.379200"}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["current_lat"], "6.524400")
        self.assertIsNotNone(resp.data["location_updated_at"])


class ApprovalWorkflowTests(DriverOnboardingTestCase):
    def test_admin_approves_driver(self):
        resp = self.approve()
        self.assertEqual(resp.data["approval_status"], DriverApprovalStatus.APPROVED)
        self.assertIsNotNone(resp.data["approved_at"])
        self.assertEqual(resp.data["approved_by"], self.admin.pk)

    def test_approving_twice_fails(self):
        self.approve()
        resp = self.client.post(
            reverse("management:driver-approve", args=[self.driver.driver_profile.pk]), {}
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_requires_reason_and_forces_offline(self):
        self.approve()
        self.login(self.driver)
        self.client.put(reverse("drivers:my-vehicle"), VEHICLE)
        self.client.post(reverse("drivers:my-availability"), {"is_online": True})

        self.login(self.admin)
        profile_pk = self.driver.driver_profile.pk
        resp = self.client.post(reverse("management:driver-reject", args=[profile_pk]), {})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)  # reason required

        resp = self.client.post(
            reverse("management:driver-reject", args=[profile_pk]),
            {"reason": "License could not be verified"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["approval_status"], DriverApprovalStatus.REJECTED)
        self.assertFalse(resp.data["availability"]["is_online"])

    def test_license_change_after_approval_resets_to_pending(self):
        self.approve()
        self.login(self.driver)
        resp = self.client.put(
            reverse("drivers:my-profile"), {"license_number": "NEW-LICENSE-001"}
        )
        self.assertEqual(resp.data["approval_status"], DriverApprovalStatus.PENDING)

    def test_non_admin_cannot_use_management_endpoints(self):
        profile_pk = self.driver.driver_profile.pk
        for user in (self.driver, self.passenger):
            self.login(user)
            resp = self.client.get(reverse("management:driver-list"))
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
            resp = self.client.post(
                reverse("management:driver-approve", args=[profile_pk]), {}
            )
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_list_filters_by_approval_status(self):
        self.approve()
        register_driver(phone="+2348031200010", password=PASSWORD)  # stays PENDING
        self.login(self.admin)
        resp = self.client.get(reverse("management:driver-list"), {"approval_status": "pending"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        statuses = {d["approval_status"] for d in resp.data["results"]}
        self.assertEqual(statuses, {DriverApprovalStatus.PENDING})


class UserManagementTests(DriverOnboardingTestCase):
    def test_users_list_filters_by_role(self):
        self.login(self.admin)
        resp = self.client.get(reverse("management:user-list"), {"role": "driver"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        roles = {u["role"] for u in resp.data["results"]}
        self.assertEqual(roles, {UserRole.DRIVER})

    def test_users_list_search_by_phone(self):
        self.login(self.admin)
        resp = self.client.get(reverse("management:user-list"), {"search": "31200002"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(resp.data["results"][0]["phone"], "+2348031200002")
