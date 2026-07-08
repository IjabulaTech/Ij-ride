from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status

from apps.rides.models import Ride
from apps.rides.tests import RideTestCase

from .models import CommissionType, PlatformCommissionSetting, RemittanceStatus, RideCommission
from .services import compute_commission


def make_setting(**overrides) -> PlatformCommissionSetting:
    defaults = dict(
        commission_type=CommissionType.PERCENTAGE,
        commission_value=Decimal("15"),
        is_active=True,
    )
    defaults.update(overrides)
    return PlatformCommissionSetting.objects.create(**defaults)


class CommissionMathTests(RideTestCase):
    def _setting(self, ctype, value):
        return PlatformCommissionSetting(commission_type=ctype, commission_value=Decimal(value))

    def test_percentage(self):
        s = self._setting(CommissionType.PERCENTAGE, "15")
        self.assertEqual(compute_commission(Decimal("3300.00"), s), Decimal("495.00"))

    def test_percentage_rounding(self):
        s = self._setting(CommissionType.PERCENTAGE, "12.5")
        # 12.5% of 1015 = 126.875 -> 126.88 (half-up)
        self.assertEqual(compute_commission(Decimal("1015.00"), s), Decimal("126.88"))

    def test_fixed(self):
        s = self._setting(CommissionType.FIXED, "300")
        self.assertEqual(compute_commission(Decimal("3300.00"), s), Decimal("300.00"))

    def test_fixed_capped_at_fare(self):
        s = self._setting(CommissionType.FIXED, "1000")
        self.assertEqual(compute_commission(Decimal("700.00"), s), Decimal("700.00"))

    def test_single_active_constraint(self):
        make_setting()
        with self.assertRaises(IntegrityError):
            make_setting()

    def test_percentage_over_100_rejected(self):
        setting = PlatformCommissionSetting(
            commission_type=CommissionType.PERCENTAGE, commission_value=Decimal("150")
        )
        with self.assertRaises(DjangoValidationError):
            setting.full_clean()


class CommissionRecordingTests(RideTestCase):
    def complete_ride(self) -> int:
        ride = self.request_ride()
        for action in ("accept", "arrived", "start", "complete"):
            resp = self.act(self.driver, ride["id"], action)
            assert resp.status_code == status.HTTP_200_OK, resp.data
        return ride["id"]

    def test_completion_creates_pending_commission(self):
        make_setting()  # 15%
        ride_id = self.complete_ride()
        record = RideCommission.objects.get(ride_id=ride_id)
        fare = Ride.objects.get(pk=ride_id).final_fare
        self.assertEqual(record.driver, self.driver)
        self.assertEqual(record.fare_amount, fare)
        self.assertEqual(record.commission_amount + record.driver_earning, fare)
        self.assertEqual(record.commission_amount, (fare * Decimal("15") / 100).quantize(Decimal("0.01")))
        self.assertEqual(record.status, RemittanceStatus.PENDING)
        self.assertIsNotNone(record.commission_setting)

    def test_no_active_setting_records_zero_auto_settled(self):
        ride_id = self.complete_ride()
        record = RideCommission.objects.get(ride_id=ride_id)
        self.assertEqual(record.commission_amount, Decimal("0.00"))
        self.assertEqual(record.driver_earning, record.fare_amount)
        self.assertEqual(record.status, RemittanceStatus.REMITTED)

    def test_earnings_include_commission_and_outstanding(self):
        make_setting()
        self.complete_ride()
        self.login(self.driver)
        resp = self.client.get(reverse("drivers:my-earnings"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        all_time = resp.data["all_time"]
        gross = Decimal(all_time["gross"])
        commission = Decimal(all_time["commission"])
        self.assertGreater(commission, 0)
        self.assertEqual(Decimal(all_time["net"]), gross - commission)
        self.assertEqual(Decimal(resp.data["outstanding_commission"]), commission)


class RemittanceApiTests(RideTestCase):
    def setUp(self):
        super().setUp()
        make_setting()

    def complete_ride(self) -> RideCommission:
        ride = self.request_ride()
        for action in ("accept", "arrived", "start", "complete"):
            self.act(self.driver, ride["id"], action)
        return RideCommission.objects.get(ride_id=ride["id"])

    def test_admin_marks_single_commission_remitted(self):
        record = self.complete_ride()
        self.login(self.admin)
        resp = self.client.post(
            reverse("management:commission-remit", args=[record.pk]),
            {"note": "GTB transfer 001"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["status"], RemittanceStatus.REMITTED)
        self.assertEqual(resp.data["note"], "GTB transfer 001")
        # double remit rejected
        resp = self.client.post(reverse("management:commission-remit", args=[record.pk]), {})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_settle_driver_clears_all_pending(self):
        first = self.complete_ride()
        second = self.complete_ride()
        total = first.commission_amount + second.commission_amount

        self.login(self.admin)
        resp = self.client.post(
            reverse("management:commission-settle-driver"),
            {"driver_id": self.driver.pk, "note": "weekly settlement"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["settled_count"], 2)
        self.assertEqual(Decimal(resp.data["settled_amount"]), total)
        self.assertFalse(
            RideCommission.objects.filter(
                driver=self.driver, status=RemittanceStatus.PENDING
            ).exists()
        )
        # settling again -> nothing pending
        resp = self.client.post(
            reverse("management:commission-settle-driver"), {"driver_id": self.driver.pk}
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_summary_math_and_filters(self):
        first = self.complete_ride()
        second = self.complete_ride()
        self.login(self.admin)
        self.client.post(reverse("management:commission-remit", args=[first.pk]), {})

        resp = self.client.get(reverse("management:commission-summary"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        totals = resp.data["totals"]
        self.assertEqual(
            Decimal(totals["commission_total"]),
            first.commission_amount + second.commission_amount,
        )
        self.assertEqual(Decimal(totals["outstanding"]), second.commission_amount)
        self.assertEqual(Decimal(totals["remitted"]), first.commission_amount)
        owing = resp.data["drivers_owing"]
        self.assertEqual(len(owing), 1)
        self.assertEqual(owing[0]["driver_id"], self.driver.pk)
        self.assertEqual(owing[0]["pending_rides"], 1)

        resp = self.client.get(reverse("management:commission-list"), {"status": "pending"})
        self.assertEqual([c["id"] for c in resp.data["results"]], [second.pk])

    def test_non_admin_blocked(self):
        record = self.complete_ride()
        for user in (self.driver, self.passenger):
            self.login(user)
            self.assertEqual(
                self.client.get(reverse("management:commission-list")).status_code,
                status.HTTP_403_FORBIDDEN,
            )
            self.assertEqual(
                self.client.post(
                    reverse("management:commission-remit", args=[record.pk]), {}
                ).status_code,
                status.HTTP_403_FORBIDDEN,
            )
