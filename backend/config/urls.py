from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config.views import health

urlpatterns = [
    path("admin/", admin.site.urls),  # Django built-in admin (staff back-office fallback)
    path("healthz/", health),
    path("api/v1/", include("config.api_urls")),
]

if settings.DEBUG:  # dev media serving; production uses the host/CDN
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
