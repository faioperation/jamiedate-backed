import time
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from conversation.models import PlatformUser, Message
from conversation.serializers import PlatformUserSerializer, MessageSerializer
import json
import requests
import time
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings


class PlatformUserViewSet(viewsets.ModelViewSet):
    queryset = PlatformUser.objects.all()
    serializer_class = PlatformUserSerializer
    permission_classes = [
        permissions.AllowAny
    ]  # Switch to IsAuthenticated in production

    @action(detail=True, methods=["post"])
    def send_message(self, request, pk=None):
        user = self.get_object()
        text = request.data.get("text")

        if not text:
            return Response(
                {"error": "Text is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        msg = Message.objects.create(
            sender=user,
            text=text,
            is_from_bot=True,
            message_id=f"api_{int(time.time())}",
        )

        from .tasks import send_fb_message_task

        send_fb_message_task.delay(user.sender_id, text, msg.id)

        # Real-time dashboard update
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "dashboard_messages", {"type": "chat_message"}
        )

        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")
        if user_id:
            return self.queryset.filter(sender_id=user_id)
        return self.queryset


@csrf_exempt
def webhook(request):
    print(f"Webhook called: {request.method}")
    if request.method == "GET":
        # Facebook webhook verification
        verify_token = settings.FB_VERIFY_TOKEN
        print(f"GET Params: {request.GET}")
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == verify_token:
            print("Verification Successful!")
            return HttpResponse(challenge)
        print("Verification Failed!")
        return HttpResponse("Invalid verification token", status=403)

    elif request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))

        # 1. Print full JSON data for debugging
        print("-" * 50)
        print(f"WEBHOOK RECEIVED AT {request.path}")
        print(json.dumps(data, indent=2))
        print("-" * 50)

        if data.get("object") in ["page", "instagram", "whatsapp_business_account"]:
            platform = "facebook"
            if data.get("object") == "instagram":
                platform = "instagram"
            elif data.get("object") == "whatsapp_business_account":
                platform = "whatsapp"

            for entry in data.get("entry", []):
                # Handle FB/IG 'messaging' events
                for messaging_event in entry.get("messaging", []):
                    sender_id = messaging_event.get("sender", {}).get("id")
                    if not sender_id:
                        continue
                    entry_id = entry.get("id")
                    message_text = None
                    message_id = None
                    attachment_url = None
                    is_from_bot = False

                    if "message" in messaging_event:
                        msg_data = messaging_event["message"]
                        message_id = msg_data.get("mid")
                        message_text = msg_data.get("text")
                        is_echo = msg_data.get("is_echo", False)
                        if not is_echo and str(sender_id) == str(entry_id):
                            is_echo = True
                        if is_echo:
                            sender_id = messaging_event.get("recipient", {}).get("id")
                            is_from_bot = True
                        else:
                            is_from_bot = False
                        attachments = msg_data.get("attachments", [])
                        for att in attachments:
                            if att.get("type") == "image":
                                attachment_url = att.get("payload", {}).get("url")
                                break
                    elif "postback" in messaging_event:
                        message_text = messaging_event["postback"].get("payload")
                        message_id = f"pb_{messaging_event['postback'].get('mid', messaging_event['timestamp'])}"
                        is_from_bot = False

                    if (message_text or attachment_url) and sender_id:
                        process_messaging_event(sender_id, platform, message_id, message_text, attachment_url, is_from_bot)

                # Handle WhatsApp 'changes' events
                for change in entry.get("changes", []):
                    if change.get("field") == "messages":
                        value = change.get("value", {})
                        if "messages" in value:
                            for wa_msg in value["messages"]:
                                sender_id = wa_msg.get("from")
                                message_id = wa_msg.get("id")
                                message_text = wa_msg.get("text", {}).get("body")
                                # WhatsApp allows other types like image/audio, but we focus on text for now
                                if message_text and sender_id:
                                    process_messaging_event(sender_id, "whatsapp", message_id, message_text, None, False)

            return HttpResponse("EVENT_RECEIVED")

        return HttpResponse("NOT_A_HANDLED_EVENT", status=404)


def process_messaging_event(sender_id, platform, message_id, message_text, attachment_url, is_from_bot):
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
            if is_from_bot and (not msg.message_id or msg.message_id.startswith(("dash_", "api_", "bot_"))):
                msg.message_id = message_id
                msg.save()
            return

        print(f"Processing {platform.upper()} Event from {sender_id}: {message_text[:30] if message_text else '[Image]'}")

        # Fetch name if missing
        if not user.name:
            fetch_user_info(user)

        # Real-time dashboard update
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "dashboard_messages", {"type": "chat_message"}
        )

        # Reply only if it's NOT from bot/echo
        if not is_from_bot:
            from .tasks import call_chatbot_task
            call_chatbot_task.delay(user.sender_id, message_text, msg.id)

    except Exception as e:
        print(f"Error in process_messaging_event: {e}")


def get_access_token(user):
    # Use IG_PAGE_ACCESS_TOKEN for Instagram users if available
    ig_token = getattr(settings, "IG_PAGE_ACCESS_TOKEN", None)
    if user.platform == "instagram" and ig_token:
        return ig_token
    return settings.FB_PAGE_ACCESS_TOKEN


def send_fb_message(user, text):
    recipient_id = user.sender_id
    token = get_access_token(user)

    if user.platform == "whatsapp":
        # WhatsApp Cloud API
        phone_number_id = config("WHATSAPP_PHONE_NUMBER_ID", default="")
        if not phone_number_id:
            print("WHATSAPP_PHONE_NUMBER_ID not configured")
            return False, "WHATSAPP_PHONE_NUMBER_ID missing"
            
        url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": "text",
            "text": {"body": text}
        }
    elif user.platform == "instagram" and token and token.startswith("IGA"):
        version = settings.FB_API_URL.split("/")[-1] if "v" in settings.FB_API_URL else "v21.0"
        url = f"https://graph.instagram.com/{version}/me/messages"
        payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    else:
        url = f"{settings.FB_API_URL}/me/messages"
        payload = {"recipient": {"id": recipient_id}, "message": {"text": text}}

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        res = requests.post(url, headers=headers, json=payload)
        print(f"{user.platform.upper()} Send Status: {res.status_code}")
        if res.status_code == 200 or res.status_code == 201:
            try:
                data = res.json()
                msg_id = data.get("message_id") or data.get("messages", [{}])[0].get("id")
            except Exception:
                msg_id = None
            return True, msg_id
        else:
            error_msg = res.text
            print(f"{user.platform.upper()} Send Error: {error_msg}")
            return False, error_msg
    except Exception as e:
        error_msg = str(e)
        print(f"Error sending {user.platform} message: {error_msg}")
        return False, error_msg


def fetch_user_info(user):
    token = get_access_token(user)

    if user.platform == "instagram" and token and token.startswith("IGA"):
        version = (
            settings.FB_API_URL.split("/")[-1]
            if "v" in settings.FB_API_URL
            else "v21.0"
        )
        url = f"https://graph.instagram.com/{version}/{user.sender_id}"
        params = {
            "fields": "name,username,profile_pic",
            "access_token": token,
        }
    else:
        url = f"{settings.FB_API_URL}/{user.sender_id}"
        params = {
            "fields": "first_name,last_name,name,username,profile_pic",
            "access_token": token,
        }

    print(f"--- Fetching Info for: {user.sender_id} ---")

    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Graph API Status (Combined): {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            update_user_data(user, data)
            return

        # If combined fails, try only first_name and last_name
        print("Combined fetch failed, trying first_name and last_name only...")
        params["fields"] = "first_name,last_name"
        response = requests.get(url, params=params, timeout=10)
        print(f"Graph API Status (Granular): {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            update_user_data(user, data)
            return

        # Still failing, log detailed error
        print(f"Failed to fetch user info. Status: {response.status_code}")
        try:
            err_data = response.json().get("error", {})
            print(f"FB Error: {err_data.get('message')} (Code: {err_data.get('code')})")
        except Exception:
            print(f"Raw Error Body: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Network error fetching user info: {e}")


def update_user_data(user, data):
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    full_name = data.get("name")
    username = data.get("username")

    if full_name:
        user.name = full_name
    elif first_name or last_name:
        user.name = f"{first_name or ''} {last_name or ''}".strip()
    elif username:
        user.name = username

    if not user.name:
        pass

    # Accommodate both FB and IG profile picture fields
    if "profile_pic" in data:
        user.profile_pic = data.get("profile_pic")
    elif "profile_picture_url" in data:
        user.profile_pic = data.get("profile_picture_url")

    user.save()
    print(f"User info updated: {user.name}")


def api_messages(request):
    users = PlatformUser.objects.all().order_by("-last_interaction")
    data = []
    for user in users:
        messages = []
        for msg in user.messages.all().order_by("timestamp"):
            messages.append(
                {
                    "id": msg.id,
                    "text": msg.text,
                    "image_url": msg.image_url,
                    "is_from_bot": msg.is_from_bot,
                    "timestamp": msg.timestamp.strftime("%I:%M %p"),  # e.g. 02:30 PM
                    "full_timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

        data.append(
            {
                "id": user.id,
                "sender_id": user.sender_id,
                "name": user.name or f"User-{user.sender_id[-6:]}",
                "profile_pic": user.profile_pic,
                "last_interaction": (
                    user.last_interaction.strftime("%I:%M %p")  # Short time for sidebar
                    if user.last_interaction
                    else ""
                ),
                "last_interaction_date": (
                    user.last_interaction.strftime("%b %d")  # e.g. Mar 14
                    if user.last_interaction
                    else ""
                ),
                "platform": user.platform,
                "full_last_interaction": (
                    user.last_interaction.strftime("%Y-%m-%d %H:%M:%S")
                    if user.last_interaction
                    else ""
                ),
                "messages": messages,
            }
        )
    return JsonResponse({"users": data})


@csrf_exempt
@require_POST
def api_send_reply(request):
    try:
        data = json.loads(request.body)
        sender_id = data.get("sender_id")
        text = data.get("text")

        if not sender_id or not text:
            return JsonResponse(
                {"status": "error", "message": "Missing fields"}, status=400
            )

        user = PlatformUser.objects.get(sender_id=sender_id)

        # Save Message to DB immediately for instant UI update
        msg = Message.objects.create(
            sender=user,
            text=text,
            is_from_bot=True,
            message_id=f"dash_{int(time.time())}",
        )
        user.last_interaction = msg.timestamp
        user.save()

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "dashboard_messages", {"type": "chat_message"}
        )

        # Use Celery for Background Task
        from .tasks import send_fb_message_task

        send_fb_message_task.delay(user.sender_id, text, msg.id)

        return JsonResponse({"status": "success"})

    except PlatformUser.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "User not found"}, status=404
        )
    except Exception as e:
        print(f"Reply Error: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
