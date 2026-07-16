"""Pluggable NIN verification.

V1 uses a stub: it validates the 11-digit format only, and an admin confirms
identity manually. NIMC has no public API — automated verification requires a
licensed aggregator (Dojah, Smile ID, VerifyMe, Prembly/IdentityPass, QoreID,
YouVerify…), which needs a paid account and business KYC. When one is
configured, drop in a provider that does the real NIMC lookup + face/liveness
match here — callers won't change (same pattern as the geo providers).

Select via the NIN_PROVIDER setting (default "stub").
"""
import re
from dataclasses import dataclass

from django.conf import settings

NIN_RE = re.compile(r"^\d{11}$")


@dataclass(frozen=True)
class NinCheck:
    ok: bool
    detail: str = ""


def valid_format(nin: str) -> bool:
    return bool(NIN_RE.match(nin or ""))


class NinProvider:
    def verify(self, nin: str, *, first_name: str = "", last_name: str = "") -> NinCheck:
        raise NotImplementedError


class StubNinProvider(NinProvider):
    """No external call — validates the 11-digit format only. Real identity
    confirmation is done manually by an admin in V1."""

    def verify(self, nin, *, first_name="", last_name=""):
        if not valid_format(nin):
            return NinCheck(False, "NIN must be exactly 11 digits.")
        return NinCheck(True, "Format valid — pending manual review.")


def get_nin_provider() -> NinProvider:
    name = getattr(settings, "NIN_PROVIDER", "stub").lower()
    if name == "stub":
        return StubNinProvider()
    raise ValueError(f"Unknown NIN_PROVIDER '{name}'. Expected 'stub'.")
