"""One-time-code generation, hashing, and delivery.

Delivery uses a small provider abstraction (mirrors apps/geo): `console`
logs the code (dev / pilot without SMS) and `termii` sends a real SMS.
Select with the OTP_PROVIDER env var. The code is never returned in an API
response — only delivered out-of-band — so requesting a reset for someone
else's phone leaks nothing.
"""
import hashlib
import logging
import secrets
from abc import ABC, abstractmethod
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("ijride.otp")

CODE_LENGTH = 6
MAX_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60


def generate_code() -> str:
    """A zero-padded numeric code, e.g. '048213'."""
    return f"{secrets.randbelow(10 ** CODE_LENGTH):0{CODE_LENGTH}d}"


def hash_code(code: str) -> str:
    # Peppered with SECRET_KEY so a DB leak alone doesn't expose live codes.
    return hashlib.sha256(f"{code}:{settings.SECRET_KEY}".encode()).hexdigest()


def code_matches(code: str, code_hash: str) -> bool:
    return secrets.compare_digest(hash_code(code), code_hash)


def expiry() -> "timezone.datetime":
    return timezone.now() + timedelta(minutes=settings.OTP_CODE_TTL_MINUTES)


# ---------------------------------------------------------------------------
# Delivery providers
# ---------------------------------------------------------------------------


class OTPSender(ABC):
    @abstractmethod
    def send(self, phone: str, code: str) -> None:
        """Deliver the code. Must not raise on ordinary delivery failure —
        log it; the reset flow should not reveal delivery problems."""


class ConsoleOTPSender(OTPSender):
    def send(self, phone: str, code: str) -> None:
        logger.info("IJ Ride password reset code for %s: %s", phone, code)


class TermiiOTPSender(OTPSender):
    """Termii SMS (https://termii.com) — common SMS gateway in Nigeria."""

    def send(self, phone: str, code: str) -> None:
        if not settings.TERMII_API_KEY:
            logger.error("TERMII_API_KEY not set; cannot send OTP SMS to %s", phone)
            return
        payload = {
            "api_key": settings.TERMII_API_KEY,
            "to": phone.lstrip("+"),
            "from": settings.TERMII_SENDER_ID,
            "sms": (
                f"Your IJ Ride password reset code is {code}. "
                f"It expires in {settings.OTP_CODE_TTL_MINUTES} minutes."
            ),
            "type": "plain",
            "channel": "generic",
        }
        try:
            resp = requests.post(
                f"{settings.TERMII_BASE_URL.rstrip('/')}/api/sms/send",
                json=payload,
                timeout=10,
            )
            if resp.status_code >= 400:
                logger.error("Termii SMS failed (%s): %s", resp.status_code, resp.text[:300])
        except requests.RequestException:
            logger.exception("Termii SMS request error for %s", phone)


def get_sender() -> OTPSender:
    provider = settings.OTP_PROVIDER.lower()
    if provider == "termii":
        return TermiiOTPSender()
    return ConsoleOTPSender()


def send_code(phone: str, code: str) -> None:
    get_sender().send(phone, code)
