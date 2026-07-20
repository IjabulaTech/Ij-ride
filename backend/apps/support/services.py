"""Support-chat business rules: thread lookup, posting, read receipts.

Posting a message updates the thread's activity fields and the unread counter
for the *other* side, then broadcasts over the WebSocket so both the user and
any signed-in admin see it live.
"""
from django.db import transaction
from django.utils import timezone

from apps.realtime.events import broadcast_support_message

from .models import SupportMessage, SupportThread

PREVIEW_LEN = 140


def get_or_create_thread(user) -> SupportThread:
    thread, _ = SupportThread.objects.get_or_create(user=user)
    return thread


@transaction.atomic
def post_message(*, thread: SupportThread, sender, body: str, from_admin: bool) -> SupportMessage:
    message = SupportMessage.objects.create(
        thread=thread, sender=sender, body=body, from_admin=from_admin
    )
    thread.last_message_at = message.created_at or timezone.now()
    thread.last_message_preview = body[:PREVIEW_LEN]
    # The side that didn't write it gains an unread
    if from_admin:
        thread.unread_for_user += 1
    else:
        thread.unread_for_admin += 1
    thread.save(
        update_fields=[
            "last_message_at",
            "last_message_preview",
            "unread_for_user",
            "unread_for_admin",
            "updated_at",
        ]
    )
    broadcast_support_message(message)
    return message


def mark_read(thread: SupportThread, *, for_admin: bool) -> None:
    field = "unread_for_admin" if for_admin else "unread_for_user"
    if getattr(thread, field) == 0:
        return
    setattr(thread, field, 0)
    thread.save(update_fields=[field, "updated_at"])
