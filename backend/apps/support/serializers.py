from rest_framework import serializers

from .models import SupportMessage, SupportThread


class SupportMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportMessage
        fields = ("id", "thread", "body", "from_admin", "sender_name", "created_at")
        read_only_fields = fields

    def get_sender_name(self, message) -> str:
        if message.from_admin:
            return "IJ Ride Support"
        sender = message.sender
        if not sender:
            return "User"
        return " ".join(p for p in (sender.first_name, sender.last_name) if p) or sender.phone


class SendMessageSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=2000, trim_whitespace=True)

    def validate_body(self, value):
        if not value.strip():
            raise serializers.ValidationError("Message cannot be empty.")
        return value.strip()


class SupportThreadSerializer(serializers.ModelSerializer):
    """Admin inbox row: who it's from plus the latest activity."""

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    name = serializers.SerializerMethodField()
    role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = SupportThread
        fields = (
            "id",
            "user_id",
            "phone",
            "name",
            "role",
            "last_message_at",
            "last_message_preview",
            "unread_for_admin",
            "created_at",
        )
        read_only_fields = fields

    def get_name(self, thread) -> str:
        user = thread.user
        return " ".join(p for p in (user.first_name, user.last_name) if p) or user.phone
