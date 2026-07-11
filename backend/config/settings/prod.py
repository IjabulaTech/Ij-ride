"""Production settings: strict CORS, TLS-aware security headers, and a
channel layer that uses Redis when REDIS_URL is set (multi-instance) or the
built-in in-memory layer when it isn't (fine for a single free instance —
WebSockets still work in-process; the frontend polls as a fallback)."""
from .base import *  # noqa: F403
from .base import env

DEBUG = False
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

# REDIS_URL is optional. With it, ride events fan out across multiple web
# instances. Without it, a single instance uses the in-memory layer.
_REDIS_URL = env("REDIS_URL", default="")
if _REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [_REDIS_URL]},
        },
    }
else:
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# Render/Railway terminate TLS at their proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Persistent media: when CLOUDINARY_URL is present, driver/vehicle photos are
# stored on Cloudinary's CDN instead of Render's ephemeral disk (which wipes
# uploads on every deploy). Without it, we fall back to local disk served by
# config/urls.py. Get a free CLOUDINARY_URL at cloudinary.com and set it in the
# Render environment — no code change needed.
_CLOUDINARY_URL = env("CLOUDINARY_URL", default="")
USE_CLOUDINARY = bool(_CLOUDINARY_URL)
if USE_CLOUDINARY:
    INSTALLED_APPS += ["cloudinary_storage", "cloudinary"]  # noqa: F405
    STORAGES["default"] = {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"}
