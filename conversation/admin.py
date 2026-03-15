from django.contrib import admin
from conversation.models import PlatformUser, Message


# Register your models here.
@admin.register(PlatformUser)
class PlatformUserAdmin(admin.ModelAdmin):
    list_display = (
        "sender_id",
        "name",
        "platform",
        "score",
        "status",
        "current_state",
        "last_interaction",
    )
    list_filter = ("platform", "status")
    search_fields = ("sender_id", "name")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "text", "is_from_bot", "timestamp")
    list_filter = ("is_from_bot",)
    search_fields = ("sender__name", "text")
