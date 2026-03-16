from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from conversation.models import PlatformUser, Message
from conversation.utils import fetch_user_info


def process_messaging_event(
    sender_id, platform, message_id, message_text, attachment_url, is_from_bot
):
    """
    Core logic to handle incoming message events from various platforms.
    """
    try:
        # Get or create user
        user, created = PlatformUser.objects.get_or_create(
            sender_id=sender_id, defaults={"platform": platform}
        )

        # Always update last_interaction
        user.save()

        # Create message record
        msg, msg_created = Message.objects.get_or_create(
            message_id=message_id,
            defaults={
                "sender": user,
                "text": message_text,
                "image_url": attachment_url,
                "is_from_bot": is_from_bot,
            },
        )

        if not msg_created:
            # If it's an echo and we found an existing message without a real ID, update it
            if is_from_bot and (
                not msg.message_id
                or msg.message_id.startswith(("dash_", "api_", "bot_"))
            ):
                msg.message_id = message_id
                msg.save()
            return

        # print(
        #     f"Processing {platform.upper()} Event from {sender_id}. Text: '{message_text}' (len: {len(message_text) if message_text else 0})"
        # )

        # Fetch name if missing
        if not user.name:
            fetch_user_info(user)

        # Real-time dashboard update
        from conversation.utils import broadcast_message

        broadcast_message(msg)

        # Reply only if it's NOT from bot/echo
        if not is_from_bot:
            from conversation.tasks import call_chatbot_task

            call_chatbot_task.delay(user.sender_id, message_text, msg.id)

    except Exception as e:
        print(f"Error in process_messaging_event: {e}")
