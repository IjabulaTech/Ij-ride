from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole

from .models import SupportMessage, SupportThread

PASSWORD = "str0ng-Pass-2026"


class SupportChatTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(phone="+2348031150001", password=PASSWORD)
        self.other = User.objects.create_user(phone="+2348031150002", password=PASSWORD)
        self.admin = User.objects.create_user(
            phone="+2348031150099", password=PASSWORD, role=UserRole.ADMIN
        )

    # ---- user side ----
    def test_thread_created_on_first_read(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("support:my-messages"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["results"], [])
        self.assertTrue(SupportThread.objects.filter(user=self.user).exists())

    def test_user_sends_message(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post(reverse("support:my-messages"), {"body": "My driver never came"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertFalse(resp.data["from_admin"])
        thread = SupportThread.objects.get(user=self.user)
        self.assertEqual(thread.unread_for_admin, 1)
        self.assertEqual(thread.last_message_preview, "My driver never came")

    def test_empty_message_rejected(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post(reverse("support:my-messages"), {"body": "   "})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_support_requires_auth(self):
        resp = self.client.get(reverse("support:my-messages"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_only_sees_own_thread(self):
        self.client.force_authenticate(self.user)
        self.client.post(reverse("support:my-messages"), {"body": "mine"})
        self.client.force_authenticate(self.other)
        resp = self.client.get(reverse("support:my-messages"))
        self.assertEqual(resp.data["results"], [])

    # ---- admin side ----
    def test_admin_lists_threads_and_replies(self):
        self.client.force_authenticate(self.user)
        self.client.post(reverse("support:my-messages"), {"body": "help me"})
        thread = SupportThread.objects.get(user=self.user)

        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse("management:support-thread-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["results"][0]["unread_for_admin"], 1)

        # Opening the thread clears the admin unread badge
        resp = self.client.get(
            reverse("management:support-thread-messages", args=[thread.pk])
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(len(resp.data["results"]), 1)
        thread.refresh_from_db()
        self.assertEqual(thread.unread_for_admin, 0)

        # Replying marks unread for the user
        resp = self.client.post(
            reverse("management:support-thread-messages", args=[thread.pk]),
            {"body": "Sorry about that — we're on it."},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertTrue(resp.data["from_admin"])
        self.assertEqual(resp.data["sender_name"], "IJ Ride Support")
        thread.refresh_from_db()
        self.assertEqual(thread.unread_for_user, 1)

    def test_user_sees_admin_reply_and_read_clears(self):
        thread = SupportThread.objects.create(user=self.user)
        SupportMessage.objects.create(thread=thread, sender=self.admin, from_admin=True, body="hi")
        thread.unread_for_user = 1
        thread.save(update_fields=["unread_for_user"])

        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("support:my-messages"))
        self.assertEqual(len(resp.data["results"]), 1)
        thread.refresh_from_db()
        self.assertEqual(thread.unread_for_user, 0)

    def test_unread_filter(self):
        self.client.force_authenticate(self.user)
        self.client.post(reverse("support:my-messages"), {"body": "waiting"})
        SupportThread.objects.create(user=self.other)  # no messages -> not unread

        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse("management:support-thread-list"), {"unread": "true"})
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(resp.data["results"][0]["phone"], self.user.phone)

    def test_non_admin_cannot_use_admin_inbox(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("management:support-thread-list"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_reply_to_missing_thread_404s(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            reverse("management:support-thread-messages", args=[99999]), {"body": "x"}
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
