from rest_framework import serializers
from conversation.models import PlatformUser, Message


class MessageSerializer(serializers.ModelSerializer):
    timestamp_display = serializers.SerializerMethodField()
    date_display = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "sender",
            "message_id",
            "text",
            "image_url",
            "timestamp",
            "timestamp_display",
            "date_display",
            "is_from_bot",
        ]
        read_only_fields = ["id", "timestamp", "timestamp_display"]

    def get_timestamp_display(self, obj):
        return obj.timestamp.strftime("%I:%M %p")

    def get_date_display(self, obj):
        return obj.timestamp.strftime("%b %d, %Y")


class PlatformUserSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    last_interaction_display = serializers.SerializerMethodField()
    display_name = serializers.ReadOnlyField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PlatformUser
        fields = [
            "id",
            "sender_id",
            "platform",
            "name",
            "display_name",
            "profile_pic",
            "current_state",
            "bot_attributes",
            "score",
            "status",
            "status_display",
            "last_interaction",
            "last_interaction_display",
            "messages",
        ]
        read_only_fields = [
            "id",
            "last_interaction",
            "last_interaction_display",
            "display_name",
            "status_display",
        ]

    def get_last_interaction_display(self, obj):
        if obj.last_interaction:
            return obj.last_interaction.strftime("%b %d, %I:%M %p")
        return None
