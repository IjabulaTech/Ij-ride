"""Live customer-support chat: one thread per user, messages inside it.

Every passenger/driver gets a single ongoing conversation with the IJ Ride
support team (any admin). Unread counters are kept per side so the user sees a
badge for admin replies and admins see which threads need attention.
"""
from django.conf import settings
from django.db import models


class SupportThread(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_thread"
    )
    # Nulls sort last; set on every message so the admin inbox orders by activity
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_message_preview = models.CharField(max_length=140, blank=True, default="")
    unread_for_admin = models.PositiveIntegerField(default=0)
    unread_for_user = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_message_at", "-created_at"]

    def __str__(self):
        return f"Support thread for {self.user.phone}"


class SupportMessage(models.Model):
    thread = models.ForeignKey(
        SupportThread, on_delete=models.CASCADE, related_name="messages"
    )
    # Kept even if the admin account is later removed
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="support_messages",
    )
    # True when written by support staff — drives which side of the chat it sits on
    from_admin = models.BooleanField(default=False)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["thread", "created_at"])]

    def __str__(self):
        who = "support" if self.from_admin else "user"
        return f"[{who}] {self.body[:40]}"
