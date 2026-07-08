from django.apps import AppConfig


class RealtimeConfig(AppConfig):
    """Channels consumers and event broadcasting. No models — wired up in Module 8."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.realtime"
    label = "realtime"
