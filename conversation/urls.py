from django.urls import path, include
from rest_framework.routers import DefaultRouter
from conversation import views


router = DefaultRouter()
router.register("users", views.PlatformUserViewSet)
router.register("messages", views.MessageViewSet)

urlpatterns = [
    path("webhook/", views.webhook, name="webhook"),
    path("api/messages/", views.api_messages, name="api_messages"),
    path("api/send-reply/", views.api_send_reply, name="api_send_reply"),
    path("", include(router.urls)),
]
