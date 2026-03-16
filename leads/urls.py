from django.urls import path
from leads.views import LeadsListView, LeadsAnalyticsView

urlpatterns = [
    path("leads/", LeadsListView.as_view(), name="leads"),
    path("leads-summary", LeadsAnalyticsView.as_view(), name="leads"),
]
