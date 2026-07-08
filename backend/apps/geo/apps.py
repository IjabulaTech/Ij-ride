from django.apps import AppConfig


class GeoConfig(AppConfig):
    """Geocoding/routing provider abstraction. No models — services only (Module 5)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.geo"
    label = "geo"
