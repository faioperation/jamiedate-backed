import time
import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.db.models import Prefetch
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from conversation.models import PlatformUser, Message
from conversation.serializers import PlatformUserSerializer, MessageSerializer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from conversation.services import process_messaging_event


class PlatformUserViewSet(viewsets.ModelViewSet):
    queryset = PlatformUser.objects.prefetch_related(
        Prefetch("messages", queryset=Message.objects.order_by("-timestamp"))
    ).all()
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
                        process_messaging_event(
                            sender_id,
                            platform,
                            message_id,
                            message_text,
                            attachment_url,
                            is_from_bot,
                        )

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
                                    process_messaging_event(
                                        sender_id,
                                        "whatsapp",
                                        message_id,
                                        message_text,
                                        None,
                                        False,
                                    )

            return HttpResponse("EVENT_RECEIVED")

        return HttpResponse("NOT_A_HANDLED_EVENT", status=404)


def api_messages(request):
    users = (
        PlatformUser.objects.prefetch_related(
            Prefetch("messages", queryset=Message.objects.order_by("-timestamp"))
        )
        .all()
        .order_by("-last_interaction")
    )
    data = []
    for user in users:
        messages = []
        # Use prefetched messages directly
        for msg in user.messages.all():
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
        from conversation.tasks import send_fb_message_task

        send_fb_message_task.delay(user.sender_id, text, msg.id)

        return JsonResponse({"status": "success"})

    except PlatformUser.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "User not found"}, status=404
        )
    except Exception as e:
        print(f"Reply Error: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
