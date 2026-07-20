"""The signed-in user's own support conversation (/api/v1/support/)."""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .serializers import SendMessageSerializer, SupportMessageSerializer


class MySupportThreadView(APIView):
    """GET  -> the user's whole conversation (and marks admin replies read)
    POST -> send a message to support."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        thread = services.get_or_create_thread(request.user)
        messages = thread.messages.select_related("sender").all()
        data = SupportMessageSerializer(messages, many=True).data
        services.mark_read(thread, for_admin=False)
        return Response({"thread_id": thread.id, "results": data})

    def post(self, request):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        thread = services.get_or_create_thread(request.user)
        message = services.post_message(
            thread=thread,
            sender=request.user,
            body=serializer.validated_data["body"],
            from_admin=False,
        )
        return Response(
            SupportMessageSerializer(message).data, status=status.HTTP_201_CREATED
        )
