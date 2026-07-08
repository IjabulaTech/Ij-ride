"""Admin-only payment records (mounted under /api/v1/management/)."""
from django.db.models import Q
from rest_framework import generics

from apps.accounts.permissions import IsAdminRole

from .models import Payment
from .serializers import PaymentAdminSerializer


def _payment_queryset():
    return Payment.objects.select_related(
        "ride", "ride__passenger", "ride__driver", "confirmed_by"
    ).order_by("-created_at")


class PaymentAdminListView(generics.ListAPIView):
    serializer_class = PaymentAdminSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        qs = _payment_queryset()
        payment_status = self.request.query_params.get("status")
        if payment_status:
            qs = qs.filter(status=payment_status.upper())
        method = self.request.query_params.get("method")
        if method:
            qs = qs.filter(method=method.upper())
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(ride__passenger__phone__icontains=search)
                | Q(ride__driver__phone__icontains=search)
                | Q(reference__icontains=search)
            )
        return qs


class PaymentAdminDetailView(generics.RetrieveAPIView):
    serializer_class = PaymentAdminSerializer
    permission_classes = [IsAdminRole]
    queryset = _payment_queryset()
