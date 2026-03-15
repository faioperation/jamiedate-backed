import requests
import json
import time
from celery import shared_task
from django.conf import settings
from .models import PlatformUser, Message
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@shared_task
def send_fb_message_task(sender_id, text, message_db_id=None):
    """
    Background task to send a message via Meta Graph API.
    """
    try:
        user = PlatformUser.objects.get(sender_id=sender_id)
        # Import here to avoid circular dependency
        from .views import send_fb_message
        
        success, response = send_fb_message(user, text)
        
        if success and message_db_id:
            msg = Message.objects.filter(id=message_db_id).first()
            if msg:
                msg.message_id = response # Meta returns the mid
                msg.save()
        
        return success
    except Exception as e:
        print(f"Error in send_fb_message_task: {e}")
        return False

@shared_task
def call_chatbot_task(sender_id, user_text, incoming_msg_id):
    """
    Background task to call the chatbot server and handle the reply.
    """
    print(f"\n[BOT] Starting chatbot task for sender: {sender_id}")
    try:
        user = PlatformUser.objects.get(sender_id=sender_id)
        
        # Prepare history (last 10 messages)
        history = []
        recent_msgs = Message.objects.filter(sender=user).order_by('-timestamp')[:10]
        for m in reversed(recent_msgs):
            history.append({
                "role": "assistant" if m.is_from_bot else "user",
                "content": m.text
            })

        payload = {
            "user_id": sender_id,
            "message": user_text,
            "platform": user.platform,
            "history": history,
            "attributes": user.bot_attributes
        }

        chatbot_url = settings.CHATBOT_URL
        if not chatbot_url:
            print("[BOT] CHATBOT_URL not configured in settings")
            return

        print(f"[BOT] Calling Chatbot URL: {chatbot_url}")
        print(f"[BOT] Payload: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(chatbot_url, json=payload, timeout=30)
            print(f"[BOT] Response Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[BOT] Connection Error: {e}")
            return
        
        if response.status_code == 200:
            data = response.json()
            print(f"[BOT] Data Received: {json.dumps(data, indent=2)}")
            reply_text = data.get("reply")
            next_state = data.get("next_state")
            extracted_attrs = data.get("extracted_attributes", {})
            progress_score = data.get("progress_score", 0)

            if reply_text:
                # Save bot reply to DB
                bot_msg = Message.objects.create(
                    sender=user,
                    text=reply_text,
                    is_from_bot=True,
                    message_id=f"bot_pending_{int(time.time())}"
                )
                print(f"[BOT] Bot reply saved: {bot_msg.id}")

                # Update user state and attributes
                if next_state:
                    user.current_state = next_state
                
                if extracted_attrs:
                    user.bot_attributes.update(extracted_attrs)
                
                user.update_score_and_status(progress_score)
                user.save()

                # Notify dashboard via WebSocket
                print("[BOT] Sending WebSocket update signal")
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "dashboard_messages", {"type": "chat_message"}
                )

                # Trigger sending task
                print(f"[BOT] Triggering send_fb_message_task for: {reply_text[:20]}...")
                send_fb_message_task.delay(user.sender_id, reply_text, bot_msg.id)
            else:
                print("[BOT] No reply_text found in API response")
        else:
            print(f"[BOT] Chatbot API error: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"[BOT] Critical Error in call_chatbot_task: {e}")
