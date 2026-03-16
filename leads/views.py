from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from conversation.models import PlatformUser
from leads.serializers import LeadsSerializer, LeadsAnalyticsSerializer
from django.db.models import Avg


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
