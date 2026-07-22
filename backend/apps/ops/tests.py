from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole

from .models import MaintenanceMode
from .services import get_state, set_state

PASSWORD = "str0ng-Pass-2026"


class MaintenanceModeTests(APITestCase):
    def setUp(self):
        cache.clear()
        MaintenanceMode.objects.all().delete()
        self.rider = User.objects.create_user(phone="+2348031160001", password=PASSWORD)
        self.admin = User.objects.create_user(
            phone="+2348031160099", password=PASSWORD, role=UserRole.ADMIN
        )

    def tearDown(self):
        cache.clear()

    # ---- state ----
    def test_defaults_to_off(self):
        self.assertFalse(get_state(refresh=True)["active"])

    def test_get_solo_always_returns_the_one_row(self):
        first = MaintenanceMode.get_solo()
        first.is_active = True
        first.save()
        second = MaintenanceMode.get_solo()
        self.assertEqual(first.pk, second.pk)
        self.assertTrue(second.is_active)
        self.assertEqual(MaintenanceMode.objects.count(), 1)

    # ---- public status endpoint ----
    def test_status_endpoint_is_public(self):
        resp = self.client.get(reverse("ops:status"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["maintenance"])

    def test_status_reflects_toggle(self):
        set_state(active=True, message="Back at 6pm", admin_user=self.admin)
        resp = self.client.get(reverse("ops:status"))
        self.assertTrue(resp.data["maintenance"])
        self.assertEqual(resp.data["message"], "Back at 6pm")

    # ---- blocking behaviour ----
    def test_rider_api_blocked_with_503(self):
        set_state(active=True, admin_user=self.admin)
        self.client.force_authenticate(self.rider)
        resp = self.client.get(reverse("geo:suggest"), {"q": "Jimeta"})
        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertTrue(resp.json()["maintenance"])

    def test_rider_api_works_when_off(self):
        self.client.force_authenticate(self.rider)
        resp = self.client.get(reverse("geo:suggest"), {"q": "Jimeta"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_healthz_still_ok_during_maintenance(self):
        set_state(active=True, admin_user=self.admin)
        resp = self.client.get("/healthz/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_login_still_works_during_maintenance(self):
        """An admin must be able to sign in to turn it back off."""
        set_state(active=True, admin_user=self.admin)
        resp = self.client.post(
            reverse("accounts:token"), {"phone": "+2348031160099", "password": PASSWORD}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

    def test_admin_api_reachable_during_maintenance(self):
        set_state(active=True, admin_user=self.admin)
        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse("management:user-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # ---- admin switch ----
    def test_admin_turns_it_on_and_off(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            reverse("management:maintenance"), {"active": True, "message": "Upgrading fares"}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertTrue(resp.data["maintenance"])
        self.assertEqual(resp.data["message"], "Upgrading fares")

        # ...and the rider is blocked immediately (cache is invalidated)
        self.client.force_authenticate(self.rider)
        blocked = self.client.get(reverse("geo:suggest"), {"q": "Jimeta"})
        self.assertEqual(blocked.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

        self.client.force_authenticate(self.admin)
        resp = self.client.post(reverse("management:maintenance"), {"active": False})
        self.assertFalse(resp.data["maintenance"])
        self.client.force_authenticate(self.rider)
        ok = self.client.get(reverse("geo:suggest"), {"q": "Jimeta"})
        self.assertEqual(ok.status_code, status.HTTP_200_OK)

    def test_toggle_keeps_previous_message_when_blank(self):
        set_state(active=True, message="Original", admin_user=self.admin)
        self.client.force_authenticate(self.admin)
        resp = self.client.post(reverse("management:maintenance"), {"active": True})
        self.assertEqual(resp.data["message"], "Original")

    def test_non_admin_cannot_toggle(self):
        self.client.force_authenticate(self.rider)
        resp = self.client.post(reverse("management:maintenance"), {"active": True})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_toggle(self):
        resp = self.client.post(reverse("management:maintenance"), {"active": True})
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    # ---- env fail-safe ----
    @override_settings(MAINTENANCE_MODE=True)
    def test_env_var_forces_maintenance_on(self):
        cache.clear()
        self.assertTrue(get_state(refresh=True)["active"])
        self.client.force_authenticate(self.rider)
        resp = self.client.get(reverse("geo:suggest"), {"q": "Jimeta"})
        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
