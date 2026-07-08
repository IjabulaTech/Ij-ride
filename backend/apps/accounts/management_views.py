"""Admin-only user management endpoints (mounted under /api/v1/management/)."""
from django.db.models import Q
from rest_framework import generics, serializers

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
            )
        return qs
