from django.urls import path

from voting_system.apps.analytics.views import OrgDashboardView, SystemDashboardView, SystemHealthView

urlpatterns = [
    path("system/dashboard/", SystemDashboardView.as_view(), name="system-dashboard"),
    path("system/health/", SystemHealthView.as_view(), name="system-health"),
    path("org/dashboard/", OrgDashboardView.as_view(), name="org-dashboard"),
]
