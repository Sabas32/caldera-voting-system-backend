from __future__ import annotations

from rest_framework.test import APITestCase

from voting_system.apps.accounts.models import MembershipRole, OrgMembership, User
from voting_system.apps.organizations.models import Organization


class OrgSettingsTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Acme School", slug="acme-school")
        self.admin = User.objects.create_user(email="org-admin@example.com", password="Password123!")
        self.viewer = User.objects.create_user(email="org-viewer@example.com", password="Password123!")
        OrgMembership.objects.create(
            user=self.admin,
            organization=self.org,
            role=MembershipRole.ORG_ADMIN,
            is_active=True,
        )
        OrgMembership.objects.create(
            user=self.viewer,
            organization=self.org,
            role=MembershipRole.RESULTS_VIEWER,
            is_active=True,
        )

    def test_org_admin_can_update_org_settings(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            "/api/v1/org/settings/",
            {"primary_color_override": "#FFD766"},
            format="json",
            HTTP_X_ORG_ID=str(self.org.id),
        )
        self.assertEqual(response.status_code, 200)
        self.org.refresh_from_db()
        self.assertEqual(self.org.primary_color_override, "#FFD766")

    def test_non_admin_role_cannot_update_org_settings(self):
        self.client.force_authenticate(self.viewer)
        response = self.client.patch(
            "/api/v1/org/settings/",
            {"primary_color_override": "#FFD766"},
            format="json",
            HTTP_X_ORG_ID=str(self.org.id),
        )
        self.assertEqual(response.status_code, 403)
