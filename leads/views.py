from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from datetime import timedelta
from conversation.models import PlatformUser, Message
from leads.serializers import (
    LeadsSerializer,
    LeadsAnalyticsSerializer,
    DashbaordSummarySerializer,
)
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate


class LeadsListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        leads = PlatformUser.objects.all().order_by("-score")
        serializer = LeadsSerializer(leads, many=True)
        return Response(serializer.data)


class LeadsAnalyticsView(APIView):

    def get(self, request):
        total_leads = PlatformUser.objects.count()

        hot_leads = PlatformUser.objects.filter(status="hotLead").count()
        average_score = PlatformUser.objects.aggregate(avg=Avg("score"))["avg"] or 0

        hot_lead_rate = (hot_leads / total_leads * 100) if total_leads > 0 else 0

        data = {
            "total_leads": total_leads,
            "hot_leads": hot_leads,
            "hot_lead_rate": round(hot_lead_rate, 2),
            "average_score": round(average_score, 2),
        }

        serializer = LeadsAnalyticsSerializer(data)
        return Response(serializer.data)


class DashbaordSummaryView(APIView):

    def get(self, request):
        total_users = PlatformUser.objects.count()

        # total user messages (bot message না)
        total_user_messages = Message.objects.filter(is_from_bot=False).count()

        # potential leads (score >= 70)
        potential_leads = PlatformUser.objects.filter(score__gte=70).count()

        # conversation rate
        users_with_messages = (
            PlatformUser.objects.annotate(msg_count=Count("messages"))
            .filter(msg_count__gt=0)
            .count()
        )

        conversation_rate = (
            (users_with_messages / total_users) * 100 if total_users > 0 else 0
        )

        # average messages per user
        average_messages_per_user = (
            total_user_messages / total_users if total_users > 0 else 0
        )

        data = {
            "total_user_messages": total_users,
            "potential_leads": potential_leads,
            "conversation_rate": round(conversation_rate, 2),
            "average_messages_per_user": round(average_messages_per_user, 2),
        }

        serializer = DashbaordSummarySerializer(data)
        return Response(serializer.data)


class Last7DaysMessagesView(APIView):

    def get(self, request):
        today = timezone.now().date()
        start_date = today - timedelta(days=6)

        messages = (
            Message.objects.filter(is_from_bot=False, timestamp__date__gte=start_date)
            .annotate(day=TruncDate("timestamp"))  # DB agnostic
            .values("day")
            .annotate(total_messages=Count("id"))
            .order_by("day")
        )

        # Convert QuerySet to dict for easy lookup
        messages_dict = {item["day"]: item["total_messages"] for item in messages}

        result = []
        for i in range(7):
            day = start_date + timedelta(days=i)
            count = messages_dict.get(day, 0)
            result.append(
                {
                    "day": day.strftime("%A %d-%b"),  # Monday 16-Mar
                    "total_messages": count,
                }
            )

        return Response(result)
