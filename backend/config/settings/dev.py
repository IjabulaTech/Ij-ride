"""Development settings: permissive CORS, in-memory channel layer, ASGI runserver."""
import sys

from .base import *  # noqa: F403
from .base import INSTALLED_APPS

DEBUG = True
ALLOWED_HOSTS = ["*"]

# daphne must precede django.contrib.staticfiles so runserver speaks ASGI (HTTP + WS)
INSTALLED_APPS = ["daphne", *INSTALLED_APPS]

CORS_ALLOW_ALL_ORIGINS = True

# Serve static files from app dirs without collectstatic in dev
WHITENOISE_AUTOREFRESH = True
WHITENOISE_USE_FINDERS = True

# Fast (insecure) password hashing for the test suite only — never in prod,
# which uses config.settings.prod and is unaffected by this block.
if "test" in sys.argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    # Force the deterministic stub geo provider during tests, no matter what
    # GEO_PROVIDER/MAPBOX_ACCESS_TOKEN are set to locally. Tests must never
    # hit real Mapbox (billing + non-determinism + offline CI).
    GEO_PROVIDER = "stub"

CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}
