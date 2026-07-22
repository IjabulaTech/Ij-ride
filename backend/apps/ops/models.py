"""Operational switches. Currently: maintenance mode.

A single row (pk=1) holds the flag so it can be flipped instantly from the
admin UI — no redeploy. The MAINTENANCE_MODE env var can force it on as a
fail-safe when the admin UI or database isn't reachable.
"""
from django.conf import settings
from django.db import models

DEFAULT_MESSAGE = (
    "IJ Ride is down for scheduled maintenance. We'll be back shortly — "
    "thank you for your patience."
)


class MaintenanceMode(models.Model):
    """Singleton; always read/written through get_solo()."""

    is_active = models.BooleanField(default=False)
    message = models.TextField(blank=True, default=DEFAULT_MESSAGE)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="maintenance_changes",
    )

    class Meta:
        verbose_name = "maintenance mode"
        verbose_name_plural = "maintenance mode"

    def __str__(self):
        return f"Maintenance mode: {'ON' if self.is_active else 'off'}"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce the singleton
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> "MaintenanceMode":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
