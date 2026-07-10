"""Admin-only ride records (mounted under /api/v1/management/)."""
from django.db.models import Q
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
        return qs


class RideAdminDetailView(generics.RetrieveAPIView):
    serializer_class = RideDetailSerializer
    permission_classes = [IsAdminRole]
    queryset = _ride_queryset()
