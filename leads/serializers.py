from rest_framework import serializers
from conversation.models import PlatformUser, Message


class LeadsSerializer(serializers.ModelSerializer):
    last_interaction_display = serializers.SerializerMethodField()
    display_name = serializers.ReadOnlyField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PlatformUser
        fields = [
            "id",
            "platform",
            "display_name",
            # "bot_attributes",
            "score",
            "status_display",
            "last_interaction_display",
        ]
        read_only_fields = [
            "id",
            "last_interaction_display",
            "display_name",
            "status_display",
        ]

    def get_last_interaction_display(self, obj):
        if obj.last_interaction:
            return obj.last_interaction.strftime("%b %d, %Y, %I:%M %p")
        return None


class LeadsAnalyticsSerializer(serializers.Serializer):
    total_leads = serializers.IntegerField()
    hot_leads = serializers.IntegerField()
    hot_lead_rate = serializers.FloatField()
    average_score = serializers.FloatField()


class DashbaordSummarySerializer(serializers.Serializer):
    total_user_messages = serializers.IntegerField()
    potential_leads = serializers.IntegerField()
    conversation_rate = serializers.FloatField()
    average_messages_per_user = serializers.FloatField()


class MessageGraphSerializer(serializers.Serializer):
    day = serializers.CharField()
    total_messages = serializers.IntegerField()
