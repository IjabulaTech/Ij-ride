"""Admin support inbox (mounted under /api/v1/management/support/)."""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole

from . import services
from .models import SupportThread
from .serializers import (
    SendMessageSerializer,
    SupportMessageSerializer,
    SupportThreadSerializer,
)


class SupportThreadListView(generics.ListAPIView):
    """Every conversation, most recently active first. `unread=true` narrows
    to threads waiting on a reply."""

    serializer_class = SupportThreadSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        qs = SupportThread.objects.select_related("user")
        if self.request.query_params.get("unread") == "true":
            qs = qs.filter(unread_for_admin__gt=0)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(user__phone__icontains=search)
        return qs


class SupportThreadMessagesView(APIView):
    """GET  -> one thread's messages (marks them read for admins)
    POST -> reply as support."""

    permission_classes = [IsAdminRole]

    def _thread(self, pk):
        return SupportThread.objects.select_related("user").filter(pk=pk).first()

    def get(self, request, pk):
        thread = self._thread(pk)
        if thread is None:
            return Response({"detail": "Thread not found."}, status=status.HTTP_404_NOT_FOUND)
        messages = thread.messages.select_related("sender").all()
        data = SupportMessageSerializer(messages, many=True).data
        services.mark_read(thread, for_admin=True)
        return Response({"thread": SupportThreadSerializer(thread).data, "results": data})

    def post(self, request, pk):
        thread = self._thread(pk)
        if thread is None:
            return Response({"detail": "Thread not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = services.post_message(
            thread=thread,
            sender=request.user,
            body=serializer.validated_data["body"],
            from_admin=True,
        )
        return Response(
            SupportMessageSerializer(message).data, status=status.HTTP_201_CREATED
        )
