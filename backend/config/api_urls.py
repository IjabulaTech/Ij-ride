"""Central /api/v1/ route table. Each module registers its app URLs here.

Custom admin/staff endpoints will live under management/ — NOT admin/ —
to avoid clashing with Django's built-in admin site.
"""
from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.accounts.urls")),
    path("drivers/", include("apps.drivers.urls")),
    path("management/", include("config.management_urls")),
    path("rides/", include("apps.rides.urls")),
    path("geo/", include("apps.geo.urls")),
]
