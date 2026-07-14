"""Admin-only ride records (mounted under /api/v1/management/)."""
from datetime import datetime, time, timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import generics

from apps.accounts.permissions import IsAdminRole

from .models import Ride
from .serializers import RideDetailSerializer


def _ride_queryset():
    return Ride.objects.select_related(
        "passenger", "driver", "driver__driver_profile", "vehicle", "payment"
    ).order_by(
        "-created_at"
    )


def _parse_date(value):
    """Parse a YYYY-MM-DD query param into a date, or None if absent/invalid."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


class RideAdminListView(generics.ListAPIView):
    serializer_class = RideDetailSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        qs = _ride_queryset()
        ride_status = self.request.query_params.get("status")
        if ride_status:
            qs = qs.filter(status=ride_status.upper())
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(passenger__phone__icontains=search)
                | Q(driver__phone__icontains=search)
                | Q(pickup_address__icontains=search)
                | Q(dropoff_address__icontains=search)
            )
        # Filter by calendar day (inclusive) in the app's local timezone, so
        # "1 July" means a Yola day, not a UTC one. Either bound is optional.
        tz = timezone.get_current_timezone()
        date_from = _parse_date(self.request.query_params.get("date_from"))
        if date_from:
            start = timezone.make_aware(datetime.combine(date_from, time.min), tz)
            qs = qs.filter(created_at__gte=start)
        date_to = _parse_date(self.request.query_params.get("date_to"))
        if date_to:
            end = timezone.make_aware(datetime.combine(date_to + timedelta(days=1), time.min), tz)
            qs = qs.filter(created_at__lt=end)
        return qs


class RideAdminDetailView(generics.RetrieveAPIView):
    serializer_class = RideDetailSerializer
    permission_classes = [IsAdminRole]
    queryset = _ride_queryset()
