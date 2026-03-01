from __future__ import annotations

from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from voting_system.apps.accounts.models import MembershipRole, OrgMembership, User
from voting_system.apps.ballots.models import Ballot, BallotChoice
from voting_system.apps.elections.models import Candidate, Election, Post
from voting_system.apps.organizations.models import Organization
from voting_system.apps.tokens.models import Token, TokenBatch, TokenStatus
from voting_system.apps.tokens.services import run_expired_batch_cleanup


class UsedTokenManagementTests(APITestCase):
    def setUp(self):
        self.org_1 = Organization.objects.create(name="Org One", slug="org-one")
        self.org_2 = Organization.objects.create(name="Org Two", slug="org-two")

        self.manager = User.objects.create_user(email="manager@org-one.local", password="password123")
        self.viewer = User.objects.create_user(email="viewer@org-one.local", password="password123")
        OrgMembership.objects.create(user=self.manager, organization=self.org_1, role=MembershipRole.ELECTION_MANAGER)
        OrgMembership.objects.create(user=self.viewer, organization=self.org_1, role=MembershipRole.RESULTS_VIEWER)

        self.election = Election.objects.create(organization=self.org_1, title="Guild Election", slug="guild-election")
        self.post = Post.objects.create(election=self.election, title="President", max_selections=1, sort_order=1)
        self.candidate = Candidate.objects.create(post=self.post, name="Alex Carter", sort_order=1)

        self.batch = TokenBatch.objects.create(election=self.election, label="Main Batch", quantity=10)
        self.used_token = Token.objects.create(
            batch=self.batch,
            election=self.election,
            token_hash="hash-used-1",
            token_hint="USED01",
            status=TokenStatus.USED,
            used_at=timezone.now(),
        )
        self.ballot = Ballot.objects.create(election=self.election, token=self.used_token, receipt_code="RECPT0001")
        BallotChoice.objects.create(ballot=self.ballot, post=self.post, candidate=self.candidate, abstained=False)

        self.other_election = Election.objects.create(organization=self.org_2, title="Other Election", slug="other-election")
        self.other_batch = TokenBatch.objects.create(election=self.other_election, label="Other Batch", quantity=5)
        self.other_token = Token.objects.create(
            batch=self.other_batch,
            election=self.other_election,
            token_hash="hash-other-1",
            token_hint="OTH001",
            status=TokenStatus.USED,
            used_at=timezone.now(),
        )

    def test_list_used_tokens_and_search(self):
        self.client.force_authenticate(self.manager)
        response = self.client.get(f"/api/v1/org/elections/{self.election.id}/used-tokens/")
        self.assertEqual(response.status_code, 200)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["token_hint"], "USED01")
        self.assertEqual(results[0]["selections"][0]["candidate_names"], ["Alex Carter"])

        search_response = self.client.get(
            f"/api/v1/org/elections/{self.election.id}/used-tokens/",
            {"search": "Alex"},
        )
        self.assertEqual(search_response.status_code, 200)
        self.assertEqual(len(search_response.data["data"]["results"]), 1)

    def test_reset_vote_reactivates_token_and_deletes_ballot(self):
        self.client.force_authenticate(self.manager)
        response = self.client.post(f"/api/v1/org/tokens/{self.used_token.id}/reset-vote/", {}, format="json")
        self.assertEqual(response.status_code, 200)

        self.used_token.refresh_from_db()
        self.assertEqual(self.used_token.status, TokenStatus.ACTIVE)
        self.assertIsNone(self.used_token.used_at)
        self.assertFalse(Ballot.objects.filter(id=self.ballot.id).exists())

    def test_delete_token_removes_token_and_ballot(self):
        self.client.force_authenticate(self.manager)
        response = self.client.delete(f"/api/v1/org/tokens/{self.used_token.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Token.objects.filter(id=self.used_token.id).exists())
        self.assertFalse(Ballot.objects.filter(id=self.ballot.id).exists())

    def test_delete_batch_removes_tokens_and_ballots(self):
        self.client.force_authenticate(self.manager)
        response = self.client.delete(f"/api/v1/org/token-batches/{self.batch.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TokenBatch.objects.filter(id=self.batch.id).exists())
        self.assertFalse(Token.objects.filter(batch_id=self.batch.id).exists())
        self.assertFalse(Ballot.objects.filter(id=self.ballot.id).exists())

    def test_results_viewer_cannot_reset_or_delete_token(self):
        self.client.force_authenticate(self.viewer)
        reset_response = self.client.post(f"/api/v1/org/tokens/{self.used_token.id}/reset-vote/", {}, format="json")
        self.assertEqual(reset_response.status_code, 403)

        delete_response = self.client.delete(f"/api/v1/org/tokens/{self.used_token.id}/")
        self.assertEqual(delete_response.status_code, 403)

    def test_results_viewer_cannot_delete_batch(self):
        self.client.force_authenticate(self.viewer)
        delete_response = self.client.delete(f"/api/v1/org/token-batches/{self.batch.id}/")
        self.assertEqual(delete_response.status_code, 403)

    def test_org_isolation_for_used_token_actions(self):
        self.client.force_authenticate(self.manager)
        list_other_response = self.client.get(f"/api/v1/org/elections/{self.other_election.id}/used-tokens/")
        self.assertEqual(list_other_response.status_code, 403)

        reset_other_response = self.client.post(f"/api/v1/org/tokens/{self.other_token.id}/reset-vote/", {}, format="json")
        self.assertEqual(reset_other_response.status_code, 403)

        delete_other_batch_response = self.client.delete(f"/api/v1/org/token-batches/{self.other_batch.id}/")
        self.assertEqual(delete_other_batch_response.status_code, 403)

    def test_view_tokens_later_works_from_encrypted_db_archive(self):
        self.client.force_authenticate(self.manager)
        create_response = self.client.post(
            f"/api/v1/org/elections/{self.election.id}/token-batches/",
            {"label": "Archive Batch", "quantity": 3},
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        created_tokens = create_response.data["data"]["tokens"]
        batch_id = create_response.data["data"]["id"]

        batch = TokenBatch.objects.get(id=batch_id)
        self.assertTrue(batch.encrypted_tokens_blob)

        cache.clear()

        view_response = self.client.get(f"/api/v1/org/token-batches/{batch_id}/tokens/")
        self.assertEqual(view_response.status_code, 200)
        restored_tokens = view_response.data["data"]["tokens"]
        self.assertEqual(sorted(created_tokens), sorted(restored_tokens))

    def test_csv_export_still_works_after_cache_expiry(self):
        self.client.force_authenticate(self.manager)
        create_response = self.client.post(
            f"/api/v1/org/elections/{self.election.id}/token-batches/",
            {"label": "Csv Batch", "quantity": 2},
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        created_tokens = create_response.data["data"]["tokens"]
        batch_id = create_response.data["data"]["id"]

        cache.clear()

        export_response = self.client.get(f"/api/v1/org/token-batches/{batch_id}/export/csv/")
        self.assertEqual(export_response.status_code, 200)
        payload = export_response.content.decode("utf-8")
        self.assertIn(created_tokens[0], payload)

    def test_create_token_batch_without_expiry(self):
        self.client.force_authenticate(self.manager)
        response = self.client.post(
            f"/api/v1/org/elections/{self.election.id}/token-batches/",
            {"label": "No Expiry Batch", "quantity": 2},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["data"]["expires_at"])

        batch = TokenBatch.objects.get(id=response.data["data"]["id"])
        self.assertIsNone(batch.expires_at)

    def test_create_token_batch_with_expiry(self):
        self.client.force_authenticate(self.manager)
        expires_at = timezone.now() + timedelta(days=2)
        response = self.client.post(
            f"/api/v1/org/elections/{self.election.id}/token-batches/",
            {"label": "Expiring Batch", "quantity": 2, "expires_at": expires_at.isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(response.data["data"]["expires_at"])

        batch = TokenBatch.objects.get(id=response.data["data"]["id"])
        self.assertIsNotNone(batch.expires_at)

    def test_expired_batch_cleanup_deletes_only_expired_batches(self):
        self.batch.expires_at = timezone.now() - timedelta(minutes=1)
        self.batch.save(update_fields=["expires_at", "updated_at"])

        future_batch = TokenBatch.objects.create(
            election=self.election,
            label="Future Batch",
            quantity=2,
            expires_at=timezone.now() + timedelta(days=1),
        )
        future_token = Token.objects.create(
            batch=future_batch,
            election=self.election,
            token_hash="hash-future-1",
            token_hint="FUT001",
            status=TokenStatus.ACTIVE,
        )

        deleted_count = run_expired_batch_cleanup()
        self.assertEqual(deleted_count, 1)
        self.assertFalse(TokenBatch.objects.filter(id=self.batch.id).exists())
        self.assertFalse(Token.objects.filter(batch_id=self.batch.id).exists())
        self.assertFalse(Ballot.objects.filter(id=self.ballot.id).exists())
        self.assertTrue(TokenBatch.objects.filter(id=future_batch.id).exists())
        self.assertTrue(Token.objects.filter(id=future_token.id).exists())
