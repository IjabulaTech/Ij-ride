from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsPassenger

from . import services
from .serializers import ClaimPaymentSerializer


def _ride_response(payment):
    # Serialize the full ride so the frontend refreshes one object
    from apps.rides.models import Ride
    from apps.rides.serializers import RideDetailSerializer

    ride = Ride.objects.select_related("passenger", "driver", "vehicle", "payment").get(
        pk=payment.ride_id
    )
    return Response(RideDetailSerializer(ride).data)


class ClaimPaymentView(APIView):
    """POST /rides/{id}/payment/claim/ — passenger's 'I have paid' for
    transfer rides, with an optional bank reference."""

    permission_classes = [IsPassenger]

    def post(self, request, pk):
        serializer = ClaimPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = services.claim_payment(
            ride_id=pk, passenger=request.user, reference=serializer.validated_data["reference"]
        )
        return _ride_response(payment)


class ConfirmPaymentView(APIView):
    """POST /rides/{id}/payment/confirm/ — assigned driver or admin confirms
    the money was received (cash or transfer)."""

    def post(self, request, pk):
        payment = services.confirm_payment(ride_id=pk, user=request.user)
        return _ride_response(payment)
