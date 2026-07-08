from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.drivers.models import DriverApprovalStatus
from apps.payments.constants import PaymentMethod

from .models import User, UserRole

PASSWORD = "str0ng-Pass-2026"


class RegistrationTests(APITestCase):
    def setUp(self):
        cache.clear()  # reset throttle counters between test cases

    def test_register_passenger_with_local_phone(self):
        resp = self.client.post(
            reverse("accounts:register-passenger"),
            {"phone": "0803 111 0001", "password": PASSWORD, "first_name": "Ada"},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["user"]["phone"], "+2348031110001")
        self.assertEqual(resp.data["user"]["role"], UserRole.PASSENGER)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        user = User.objects.get(phone="+2348031110001")
        self.assertTrue(hasattr(user, "passenger_profile"))

    def test_register_car_driver_creates_profile_and_availability(self):
        resp = self.client.post(
            reverse("accounts:register-driver"),
            {"phone": "08031110002", "password": PASSWORD, "driver_category": "CAR"},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        user = User.objects.get(phone="+2348031110002")
        self.assertEqual(user.role, UserRole.DRIVER)
        self.assertEqual(user.driver_profile.driver_category, "CAR")
        self.assertEqual(user.driver_profile.approval_status, DriverApprovalStatus.PENDING)
        self.assertFalse(user.driver_profile.availability.is_online)

    def test_register_keke_driver(self):
        resp = self.client.post(
            reverse("accounts:register-driver"),
            {"phone": "08031110020", "password": PASSWORD, "driver_category": "KEKE"},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["user"]["role"], UserRole.DRIVER)
        user = User.objects.get(phone="+2348031110020")
        self.assertEqual(user.driver_profile.driver_category, "KEKE")

    def test_driver_registration_requires_category(self):
        resp = self.client.post(
            reverse("accounts:register-driver"),
            {"phone": "08031110021", "password": PASSWORD},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("driver_category", resp.data)

    def test_duplicate_phone_rejected_across_formats(self):
        self.client.post(
            reverse("accounts:register-passenger"),
            {"phone": "08031110003", "password": PASSWORD},
        )
        resp = self.client.post(
            reverse("accounts:register-passenger"),
            {"phone": "+2348031110003", "password": PASSWORD},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone", resp.data)

    def test_weak_password_rejected(self):
        resp = self.client.post(
            reverse("accounts:register-passenger"),
            {"phone": "08031110004", "password": "12345678"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", resp.data)


class LoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            "+2348031110005", PASSWORD, role=UserRole.PASSENGER, first_name="Bola"
        )

    def test_login_with_local_format_phone(self):
        resp = self.client.post(
            reverse("accounts:token"), {"phone": "0803 111 0005", "password": PASSWORD}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertIn("access", resp.data)
        self.assertEqual(resp.data["user"]["phone"], "+2348031110005")

    def test_login_with_wrong_password_fails(self):
        resp = self.client.post(
            reverse("accounts:token"), {"phone": "+2348031110005", "password": "wrong-pass"}
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class MeEndpointTests(APITestCase):
    def setUp(self):
        cache.clear()
        resp = self.client.post(
            reverse("accounts:register-passenger"),
            {"phone": "08031110006", "password": PASSWORD, "first_name": "Chi"},
        )
        self.access = resp.data["access"]

    def auth(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def test_me_requires_authentication(self):
        resp = self.client.get(reverse("accounts:me"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_role_aware_profile(self):
        self.auth()
        resp = self.client.get(reverse("accounts:me"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["role"], UserRole.PASSENGER)
        self.assertEqual(resp.data["profile"]["default_payment_method"], PaymentMethod.CASH)

    def test_patch_me_updates_name_and_payment_method(self):
        self.auth()
        resp = self.client.patch(
            reverse("accounts:me"),
            {"first_name": "Chidinma", "default_payment_method": PaymentMethod.TRANSFER},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["first_name"], "Chidinma")
        self.assertEqual(resp.data["profile"]["default_payment_method"], PaymentMethod.TRANSFER)

    def test_phone_and_role_are_read_only(self):
        self.auth()
        resp = self.client.patch(
            reverse("accounts:me"), {"phone": "+2348099999999", "role": UserRole.ADMIN}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["phone"], "+2348031110006")
        self.assertEqual(resp.data["role"], UserRole.PASSENGER)
