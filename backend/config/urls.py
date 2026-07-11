from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from config.views import health

urlpatterns = [
    path("admin/", admin.site.urls),  # Django built-in admin (staff back-office fallback)
    path("healthz/", health),
    path("api/v1/", include("config.api_urls")),
]

# Serve user uploads (driver/vehicle photos) directly from Django.
# When CLOUDINARY_URL is set (see settings/prod.py) uploads live on Cloudinary's
# CDN and their URLs bypass this route entirely, so this stays as the fallback
# for local disk in every environment — including production without Cloudinary.
if not settings.USE_CLOUDINARY:
    media_prefix = settings.MEDIA_URL.lstrip("/")
    urlpatterns += [
        re_path(rf"^{media_prefix}(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
