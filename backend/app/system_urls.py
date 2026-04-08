from django.urls import path

from app.accounts.views.admin_overview import AdminOverviewView
from app.accounts.views.web_usage_sync import SystemWebUsageSyncDetailView, SystemWebUsageSyncRunView, SystemWebUsageSyncSummaryView
from app.chatgpt.views.usage import SystemUsageDetailView, SystemUsageSummaryView

urlpatterns = [
    path("admin-overview", AdminOverviewView.as_view()),
    path("usage-summary", SystemUsageSummaryView.as_view()),
    path("usage-detail", SystemUsageDetailView.as_view()),
    path("web-usage-sync-summary", SystemWebUsageSyncSummaryView.as_view()),
    path("web-usage-sync-detail", SystemWebUsageSyncDetailView.as_view()),
    path("web-usage-sync", SystemWebUsageSyncRunView.as_view()),
]
