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
    print(f"\n[SERVICE] Processing {platform.upper()} Event from {sender_id}. Text: '{message_text}'", flush=True)
    try:
        # Get or create user
        user, created = PlatformUser.objects.get_or_create(
            sender_id=sender_id, defaults={"platform": platform}
        )
        if created:
            print(f"[SERVICE] Created new user: {sender_id}", flush=True)

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
            print(f"[SERVICE] Message {message_id} already exists. Skipping.", flush=True)
            # If it's an echo and we found an existing message without a real ID, update it
            if is_from_bot and (
                not msg.message_id
                or msg.message_id.startswith(("dash_", "api_", "bot_"))
            ):
                msg.message_id = message_id
                msg.save()
            return

        print(f"[SERVICE] Message successfully saved with ID: {msg.id}", flush=True)

        # Fetch name if missing
        if not user.name:
            print(f"[SERVICE] User name missing. Fetching from Meta API...", flush=True)
            fetch_user_info(user)

        # Real-time dashboard update
        from conversation.utils import broadcast_message
        print(f"[SERVICE] Broadcasting message to discovery group via WebSocket", flush=True)
        broadcast_message(msg)

        if not is_from_bot:
            from conversation.tasks import call_chatbot_task
            print(f"[SERVICE] Queueing 'call_chatbot_task' for {user.sender_id}", flush=True)
            call_chatbot_task.delay(user.sender_id, message_text, msg.id)
        else:
            print("[SERVICE] Message is from bot or echo. Skipping chatbot call.", flush=True)

    except Exception as e:
        print(f"[SERVICE] CRITICAL ERROR in process_messaging_event: {e}", flush=True)
