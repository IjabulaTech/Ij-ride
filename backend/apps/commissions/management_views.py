"""Admin-only commission & remittance endpoints (under /api/v1/management/)."""
from django.db.models import Q
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole

from . import services
from .models import RideCommission
from .serializers import (
    RemitSerializer,
    RideCommissionAdminSerializer,
    SettleDriverSerializer,
)


def _commission_queryset():
    return RideCommission.objects.select_related("driver", "confirmed_by").order_by(
        "-created_at"
    )


class CommissionListView(generics.ListAPIView):
    serializer_class = RideCommissionAdminSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        qs = _commission_queryset()
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param.upper())
        driver_id = self.request.query_params.get("driver_id")
        if driver_id and driver_id.isdigit():
            qs = qs.filter(driver_id=int(driver_id))
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(driver__phone__icontains=search)
                | Q(driver__first_name__icontains=search)
                | Q(driver__last_name__icontains=search)
            )
        return qs


class CommissionSummaryView(APIView):
    """Platform totals + per-driver outstanding balances."""

    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response(services.platform_summary())


class RemitCommissionView(APIView):
    """POST /management/commissions/{id}/remit/ — confirm one ride's remittance."""

    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        commission = generics.get_object_or_404(_commission_queryset(), pk=pk)
        serializer = RemitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        commission = services.mark_remitted(
            commission, admin_user=request.user, note=serializer.validated_data["note"]
        )
        return Response(RideCommissionAdminSerializer(commission).data)


class SettleDriverView(APIView):
    """POST /management/commissions/settle-driver/ — mark everything a driver
    owes as remitted (one transfer covering several rides)."""

    permission_classes = [IsAdminRole]

    def post(self, request):
        serializer = SettleDriverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.settle_driver(admin_user=request.user, **serializer.validated_data)
        return Response(result)
