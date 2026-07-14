"""Base settings shared by all environments. Env-specific values come from .env."""
from datetime import timedelta
from pathlib import Path

import environ

# backend/ directory (three levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
    DEFAULT_COUNTRY_CODE=(str, "+234"),
    JWT_ACCESS_MINUTES=(int, 60),
    JWT_REFRESH_DAYS=(int, 30),
    GEO_PROVIDER=(str, "stub"),
    MAPBOX_ACCESS_TOKEN=(str, ""),
    # Google Maps place search (GEO_PROVIDER=google) — best Nigeria POI coverage.
    # Needs "Places API (New)" + "Geocoding API" enabled on the key.
    GOOGLE_MAPS_API_KEY=(str, ""),
    # OSM place search (GEO_PROVIDER=osm). Photon's public instance by default;
    # point at a self-hosted or commercial instance for higher volume.
    GEO_OSM_BASE_URL=(str, "https://photon.komoot.io"),
    GEO_COUNTRY=(str, "NG"),
    GEO_PROXIMITY=(str, "12.4954,9.2035"),  # lng,lat bias center (Yola, Adamawa)
    RIDE_SEARCH_TIMEOUT_MINUTES=(int, 10),
    PUBLIC_BASE_URL=(str, "http://127.0.0.1:8000"),
    # Password-reset OTP delivery: "console" logs the code; "termii" sends SMS
    OTP_PROVIDER=(str, "console"),
    OTP_CODE_TTL_MINUTES=(int, 10),
    TERMII_API_KEY=(str, ""),
    TERMII_SENDER_ID=(str, "IJ Ride"),
    TERMII_BASE_URL=(str, "https://api.ng.termii.com"),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "channels",
    # IJ Ride apps
    "apps.accounts",
    "apps.drivers",
    "apps.rides",
    "apps.payments",
    "apps.pricing",
    "apps.commissions",
    "apps.geo",
    "apps.realtime",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": env.db_url("DATABASE_URL")}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Vehicle photos and other uploads. Local disk by default; when CLOUDINARY_URL
# is configured (prod), uploads go to Cloudinary's CDN and persist across
# deploys (Render's own disk is ephemeral). prod.py flips USE_CLOUDINARY on.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
USE_CLOUDINARY = False

# Absolute base used to build media URLs in payloads that have no request
# context (WebSocket broadcasts) — the frontend runs on a different origin.
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Local phone numbers starting with 0 are normalized to this country code (E.164)
DEFAULT_COUNTRY_CODE = env("DEFAULT_COUNTRY_CODE")

# Geo provider: "stub" (dev, no keys), "google" (best Nigeria POI coverage,
# needs GOOGLE_MAPS_API_KEY + billing), "osm" (OpenStreetMap/Photon, keyless),
# or "mapbox" (requires MAPBOX_ACCESS_TOKEN).
GEO_PROVIDER = env("GEO_PROVIDER")
MAPBOX_ACCESS_TOKEN = env("MAPBOX_ACCESS_TOKEN")
GOOGLE_MAPS_API_KEY = env("GOOGLE_MAPS_API_KEY")
GEO_OSM_BASE_URL = env("GEO_OSM_BASE_URL")
GEO_COUNTRY = env("GEO_COUNTRY")
GEO_PROXIMITY = env("GEO_PROXIMITY")

# A SEARCHING ride nobody accepts within this window becomes EXPIRED
RIDE_SEARCH_TIMEOUT_MINUTES = env("RIDE_SEARCH_TIMEOUT_MINUTES")

# Password-reset OTP delivery
OTP_PROVIDER = env("OTP_PROVIDER")
OTP_CODE_TTL_MINUTES = env("OTP_CODE_TTL_MINUTES")
TERMII_API_KEY = env("TERMII_API_KEY")
TERMII_SENDER_ID = env("TERMII_SENDER_ID")
TERMII_BASE_URL = env("TERMII_BASE_URL")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # Applied via ScopedRateThrottle on the anonymous auth endpoints
    "DEFAULT_THROTTLE_RATES": {"auth": "30/min"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("JWT_ACCESS_MINUTES")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_DAYS")),
    "UPDATE_LAST_LOGIN": True,
}
