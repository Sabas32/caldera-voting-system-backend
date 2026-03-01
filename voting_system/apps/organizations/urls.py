from django.urls import path

from voting_system.apps.organizations.views import (
    OrgSettingsView,
    SystemOrganizationDetailView,
    SystemOrganizationListCreateView,
)

urlpatterns = [
    path("system/organizations/", SystemOrganizationListCreateView.as_view(), name="system-organizations"),
    path("system/organizations/<uuid:org_id>/", SystemOrganizationDetailView.as_view(), name="system-organization-detail"),
    path("org/settings/", OrgSettingsView.as_view(), name="org-settings"),
]
