from django.urls import path

from voting_system.apps.audit.views import OrgAuditListView, SystemAuditListView

urlpatterns = [
    path("system/audit/", SystemAuditListView.as_view(), name="system-audit"),
    path("org/audit/", OrgAuditListView.as_view(), name="org-audit"),
]
