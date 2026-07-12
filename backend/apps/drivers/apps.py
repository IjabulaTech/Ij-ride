from django.apps import AppConfig


class DriversConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.drivers"
    label = "drivers"

    def ready(self):
        # If pillow-heif is available, teach Pillow to open iPhone HEIC/HEIF
        # photos too. It's an OPTIONAL extra (not in requirements, since its
        # wheel doesn't build everywhere) — iOS Safari already converts HEIC to
        # JPEG for web uploads, so standard formats cover real-world use.
        try:
            from pillow_heif import register_heif_opener

            register_heif_opener()
        except Exception:
            pass
