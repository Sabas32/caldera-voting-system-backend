from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from voting_system.apps.accounts.models import MembershipRole, OrgMembership, User
from voting_system.apps.elections.models import Election
from voting_system.apps.organizations.models import Organization


class OrgIsolationTests(APITestCase):
    def setUp(self):
        self.org_1 = Organization.objects.create(name="Org One", slug="org-one")
        self.org_2 = Organization.objects.create(name="Org Two", slug="org-two")
        self.user = User.objects.create_user(email="manager@example.com", password="password123")
        self.org_admin = User.objects.create_user(email="admin@example.com", password="password123")
        OrgMembership.objects.create(user=self.user, organization=self.org_1, role=MembershipRole.ELECTION_MANAGER)
        OrgMembership.objects.create(user=self.org_admin, organization=self.org_1, role=MembershipRole.ORG_ADMIN)
        Election.objects.create(organization=self.org_1, title="Election 1", slug="election-1")
        Election.objects.create(organization=self.org_2, title="Election 2", slug="election-2")

    def test_user_cannot_list_other_org_elections(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/org/elections/", HTTP_X_ORG_ID=str(self.org_2.id))
        self.assertEqual(response.status_code, 403)

    def test_user_can_list_own_org_elections(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/v1/org/elections/", HTTP_X_ORG_ID=str(self.org_1.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)

    def test_create_post_and_candidate_without_fk_fields_in_payload(self):
        self.client.force_authenticate(self.user)
        election = Election.objects.filter(organization=self.org_1).first()
        self.assertIsNotNone(election)
        post_response = self.client.post(
            f"/api/v1/org/elections/{election.id}/posts/",
            {"title": "President", "max_selections": 1, "allow_abstain": False, "sort_order": 1},
            format="json",
        )
        self.assertEqual(post_response.status_code, 201)
        post_id = post_response.data["data"]["id"]

        candidate_response = self.client.post(
            f"/api/v1/org/posts/{post_id}/candidates/",
            {"name": "Candidate One", "status": "APPROVED", "sort_order": 1},
            format="json",
        )
        self.assertEqual(candidate_response.status_code, 201)

    def test_schedule_moves_to_live_if_open_time_already_passed(self):
        self.client.force_authenticate(self.user)
        election = Election.objects.create(
            organization=self.org_1,
            title="Election Immediate",
            slug="election-immediate",
            status="DRAFT",
            opens_at=timezone.now() - timedelta(minutes=1),
            closes_at=timezone.now() + timedelta(hours=1),
        )
        response = self.client.post(
            f"/api/v1/org/elections/{election.id}/status/",
            {"action": "schedule"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["status"], "LIVE")

    def test_create_election_uses_org_auto_logout_default_when_not_provided(self):
        self.org_1.voter_auto_logout_seconds = 180
        self.org_1.save(update_fields=["voter_auto_logout_seconds", "updated_at"])
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/org/elections/",
            {"title": "Election Default Timeout", "slug": "election-default-timeout"},
            format="json",
            HTTP_X_ORG_ID=str(self.org_1.id),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["voter_auto_logout_seconds"], 180)

    def test_create_election_respects_explicit_auto_logout_timeout(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/org/elections/",
            {
                "title": "Election Custom Timeout",
                "slug": "election-custom-timeout",
                "voter_auto_logout_seconds": 420,
            },
            format="json",
            HTTP_X_ORG_ID=str(self.org_1.id),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["voter_auto_logout_seconds"], 420)

    def test_patch_election_ignores_unknown_fields_from_frontend_form_state(self):
        election = Election.objects.create(
            organization=self.org_1,
            title="Patch Target",
            slug="patch-target",
            status="DRAFT",
        )
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            f"/api/v1/org/elections/{election.id}/",
            {
                "title": "Patch Target Updated",
                "status": "ARCHIVED",
                "summary": {"tokens_generated": 100},
                "turnout_series": [],
                "organization_name": "Org One",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        election.refresh_from_db()
        self.assertEqual(election.title, "Patch Target Updated")
        self.assertEqual(election.status, "DRAFT")

    def test_patch_election_returns_structured_validation_error_details(self):
        election = Election.objects.create(
            organization=self.org_1,
            title="Validation Target",
            slug="validation-target",
            status="DRAFT",
        )
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            f"/api/v1/org/elections/{election.id}/",
            {
                "opens_at": "2026-03-01T10:00:00Z",
                "closes_at": "2026-03-01T09:00:00Z",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])
        self.assertIn("closes_at must be later than opens_at", response.data["message"])
        self.assertIn("non_field_errors", response.data["details"])

    def test_org_admin_can_delete_closed_election(self):
        election = Election.objects.create(
            organization=self.org_1,
            title="Closed Election",
            slug="closed-election",
            status="CLOSED",
        )
        self.client.force_authenticate(self.org_admin)
        response = self.client.delete(f"/api/v1/org/elections/{election.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Election.objects.filter(id=election.id).exists())

    def test_election_manager_cannot_delete_election(self):
        election = Election.objects.create(
            organization=self.org_1,
            title="Draft Election",
            slug="draft-election",
            status="DRAFT",
        )
        self.client.force_authenticate(self.user)
        response = self.client.delete(f"/api/v1/org/elections/{election.id}/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Election.objects.filter(id=election.id).exists())

    def test_cannot_delete_live_election(self):
        election = Election.objects.create(
            organization=self.org_1,
            title="Live Election",
            slug="live-election",
            status="LIVE",
        )
        self.client.force_authenticate(self.org_admin)
        response = self.client.delete(f"/api/v1/org/elections/{election.id}/")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Election.objects.filter(id=election.id).exists())
