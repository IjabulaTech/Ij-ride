"""Idempotent launch bootstrap, safe to run on every deploy.

Enables a turnkey deploy on hosts without shell access (e.g. Render's free
tier). Does two things, only when needed:

  1. Creates the admin superuser from DJANGO_SUPERUSER_PHONE /
     DJANGO_SUPERUSER_PASSWORD env vars (skips if that account exists).
  2. Seeds a default active KEKE and CAR fare so ride estimates work out of
     the box (skips any category that already has an active fare).

Change fares/commission anytime in Django admin — this never overwrites
existing active rows.
"""
import os
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.accounts.utils import normalize_phone
from apps.drivers.models import VehicleCategory
from apps.pricing.models import FareSetting

DEFAULT_FARES = {
    VehicleCategory.KEKE: {
        "base_fare": "300",
        "per_km": "80",
        "per_minute": "10",
        "minimum_fare": "400",
        "rounding_step": "50",
    },
    VehicleCategory.CAR: {
        "base_fare": "500",
        "per_km": "120",
        "per_minute": "15",
        "minimum_fare": "700",
        "rounding_step": "50",
    },
}


class Command(BaseCommand):
    help = "Idempotent launch bootstrap: admin superuser from env + default active fares."

    def handle(self, *args, **options):
        self._bootstrap_superuser()
        self._seed_fares()

    def _bootstrap_superuser(self):
        phone = os.environ.get("DJANGO_SUPERUSER_PHONE")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if not (phone and password):
            self.stdout.write("No DJANGO_SUPERUSER_PHONE/PASSWORD set — skipping admin bootstrap.")
            return
        phone_n = normalize_phone(phone)
        if User.objects.filter(phone=phone_n).exists():
            self.stdout.write(f"Admin {phone_n} already exists.")
            return
        User.objects.create_superuser(phone=phone_n, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created admin superuser {phone_n}."))

    def _seed_fares(self):
        for category, cfg in DEFAULT_FARES.items():
            if FareSetting.objects.filter(vehicle_category=category, is_active=True).exists():
                self.stdout.write(f"{category} already has an active fare — leaving it.")
                continue
            FareSetting.objects.create(
                vehicle_category=category,
                is_active=True,
                **{k: Decimal(v) for k, v in cfg.items()},
            )
            self.stdout.write(self.style.SUCCESS(f"Seeded default {category} fare."))
