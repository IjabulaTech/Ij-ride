"""Maintenance-mode state, cached so the middleware costs ~nothing per request.

Reads are served from cache for CACHE_TTL seconds; toggling clears the cache so
the switch takes effect immediately rather than after the TTL.
"""
from django.conf import settings
from django.core.cache import cache

from .models import DEFAULT_MESSAGE, MaintenanceMode

CACHE_KEY = "ops.maintenance.state"
CACHE_TTL = 10  # seconds


def _env_forced() -> bool:
    """MAINTENANCE_MODE=true forces maintenance on regardless of the database —
    a fail-safe for when the admin UI or DB is unavailable."""
    return bool(getattr(settings, "MAINTENANCE_MODE", False))


def get_state(*, refresh: bool = False) -> dict:
    """{"active": bool, "message": str} — safe to call on every request."""
    if not refresh:
        cached = cache.get(CACHE_KEY)
        if cached is not None:
            # The env switch must win even over a cached "off"
            if _env_forced() and not cached["active"]:
                return {"active": True, "message": cached["message"] or DEFAULT_MESSAGE}
            return cached
    try:
        row = MaintenanceMode.get_solo()
        state = {
            "active": bool(row.is_active),
            "message": row.message or DEFAULT_MESSAGE,
        }
    except Exception:
        # Never let a DB hiccup take the API down; assume "not in maintenance"
        state = {"active": False, "message": DEFAULT_MESSAGE}
    cache.set(CACHE_KEY, state, CACHE_TTL)
    if _env_forced() and not state["active"]:
        return {"active": True, "message": state["message"]}
    return state


def set_state(*, active: bool, message: str = "", admin_user=None) -> dict:
    row = MaintenanceMode.get_solo()
    row.is_active = active
    if message.strip():
        row.message = message.strip()
    row.updated_by = admin_user
    row.save()
    cache.delete(CACHE_KEY)
    return get_state(refresh=True)
