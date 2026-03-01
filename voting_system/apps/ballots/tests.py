from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.test import APITestCase

from voting_system.apps.ballots.models import Ballot, BallotChoice
from voting_system.apps.accounts.models import MembershipRole, OrgMembership, User
from voting_system.apps.common.utils import hash_token
from voting_system.apps.elections.models import Election, ElectionStatus, Post, PostVoteAccessMode, ResultsVisibility
from voting_system.apps.organizations.models import Organization
from voting_system.apps.tokens.models import Token, TokenBatch, TokenStatus


class VotingFlowTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Org 1", slug="org-1")
        self.election = Election.objects.create(
            organization=self.org,
            title="General Election",
            slug="general-election",
            status=ElectionStatus.LIVE,
            opens_at=timezone.now() - timedelta(hours=1),
            closes_at=timezone.now() + timedelta(hours=1),
        )
        self.post = Post.objects.create(election=self.election, title="President", max_selections=1, sort_order=1)
        self.c1 = self.post.candidates.create(name="Candidate A", status="APPROVED", sort_order=1)
        self.c2 = self.post.candidates.create(name="Candidate B", status="APPROVED", sort_order=2)

    def _make_token(self, plaintext="TOKEN1234", **kwargs):
        batch = TokenBatch.objects.create(
            election=self.election,
            label="Batch",
            quantity=1,
            expires_at=kwargs.pop("expires_at", timezone.now() + timedelta(hours=2)),
        )
        return Token.objects.create(
            batch=batch,
            election=self.election,
            token_hash=hash_token(plaintext),
            token_hint=plaintext[-6:],
            **kwargs,
        )

    def test_token_login_rejects_invalid(self):
        response = self.client.post("/api/v1/vote/token-login/", {"token": "INVALID"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_vote_logout_clears_voter_cookie(self):
        self._make_token(plaintext="LOGOUT01")
        login_response = self.client.post("/api/v1/vote/token-login/", {"token": "LOGOUT01"}, format="json")
        self.assertEqual(login_response.status_code, 200)
        self.assertIn(settings.VOTER_SESSION_COOKIE, login_response.cookies)
        self.assertEqual(login_response.data["data"]["voter_auto_logout_seconds"], 60)

        logout_response = self.client.post("/api/v1/vote/logout/", {}, format="json")
        self.assertEqual(logout_response.status_code, 200)
        self.assertIn(settings.VOTER_SESSION_COOKIE, logout_response.cookies)
        self.assertEqual(logout_response.cookies[settings.VOTER_SESSION_COOKIE]["max-age"], 0)

    def test_token_login_returns_org_configured_auto_logout_seconds(self):
        self.election.voter_auto_logout_seconds = 180
        self.election.voter_results_after_vote_enabled = True
        self.election.save(
            update_fields=[
                "voter_auto_logout_seconds",
                "voter_results_after_vote_enabled",
                "updated_at",
            ]
        )
        self._make_token(plaintext="TIMECFG1")

        response = self.client.post("/api/v1/vote/token-login/", {"token": "TIMECFG1"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["voter_auto_logout_seconds"], 180)
        self.assertTrue(response.data["data"]["voter_results_after_vote_enabled"])
        self.assertIsNone(response.data["data"]["voter_results_view_from"])
        self.assertIsNone(response.data["data"]["voter_results_view_until"])

    def test_token_login_rejects_revoked_and_expired(self):
        token = self._make_token(plaintext="REVOKED1", status=TokenStatus.REVOKED)
        response = self.client.post("/api/v1/vote/token-login/", {"token": "REVOKED1"}, format="json")
        self.assertEqual(response.status_code, 403)

        token.batch.expires_at = timezone.now() - timedelta(minutes=1)
        token.batch.save(update_fields=["expires_at"])
        token.status = TokenStatus.ACTIVE
        token.save(update_fields=["status", "updated_at"])
        response = self.client.post("/api/v1/vote/token-login/", {"token": "REVOKED1"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_used_token_block_mode(self):
        self.election.post_vote_access_mode = PostVoteAccessMode.FULLY_BLOCK_AFTER_VOTE
        self.election.save(update_fields=["post_vote_access_mode", "updated_at"])
        self._make_token(plaintext="USEDMODE", status=TokenStatus.USED, used_at=timezone.now())
        response = self.client.post("/api/v1/vote/token-login/", {"token": "USEDMODE"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_ballot_endpoint_requires_live_election(self):
        self._make_token(plaintext="NOTLIVE")
        login_response = self.client.post("/api/v1/vote/token-login/", {"token": "NOTLIVE"}, format="json")
        self.assertEqual(login_response.status_code, 200)

        self.election.status = ElectionStatus.SCHEDULED
        self.election.save(update_fields=["status", "updated_at"])
        response = self.client.get(f"/api/v1/vote/elections/{self.election.slug}/ballot/")
        self.assertEqual(response.status_code, 403)

    def test_token_login_rejects_non_live_election_for_unused_token(self):
        self.election.status = ElectionStatus.DRAFT
        self.election.save(update_fields=["status", "updated_at"])
        self._make_token(plaintext="DRAFT001")

        response = self.client.post("/api/v1/vote/token-login/", {"token": "DRAFT001"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["message"], "Election is not live")

    def test_ballot_constraints_single_choice(self):
        self._make_token(plaintext="SUBMIT1")
        login_response = self.client.post("/api/v1/vote/token-login/", {"token": "SUBMIT1"}, format="json")
        self.assertEqual(login_response.status_code, 200)

        payload = {
            "selections": [
                {
                    "post_id": str(self.post.id),
                    "candidate_ids": [str(self.c1.id), str(self.c2.id)],
                    "abstain": False,
                }
            ]
        }
        response = self.client.post(f"/api/v1/vote/elections/{self.election.slug}/submit/", payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_public_results_gating(self):
        self._make_token(plaintext="RESULTS1")
        self.election.status = ElectionStatus.CLOSED
        self.election.results_visibility = ResultsVisibility.HIDDEN_UNTIL_CLOSED
        self.election.publish_results = False
        self.election.public_results_enabled = True
        self.election.save()

        response = self.client.get(f"/api/v1/vote/elections/{self.election.slug}/results/")
        self.assertEqual(response.status_code, 403)

        self.election.publish_results = True
        self.election.save(update_fields=["publish_results", "updated_at"])
        response = self.client.get(f"/api/v1/vote/elections/{self.election.slug}/results/")
        self.assertEqual(response.status_code, 200)

    def test_public_results_include_zero_vote_candidates(self):
        token = self._make_token(plaintext="RESULTS2", status=TokenStatus.USED, used_at=timezone.now())
        ballot = Ballot.objects.create(election=self.election, token=token, receipt_code="RESZERO001")
        BallotChoice.objects.create(ballot=ballot, post=self.post, candidate=self.c1, abstained=False)

        self.election.status = ElectionStatus.CLOSED
        self.election.publish_results = True
        self.election.public_results_enabled = True
        self.election.save(update_fields=["status", "publish_results", "public_results_enabled", "updated_at"])

        response = self.client.get(f"/api/v1/vote/elections/{self.election.slug}/results/")
        self.assertEqual(response.status_code, 200)
        post_payload = response.data["data"]["posts"][0]
        self.assertEqual(len(post_payload["candidates"]), 2)

        candidates = {item["name"]: item for item in post_payload["candidates"]}
        self.assertEqual(candidates["Candidate A"]["votes"], 1)
        self.assertEqual(candidates["Candidate B"]["votes"], 0)

    def test_ballot_constraints_multi_choice_and_abstain(self):
        senate = Post.objects.create(
            election=self.election,
            title="Senate",
            max_selections=2,
            allow_abstain=True,
            sort_order=2,
        )
        c3 = senate.candidates.create(name="Candidate C", status="APPROVED", sort_order=1)
        c4 = senate.candidates.create(name="Candidate D", status="APPROVED", sort_order=2)
        c5 = senate.candidates.create(name="Candidate E", status="APPROVED", sort_order=3)

        self._make_token(plaintext="MULTI001")
        login_response = self.client.post("/api/v1/vote/token-login/", {"token": "MULTI001"}, format="json")
        self.assertEqual(login_response.status_code, 200)

        invalid_payload = {
            "selections": [
                {"post_id": str(self.post.id), "candidate_ids": [str(self.c1.id)], "abstain": False},
                {"post_id": str(senate.id), "candidate_ids": [str(c3.id), str(c4.id), str(c5.id)], "abstain": False},
            ]
        }
        invalid_response = self.client.post(
            f"/api/v1/vote/elections/{self.election.slug}/submit/",
            invalid_payload,
            format="json",
        )
        self.assertEqual(invalid_response.status_code, 400)

        self._make_token(plaintext="ABSTAIN1")
        login_response = self.client.post("/api/v1/vote/token-login/", {"token": "ABSTAIN1"}, format="json")
        self.assertEqual(login_response.status_code, 200)
        valid_payload = {
            "selections": [
                {"post_id": str(self.post.id), "candidate_ids": [str(self.c1.id)], "abstain": False},
                {"post_id": str(senate.id), "candidate_ids": [], "abstain": True},
            ]
        }
        valid_response = self.client.post(
            f"/api/v1/vote/elections/{self.election.slug}/submit/",
            valid_payload,
            format="json",
        )
        self.assertEqual(valid_response.status_code, 200)

    def test_read_only_after_vote_status_access(self):
        token = self._make_token(plaintext="READONLY", status=TokenStatus.USED, used_at=timezone.now())
        self.election.post_vote_access_mode = PostVoteAccessMode.READ_ONLY_AFTER_VOTE
        self.election.save(update_fields=["post_vote_access_mode", "updated_at"])

        Ballot.objects.create(election=self.election, token=token, receipt_code="ABC123XYZ9")
        login_response = self.client.post("/api/v1/vote/token-login/", {"token": "READONLY"}, format="json")
        self.assertEqual(login_response.status_code, 200)
        self.assertIn("voter_results_view_until", login_response.data["data"])
        status_response = self.client.get(f"/api/v1/vote/elections/{self.election.slug}/status/")
        self.assertEqual(status_response.status_code, 200)
        self.assertIsNone(status_response.data["data"]["voter_results_view_from"])

    def test_voter_results_after_vote_window_allows_results_access(self):
        token = self._make_token(plaintext="VOTEVIEW", status=TokenStatus.USED, used_at=timezone.now())
        self.election.post_vote_access_mode = PostVoteAccessMode.READ_ONLY_AFTER_VOTE
        self.election.voter_results_after_vote_enabled = True
        self.election.voter_results_window_starts_at = timezone.now() - timedelta(minutes=1)
        self.election.voter_results_window_ends_at = timezone.now() + timedelta(minutes=10)
        self.election.save(
            update_fields=[
                "post_vote_access_mode",
                "voter_results_after_vote_enabled",
                "voter_results_window_starts_at",
                "voter_results_window_ends_at",
                "updated_at",
            ]
        )
        Ballot.objects.create(election=self.election, token=token, receipt_code="VIEW123456")

        login_response = self.client.post("/api/v1/vote/token-login/", {"token": "VOTEVIEW"}, format="json")
        self.assertEqual(login_response.status_code, 200)

        status_response = self.client.get(f"/api/v1/vote/elections/{self.election.slug}/status/")
        self.assertEqual(status_response.status_code, 200)
        self.assertTrue(status_response.data["data"]["voter_results_access_enabled"])
        self.assertTrue(status_response.data["data"]["voter_results_available"])
        self.assertIsNotNone(status_response.data["data"]["voter_results_view_until"])

        results_response = self.client.get(f"/api/v1/vote/elections/{self.election.slug}/results/")
        self.assertEqual(results_response.status_code, 200)

        self.election.voter_results_window_ends_at = timezone.now() - timedelta(seconds=1)
        self.election.save(update_fields=["voter_results_window_ends_at", "updated_at"])
        expired_results_response = self.client.get(f"/api/v1/vote/elections/{self.election.slug}/results/")
        self.assertEqual(expired_results_response.status_code, 403)

    def test_voter_results_absolute_window_is_enforced(self):
        token = self._make_token(plaintext="WINLOCK1", status=TokenStatus.USED, used_at=timezone.now())
        self.election.post_vote_access_mode = PostVoteAccessMode.READ_ONLY_AFTER_VOTE
        self.election.voter_results_after_vote_enabled = True
        self.election.voter_results_window_starts_at = timezone.now() + timedelta(minutes=5)
        self.election.voter_results_window_ends_at = timezone.now() + timedelta(minutes=20)
        self.election.save(
            update_fields=[
                "post_vote_access_mode",
                "voter_results_after_vote_enabled",
                "voter_results_window_starts_at",
                "voter_results_window_ends_at",
                "updated_at",
            ]
        )
        ballot = Ballot.objects.create(election=self.election, token=token, receipt_code="ABSWINDOW1")
        ballot.submitted_at = timezone.now()
        ballot.save(update_fields=["submitted_at", "updated_at"])

        login_response = self.client.post("/api/v1/vote/token-login/", {"token": "WINLOCK1"}, format="json")
        self.assertEqual(login_response.status_code, 200)
        self.assertIsNotNone(login_response.data["data"]["voter_results_view_from"])

        before_window_status = self.client.get(f"/api/v1/vote/elections/{self.election.slug}/status/")
        self.assertEqual(before_window_status.status_code, 200)
        self.assertFalse(before_window_status.data["data"]["voter_results_available"])
        before_window_results = self.client.get(f"/api/v1/vote/elections/{self.election.slug}/results/")
        self.assertEqual(before_window_results.status_code, 403)

        self.election.voter_results_window_starts_at = timezone.now() - timedelta(minutes=1)
        self.election.voter_results_window_ends_at = timezone.now() + timedelta(minutes=5)
        self.election.save(update_fields=["voter_results_window_starts_at", "voter_results_window_ends_at", "updated_at"])
        inside_window_results = self.client.get(f"/api/v1/vote/elections/{self.election.slug}/results/")
        self.assertEqual(inside_window_results.status_code, 200)

    def test_org_results_visibility_live_allowed(self):
        manager = User.objects.create_user(email="viewer@example.com", password="Password123!")
        OrgMembership.objects.create(
            user=manager,
            organization=self.org,
            role=MembershipRole.RESULTS_VIEWER,
            is_active=True,
        )
        self.election.results_visibility = ResultsVisibility.HIDDEN_UNTIL_CLOSED
        self.election.status = ElectionStatus.LIVE
        self.election.save(update_fields=["results_visibility", "status", "updated_at"])

        self.client.force_authenticate(manager)
        hidden_response = self.client.get(f"/api/v1/org/elections/{self.election.id}/results/")
        self.assertEqual(hidden_response.status_code, 403)

        self.election.results_visibility = ResultsVisibility.LIVE_ALLOWED
        self.election.save(update_fields=["results_visibility", "updated_at"])
        live_allowed_response = self.client.get(f"/api/v1/org/elections/{self.election.id}/results/")
        self.assertEqual(live_allowed_response.status_code, 200)
