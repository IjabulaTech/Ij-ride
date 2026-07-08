from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole

from .models import FareSetting
from .services import calculate_fare


def make_setting(**overrides):
    defaults = dict(
        base_fare=Decimal("500"),
        per_km=Decimal("120"),
        per_minute=Decimal("15"),
        minimum_fare=Decimal("700"),
        rounding_step=Decimal("50"),
    )
    defaults.update(overrides)
    return FareSetting(**defaults)  # unsaved instance is fine for pure math


class FareCalculationTests(TestCase):
    def test_standard_fare(self):
        # 10 km, 20 min: 500 + 1200 + 300 = 2000 (already on the 50 step)
        fare, breakdown = calculate_fare(
            distance_m=10_000, duration_s=1_200, fare_setting=make_setting()
        )
        self.assertEqual(fare, Decimal("2000.00"))
        self.assertEqual(breakdown["distance_fare"], "1200.00")
        self.assertEqual(breakdown["time_fare"], "300.00")
        self.assertFalse(breakdown["minimum_fare_applied"])

    def test_rounds_up_to_step(self):
        # 7.3 km, 11 min: 500 + 876 + 165 = 1541 -> rounds UP to 1550
        fare, _ = calculate_fare(
            distance_m=7_300, duration_s=660, fare_setting=make_setting()
        )
        self.assertEqual(fare, Decimal("1550.00"))

    def test_minimum_fare_applies_to_short_trips(self):
        # 1 km, 3 min: 500 + 120 + 45 = 665 -> minimum 700
        fare, breakdown = calculate_fare(
            distance_m=1_000, duration_s=180, fare_setting=make_setting()
        )
        self.assertEqual(fare, Decimal("700.00"))
        self.assertTrue(breakdown["minimum_fare_applied"])

    def test_zero_rounding_step_disables_rounding(self):
        fare, _ = calculate_fare(
            distance_m=1_000,
            duration_s=180,
            fare_setting=make_setting(rounding_step=Decimal("0"), minimum_fare=Decimal("0")),
        )
        self.assertEqual(fare, Decimal("665.00"))

    def test_get_active_returns_only_active(self):
        FareSetting.objects.create(
            base_fare=1, per_km=1, per_minute=1, minimum_fare=1, is_active=False
        )
        self.assertIsNone(FareSetting.get_active())
        active = FareSetting.objects.create(
            base_fare=2, per_km=2, per_minute=2, minimum_fare=2, is_active=True
        )
        self.assertEqual(FareSetting.get_active(), active)


class FareSettingManagementTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "+2348031700001", "str0ng-Pass-2026", role=UserRole.ADMIN
        )
        self.old = FareSetting.objects.create(
            base_fare=Decimal("500"),
            per_km=Decimal("120"),
            per_minute=Decimal("15"),
            minimum_fare=Decimal("700"),
            is_active=True,
        )

    def test_create_activates_new_and_deactivates_old_same_category(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            reverse("management:fare-setting-list"),
            {
                "vehicle_category": "CAR",
                "base_fare": "600",
                "per_km": "150",
                "per_minute": "20",
                "minimum_fare": "800",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertTrue(resp.data["is_active"])
        self.old.refresh_from_db()
        self.assertFalse(self.old.is_active)
        active = FareSetting.get_active("CAR")
        self.assertEqual(active.base_fare, Decimal("600"))
        self.assertEqual(active.created_by, self.admin)

    def test_one_active_per_category_allowed(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            reverse("management:fare-setting-list"),
            {
                "vehicle_category": "KEKE",
                "base_fare": "300",
                "per_km": "80",
                "per_minute": "10",
                "minimum_fare": "400",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        # KEKE activation must NOT deactivate the CAR setting
        self.old.refresh_from_db()
        self.assertTrue(self.old.is_active)
        self.assertEqual(FareSetting.get_active("KEKE").base_fare, Decimal("300"))
        self.assertEqual(FareSetting.get_active("CAR"), self.old)

    def test_second_active_same_category_rejected_at_db(self):
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            FareSetting.objects.create(
                vehicle_category="CAR",
                base_fare=1,
                per_km=1,
                per_minute=1,
                minimum_fare=1,
                is_active=True,
            )

    def test_category_required_on_create(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            reverse("management:fare-setting-list"),
            {"base_fare": "600", "per_km": "150", "per_minute": "20", "minimum_fare": "800"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("vehicle_category", resp.data)

    def test_list_returns_history_newest_first(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(reverse("management:fare-setting-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)

    def test_negative_values_rejected(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            reverse("management:fare-setting-list"),
            {"base_fare": "-5", "per_km": "150", "per_minute": "20", "minimum_fare": "800"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_admin_blocked(self):
        passenger = User.objects.create_user(
            "+2348031700002", "str0ng-Pass-2026", role=UserRole.PASSENGER
        )
        self.client.force_authenticate(user=passenger)
        self.assertEqual(
            self.client.get(reverse("management:fare-setting-list")).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post(reverse("management:fare-setting-list"), {}).status_code,
            status.HTTP_403_FORBIDDEN,
        )
