from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from apps.accounts.services import register_passenger
from apps.rides.constants import RideEventType
from apps.rides.models import Ride, RideEvent
from apps.rides.tests import PASSWORD, RideTestCase, make_ready_driver

from .constants import PaymentMethod, PaymentStatus
from .models import Payment


class PaymentTestCase(RideTestCase):
    def ride_at(self, stage: str, method: str = PaymentMethod.TRANSFER) -> int:
        """Create a ride and progress it to the given stage."""
        ride = self.request_ride(payment_method=method)
        steps = {"accepted": 1, "arrived": 2, "in_progress": 3, "completed": 4}[stage]
        for action in ["accept", "arrived", "start", "complete"][:steps]:
            resp = self.act(self.driver, ride["id"], action)
            assert resp.status_code == status.HTTP_200_OK, resp.data
        return ride["id"]

    def claim(self, ride_id, user=None, reference=""):
        self.login(user or self.passenger)
        return self.client.post(
            reverse("rides:payment-claim", args=[ride_id]), {"reference": reference}
        )

    def confirm(self, ride_id, user=None):
        self.login(user or self.driver)
        return self.client.post(reverse("rides:payment-confirm", args=[ride_id]), {})


class ClaimPaymentTests(PaymentTestCase):
    def test_passenger_claims_transfer_after_completion(self):
        ride_id = self.ride_at("completed")
        resp = self.claim(ride_id, reference="GTB-2026-0001")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["payment"]["status"], PaymentStatus.CLAIMED)
        self.assertEqual(resp.data["payment"]["reference"], "GTB-2026-0001")
        self.assertIsNotNone(resp.data["payment"]["claimed_at"])

        payment = Payment.objects.get(ride_id=ride_id)
        self.assertEqual(payment.claimed_by, self.passenger)
        self.assertTrue(
            RideEvent.objects.filter(
                ride_id=ride_id, event_type=RideEventType.PAYMENT_CLAIMED
            ).exists()
        )

    def test_claim_allowed_during_trip(self):
        ride_id = self.ride_at("in_progress")
        resp = self.claim(ride_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["payment"]["status"], PaymentStatus.CLAIMED)

    def test_claim_rejected_before_trip_starts(self):
        ride_id = self.ride_at("arrived")
        resp = self.claim(ride_id)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cash_payment_cannot_be_claimed(self):
        ride_id = self.ride_at("completed", method=PaymentMethod.CASH)
        resp = self.claim(ride_id)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("transfer", str(resp.data).lower())

    def test_other_passenger_cannot_claim(self):
        ride_id = self.ride_at("completed")
        stranger = register_passenger(phone="+2348031500001", password=PASSWORD)
        resp = self.claim(ride_id, user=stranger)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_reclaim_updates_reference(self):
        ride_id = self.ride_at("completed")
        self.claim(ride_id, reference="WRONG-REF")
        resp = self.claim(ride_id, reference="RIGHT-REF")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["payment"]["reference"], "RIGHT-REF")


class ConfirmPaymentTests(PaymentTestCase):
    def test_driver_confirms_cash(self):
        ride_id = self.ride_at("completed", method=PaymentMethod.CASH)
        resp = self.confirm(ride_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["payment"]["status"], PaymentStatus.PAID)
        payment = Payment.objects.get(ride_id=ride_id)
        self.assertEqual(payment.confirmed_by, self.driver)
        self.assertEqual(payment.amount, Ride.objects.get(pk=ride_id).final_fare)

    def test_driver_confirms_claimed_transfer(self):
        ride_id = self.ride_at("completed")
        self.claim(ride_id, reference="GTB-REF")
        resp = self.confirm(ride_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["payment"]["status"], PaymentStatus.PAID)
        self.assertTrue(
            RideEvent.objects.filter(
                ride_id=ride_id, event_type=RideEventType.PAYMENT_CONFIRMED
            ).exists()
        )

    def test_admin_can_confirm(self):
        ride_id = self.ride_at("completed")
        resp = self.confirm(ride_id, user=self.admin)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["payment"]["status"], PaymentStatus.PAID)

    def test_confirm_rejected_before_completion(self):
        ride_id = self.ride_at("in_progress")
        resp = self.confirm(ride_id)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unassigned_driver_cannot_confirm(self):
        ride_id = self.ride_at("completed")
        other = make_ready_driver("+2348031500002", "PAY111AA")
        resp = self.confirm(ride_id, user=other)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_double_confirm_rejected(self):
        ride_id = self.ride_at("completed")
        self.confirm(ride_id)
        resp = self.confirm(ride_id)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already", str(resp.data))


class EarningsTests(PaymentTestCase):
    def test_earnings_summary(self):
        first = self.ride_at("completed", method=PaymentMethod.CASH)
        self.confirm(first)  # PAID
        second = self.ride_at("completed")  # completed, unpaid
        fare = Ride.objects.get(pk=first).final_fare
        fare2 = Ride.objects.get(pk=second).final_fare

        self.login(self.driver)
        resp = self.client.get(reverse("drivers:my-earnings"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        all_time = resp.data["all_time"]
        self.assertEqual(all_time["trips"], 2)
        self.assertEqual(Decimal(all_time["gross"]), fare + fare2)
        self.assertEqual(Decimal(all_time["paid"]), fare)
        self.assertEqual(Decimal(all_time["unpaid"]), fare2)
        # both trips completed just now -> today matches all-time
        self.assertEqual(resp.data["today"], all_time)
        self.assertEqual(resp.data["currency"], "NGN")

    def test_earnings_requires_driver_role(self):
        self.login(self.passenger)
        resp = self.client.get(reverse("drivers:my-earnings"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class PaymentManagementTests(PaymentTestCase):
    def test_admin_lists_payments_with_filters(self):
        cash_ride = self.ride_at("completed", method=PaymentMethod.CASH)
        self.confirm(cash_ride)
        transfer_ride = self.ride_at("completed")
        self.claim(transfer_ride, reference="GTB-XYZ")

        self.login(self.admin)
        resp = self.client.get(reverse("management:payment-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 2)

        resp = self.client.get(reverse("management:payment-list"), {"status": "claimed"})
        self.assertEqual([p["ride_id"] for p in resp.data["results"]], [transfer_ride])

        resp = self.client.get(reverse("management:payment-list"), {"method": "cash"})
        self.assertEqual([p["ride_id"] for p in resp.data["results"]], [cash_ride])

        resp = self.client.get(reverse("management:payment-list"), {"search": "GTB-XYZ"})
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(resp.data["results"][0]["reference"], "GTB-XYZ")

    def test_non_admin_blocked(self):
        self.login(self.driver)
        resp = self.client.get(reverse("management:payment-list"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
