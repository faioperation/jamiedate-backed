from django.urls import path
from leads.views import (
    LeadsListView,
    LeadsAnalyticsView,
    DashbaordSummaryView,
    Last7DaysMessagesView,
)

urlpatterns = [
    path("leads/", LeadsListView.as_view(), name="leads"),
    path("leads-summary/", LeadsAnalyticsView.as_view(), name="leads"),
    path("dashboard-summary/", DashbaordSummaryView.as_view(), name="leads"),
    path("dashboard-graph/", Last7DaysMessagesView.as_view(), name="leads"),
]
