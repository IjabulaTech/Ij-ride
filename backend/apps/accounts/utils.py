import re

from django.conf import settings
from django.core.exceptions import ValidationError

E164_RE = re.compile(r"^\+\d{10,15}$")


def normalize_phone(raw: str) -> str:
    """Normalize a phone number to E.164.

    Accepts local format ('0803 123 4567' -> '+2348031234567' using
    DEFAULT_COUNTRY_CODE), international ('+2348031234567'), bare
    country-coded digits ('2348031234567') and '00'-prefixed numbers.
    """
    if not raw:
        raise ValidationError("Phone number is required.")
    cleaned = re.sub(r"[\s\-().]", "", raw.strip())
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if cleaned.startswith("0"):
        cleaned = settings.DEFAULT_COUNTRY_CODE + cleaned[1:]
    elif not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    if not E164_RE.match(cleaned):
        raise ValidationError(
            "Enter a valid phone number, e.g. 08031234567 or +2348031234567."
        )
    return cleaned
