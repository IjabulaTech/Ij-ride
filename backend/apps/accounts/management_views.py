"""Admin-only user management endpoints (mounted under /api/v1/management/)."""
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .permissions import IsAdminRole


class UserAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "phone",
            "first_name",
            "last_name",
            "email",
            "role",
            "nin",
            "nin_verified",
            "is_active",
            "date_joined",
            "last_login",
        )
        read_only_fields = fields


class UserListView(generics.ListAPIView):
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        qs = User.objects.order_by("-date_joined")
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role.upper())
        is_active = self.request.query_params.get("is_active")
        if is_active in ("true", "false"):
            qs = qs.filter(is_active=(is_active == "true"))
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(phone__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(nin__icontains=search)
            )
        return qs


class VerifyNinView(APIView):
    """Admin marks a user's NIN as verified / unverified after review.
    POST {verified: bool}. In V1 this is a manual decision; an automated NIMC +
    face-match provider can gate it later (see nin_verification.py)."""

    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        verified = bool(request.data.get("verified", True))
        if verified and not user.nin:
            return Response(
                {"detail": "This user has not provided a NIN yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.nin_verified = verified
        user.nin_verified_at = timezone.now() if verified else None
        user.save(update_fields=["nin_verified", "nin_verified_at"])
        return Response({"id": user.id, "nin": user.nin, "nin_verified": user.nin_verified})
