from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsApprovedDriver, IsPassenger
from apps.geo.base import GeoServiceError

from . import services
from .constants import DRIVER_BUSY_STATUSES
from .models import Ride
from .serializers import (
    CancelRideSerializer,
    CreateRideSerializer,
    EstimateRequestSerializer,
    OpenRideSerializer,
    RideDetailSerializer,
    RideListSerializer,
    serialize_estimate,
)


class RideEstimateView(APIView):
    """POST pickup/dropoff (address text or coordinates) -> distance,
    duration, and fare quote. Any authenticated user may ask."""

    def post(self, request):
        serializer = EstimateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            estimate = services.estimate_ride(**serializer.validated_data)
        except GeoServiceError as exc:
            return Response({"detail": str(exc)}, status=exc.status_code)
        return Response(serialize_estimate(estimate))


class RideListCreateView(generics.ListCreateAPIView):
    """GET: the caller's ride history (terminal rides only).
    POST: request a ride (passengers only)."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsPassenger()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        return CreateRideSerializer if self.request.method == "POST" else RideListSerializer

    def get_queryset(self):
        return services.history_for(self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = CreateRideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ride = services.create_ride(passenger=request.user, **serializer.validated_data)
        except GeoServiceError as exc:
            return Response({"detail": str(exc)}, status=exc.status_code)
        return Response(RideDetailSerializer(ride).data, status=status.HTTP_201_CREATED)


class ActiveRideView(APIView):
    """The caller's current ride (passenger: any active status; driver:
    assigned trip). 404 when there is none — poll-friendly."""

    def get(self, request):
        ride = services.active_ride_for(request.user)
        if ride is None:
            return Response({"detail": "No active ride."}, status=status.HTTP_404_NOT_FOUND)
        return Response(RideDetailSerializer(ride).data)


class OpenRidesView(generics.ListAPIView):
    """Fresh SEARCHING requests for online approved drivers (the dispatch
    feed until realtime push lands in Module 8)."""

    serializer_class = OpenRideSerializer
    permission_classes = [IsApprovedDriver]

    def get_queryset(self):
        return services.open_rides_for(self.request.user)


class RideDetailView(generics.RetrieveAPIView):
    serializer_class = RideDetailSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Ride.objects.select_related("passenger", "driver", "vehicle", "payment")
        if user.is_admin_role:
            return qs
        if user.is_driver:
            return qs.filter(driver=user)
        return qs.filter(passenger=user)


class BaseRideActionView(APIView):
    """POST /rides/{id}/<action>/ -> updated ride detail."""

    def act(self, request, pk) -> Ride:
        raise NotImplementedError

    def post(self, request, pk):
        ride = self.act(request, pk)
        return Response(RideDetailSerializer(ride).data)


class AcceptRideView(BaseRideActionView):
    permission_classes = [IsApprovedDriver]

    def act(self, request, pk):
        return services.accept_ride(ride_id=pk, driver_user=request.user)


class RejectRideView(APIView):
    permission_classes = [IsApprovedDriver]

    def post(self, request, pk):
        services.reject_ride(ride_id=pk, driver_user=request.user)
        return Response({"detail": "Ride hidden from your feed."})


class ArrivedRideView(BaseRideActionView):
    permission_classes = [IsApprovedDriver]

    def act(self, request, pk):
        return services.driver_transition(ride_id=pk, driver_user=request.user, action="arrived")


class StartRideView(BaseRideActionView):
    permission_classes = [IsApprovedDriver]

    def act(self, request, pk):
        return services.driver_transition(ride_id=pk, driver_user=request.user, action="start")


class CompleteRideView(BaseRideActionView):
    permission_classes = [IsApprovedDriver]

    def act(self, request, pk):
        return services.driver_transition(ride_id=pk, driver_user=request.user, action="complete")


class CancelRideView(BaseRideActionView):
    """Passengers, assigned drivers, and admins — the service enforces
    who may cancel in which status."""

    def act(self, request, pk):
        serializer = CancelRideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return services.cancel_ride(
            ride_id=pk, user=request.user, reason=serializer.validated_data["reason"]
        )
