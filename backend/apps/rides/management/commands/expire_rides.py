"""Expire SEARCHING rides older than RIDE_SEARCH_TIMEOUT_MINUTES.

Run periodically in production (cron / Render cron job):
    python manage.py expire_rides
The API also expires stale rides opportunistically, so this is a sweeper,
not the only line of defense.
"""
from django.core.management.base import BaseCommand

from apps.rides.services import expire_stale_rides


class Command(BaseCommand):
    help = "Mark overdue SEARCHING rides as EXPIRED."

    def handle(self, *args, **options):
        count = expire_stale_rides()
        self.stdout.write(self.style.SUCCESS(f"Expired {count} stale ride(s)."))
