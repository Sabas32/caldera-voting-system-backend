from __future__ import annotations

from rest_framework.test import APITestCase

from voting_system.apps.accounts.models import MembershipRole, OrgMembership, User
from voting_system.apps.organizations.models import Organization


class OrgUserManagementTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Org One", slug="org-one")
        self.other_org = Organization.objects.create(name="Org Two", slug="org-two")
        self.org_admin = User.objects.create_user(email="admin@example.com", password="Password123!")
        self.target_user = User.objects.create_user(email="member@example.com", password="Password123!")
        self.target_membership = OrgMembership.objects.create(
            user=self.target_user,
            organization=self.org,
            role=MembershipRole.RESULTS_VIEWER,
            is_active=True,
        )
        OrgMembership.objects.create(
            user=self.org_admin,
            organization=self.org,
            role=MembershipRole.ORG_ADMIN,
            is_active=True,
        )

    def test_org_admin_can_update_membership_and_reset_password(self):
        self.client.force_authenticate(self.org_admin)
        response = self.client.patch(
            f"/api/v1/org/users/{self.target_membership.id}/",
            {"role": "ELECTION_MANAGER", "reset_password": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.target_membership.refresh_from_db()
        self.assertEqual(self.target_membership.role, MembershipRole.ELECTION_MANAGER)
        self.assertIn("generated_password", response.data["data"])

    def test_org_admin_cannot_update_membership_in_other_org(self):
        outsider = User.objects.create_user(email="other-member@example.com", password="Password123!")
        outsider_membership = OrgMembership.objects.create(
            user=outsider,
            organization=self.other_org,
            role=MembershipRole.RESULTS_VIEWER,
            is_active=True,
        )
        self.client.force_authenticate(self.org_admin)
        response = self.client.patch(
            f"/api/v1/org/users/{outsider_membership.id}/",
            {"role": "ELECTION_MANAGER"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class AuthMeTests(APITestCase):
    def test_auth_me_returns_200_with_null_data_when_unauthenticated(self):
        response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIsNone(response.data["data"])

    def test_login_me_logout_flow_is_consistent(self):
        user = User.objects.create_user(email="flow@example.com", password="Password123!")

        login_response = self.client.post(
            "/api/v1/auth/login/",
            {"email": user.email, "password": "Password123!"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.data["success"])
        self.assertEqual(login_response.data["data"]["email"], user.email)

        me_response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.data["data"]["email"], user.email)

        logout_response = self.client.post("/api/v1/auth/logout/", {}, format="json")
        self.assertEqual(logout_response.status_code, 200)
        self.assertTrue(logout_response.data["success"])

        me_after_logout_response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(me_after_logout_response.status_code, 200)
        self.assertIsNone(me_after_logout_response.data["data"])
