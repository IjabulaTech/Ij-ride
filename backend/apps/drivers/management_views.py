"""Admin-only driver management endpoints (mounted under /api/v1/management/)."""
from django.db.models import Q
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole

from . import services
from .models import DriverProfile
from .serializers import ApproveDriverSerializer, DriverAdminSerializer, RejectDriverSerializer


def _driver_queryset():
    return (
        DriverProfile.objects.select_related("user", "availability", "approved_by")
        .prefetch_related("vehicles")
        .order_by("-created_at")
    )


class DriverListView(generics.ListAPIView):
    serializer_class = DriverAdminSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        qs = _driver_queryset()
        approval_status = self.request.query_params.get("approval_status")
        if approval_status:
            qs = qs.filter(approval_status=approval_status.upper())
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(user__phone__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(license_number__icontains=search)
                | Q(vehicles__plate_number__icontains=search)
            ).distinct()
        return qs


class DriverDetailView(generics.RetrieveAPIView):
    serializer_class = DriverAdminSerializer
    permission_classes = [IsAdminRole]
    queryset = _driver_queryset()


class ApproveDriverView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        profile = generics.get_object_or_404(_driver_queryset(), pk=pk)
        serializer = ApproveDriverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = services.approve_driver(
            profile, admin_user=request.user, note=serializer.validated_data["note"]
        )
        return Response(DriverAdminSerializer(profile).data)


class RejectDriverView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        profile = generics.get_object_or_404(_driver_queryset(), pk=pk)
        serializer = RejectDriverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = services.reject_driver(
            profile, admin_user=request.user, reason=serializer.validated_data["reason"]
        )
        return Response(DriverAdminSerializer(profile).data)
