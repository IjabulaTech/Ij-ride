from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsApprovedDriver, IsDriver

from . import services
from .models import DriverProfile
from .serializers import (
    AvailabilityUpdateSerializer,
    DriverAvailabilitySerializer,
    DriverProfileSerializer,
    LocationUpdateSerializer,
    VehicleSerializer,
)


def _my_profile(request) -> DriverProfile:
    return get_object_or_404(DriverProfile, user=request.user)


class MyDriverProfileView(generics.RetrieveUpdateAPIView):
    """GET/PUT/PATCH the driver's own profile (license details)."""

    serializer_class = DriverProfileSerializer
    permission_classes = [IsDriver]

    def get_object(self):
        return _my_profile(self.request)


class MyVehicleView(APIView):
    """The driver's single active vehicle: GET it, PUT to create or update."""

    permission_classes = [IsDriver]

    def get(self, request):
        vehicle = _my_profile(request).vehicles.filter(is_active=True).first()
        if vehicle is None:
            return Response(
                {"detail": "No vehicle registered yet."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(VehicleSerializer(vehicle, context={"request": request}).data)

    def put(self, request):
        profile = _my_profile(request)
        vehicle = profile.vehicles.filter(is_active=True).first()
        # multipart (photo upload) and JSON both supported by DRF's default parsers
        serializer = VehicleSerializer(
            instance=vehicle, data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        # V1 rule: vehicle category must match the driver's operating category
        services.enforce_driver_vehicle_category(
            profile, serializer.validated_data["category"]
        )
        created = vehicle is None
        serializer.save(driver=profile, is_active=True)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MyAvailabilityView(APIView):
    """GET current availability; POST {"is_online": bool} to toggle.
    Going online is gated on approval + registered vehicle."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsApprovedDriver()]
        return [IsDriver()]

    def get(self, request):
        return Response(DriverAvailabilitySerializer(_my_profile(request).availability).data)

    def post(self, request):
        serializer = AvailabilityUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        availability = services.set_availability(
            _my_profile(request), is_online=serializer.validated_data["is_online"]
        )
        return Response(DriverAvailabilitySerializer(availability).data)


class MyLocationView(APIView):
    """POST {"lat": ..., "lng": ...} — periodic location ping while online.

    The driver app normally streams fixes over the WebSocket; this HTTP path is
    the fallback when the socket is down, so it broadcasts live tracking too.
    """

    permission_classes = [IsApprovedDriver]

    def post(self, request):
        from apps.rides.tracking import record_driver_location

        serializer = LocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record_driver_location(request.user, **serializer.validated_data)
        availability = _my_profile(request).availability
        availability.refresh_from_db()
        return Response(DriverAvailabilitySerializer(availability).data)


class MyEarningsView(APIView):
    """Completed-trip earnings summary: today / last 7 days / all time."""

    permission_classes = [IsDriver]

    def get(self, request):
        from apps.payments.services import earnings_summary

        return Response(earnings_summary(request.user))
