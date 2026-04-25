from __future__ import annotations

from django.conf import settings
from django.utils import timezone
from rest_framework import permissions
from rest_framework.views import APIView

from voting_system.apps.ballots.models import Ballot
from voting_system.apps.ballots.serializers import BallotSubmitSerializer, VoteTokenLoginSerializer
from voting_system.apps.ballots.services import BallotValidationError, get_results_payload, submit_ballot
from voting_system.apps.common.responses import error_response, success_response
from voting_system.apps.common.throttling import TokenLoginThrottle, TokenSubmitThrottle
from voting_system.apps.common.utils import build_voter_session, hash_token, parse_voter_session
from voting_system.apps.elections.models import Election, ElectionStatus, PostVoteAccessMode
from voting_system.apps.tokens.models import Token, TokenStatus


def _get_voter_session(request):
    raw = request.COOKIES.get(settings.VOTER_SESSION_COOKIE)
    if not raw:
        return None
    try:
        return parse_voter_session(raw)
    except Exception:
        return None


def _resolve_voter_session_token(*, request, election):
    session_data = _get_voter_session(request)
    if not session_data or session_data.get("election_slug") != election.slug:
        return None
    return Token.objects.filter(id=session_data.get("token_id"), election=election).first()


def _voter_results_window(*, election, token, ballot):
    if not election.voter_results_after_vote_enabled:
        return False, election.voter_results_window_starts_at, None
    if election.post_vote_access_mode == PostVoteAccessMode.FULLY_BLOCK_AFTER_VOTE:
        return False, election.voter_results_window_starts_at, None
    if not token or token.status != TokenStatus.USED or not ballot:
        return False, election.voter_results_window_starts_at, None

    now = timezone.now()
    window_start = election.voter_results_window_starts_at
    effective_deadline = election.voter_results_window_ends_at

    if window_start and now < window_start:
        return False, window_start, effective_deadline
    if effective_deadline and now > effective_deadline:
        return False, window_start, effective_deadline
    return True, window_start, effective_deadline


class VoteTokenLoginView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    throttle_classes = (TokenLoginThrottle,)

    def post(self, request):
        serializer = VoteTokenLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hashed = hash_token(serializer.validated_data["token"].strip().upper())

        token = Token.objects.select_related("election__organization", "batch").filter(token_hash=hashed).first()
        if not token:
            return error_response("Invalid token", status_code=401)

        election = token.election
        if token.batch.revoked or token.status == TokenStatus.REVOKED:
            return error_response("Token revoked", status_code=403)
        if token.batch.expires_at and token.batch.expires_at < timezone.now():
            return error_response("Token expired", status_code=403)

        if token.status == TokenStatus.USED:
            if election.post_vote_access_mode == PostVoteAccessMode.FULLY_BLOCK_AFTER_VOTE:
                return error_response("Token already used", status_code=403)
        elif token.status == TokenStatus.ACTIVE and election.status != ElectionStatus.LIVE:
            return error_response("Election is not live", status_code=403)

        session_value = build_voter_session(
            {
                "token_id": str(token.id),
                "election_id": str(election.id),
                "election_slug": election.slug,
            }
        )
        used_ballot = Ballot.objects.filter(token=token).first() if token.status == TokenStatus.USED else None
        _, voter_results_view_from, voter_results_view_until = _voter_results_window(
            election=election,
            token=token,
            ballot=used_ballot,
        )

        response = success_response(
            {
                "election_slug": election.slug,
                "organization_name": election.organization.name,
                "status": token.status,
                "post_vote_access_mode": election.post_vote_access_mode,
                "primary_color_override": election.organization.primary_color_override,
                "voter_auto_logout_seconds": election.voter_auto_logout_seconds,
                "voter_results_after_vote_enabled": election.voter_results_after_vote_enabled,
                "voter_results_view_from": voter_results_view_from,
                "voter_results_view_until": voter_results_view_until,
            },
            "Token accepted",
        )
        response.set_cookie(
            settings.VOTER_SESSION_COOKIE,
            session_value,
            httponly=True,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite=settings.SESSION_COOKIE_SAMESITE,
            max_age=settings.VOTER_SESSION_MAX_AGE_SECONDS,
            domain=settings.SESSION_COOKIE_DOMAIN,
            path="/",
        )
        return response


class VoteLogoutView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    def get(self, request):
        response = success_response(message="Voter logged out")
        response.delete_cookie(
            settings.VOTER_SESSION_COOKIE,
            path="/",
            domain=settings.SESSION_COOKIE_DOMAIN,
            samesite=settings.SESSION_COOKIE_SAMESITE,
        )
        return response

    def post(self, request):
        response = success_response(message="Voter logged out")
        response.delete_cookie(
            settings.VOTER_SESSION_COOKIE,
            path="/",
            domain=settings.SESSION_COOKIE_DOMAIN,
            samesite=settings.SESSION_COOKIE_SAMESITE,
        )
        return response


class VoteBallotView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    def get(self, request, slug):
        session_data = _get_voter_session(request)
        if not session_data or session_data.get("election_slug") != slug:
            return error_response("Session invalid", status_code=401)

        election = Election.objects.select_related("organization").prefetch_related("posts__candidates").filter(slug=slug).first()
        token = Token.objects.filter(id=session_data.get("token_id"), election=election).first()
        if not election or not token:
            return error_response("Unauthorized", status_code=401)
        if election.status != ElectionStatus.LIVE:
            return error_response("Election is not live", status_code=403)
        if token.status != TokenStatus.ACTIVE:
            return error_response("Token already used", status_code=403)

        posts = []
        for post in election.posts.all():
            posts.append(
                {
                    "id": str(post.id),
                    "title": post.title,
                    "description": post.description,
                    "max_selections": post.max_selections,
                    "allow_abstain": post.allow_abstain,
                    "candidates": [
                        {
                            "id": str(candidate.id),
                            "name": candidate.name,
                            "description": candidate.description,
                            "image_url": candidate.image_url,
                        }
                        for candidate in post.candidates.filter(status="APPROVED")
                    ],
                }
            )

        return success_response(
            {
                "election": {
                    "id": str(election.id),
                    "title": election.title,
                    "slug": election.slug,
                    "organization_name": election.organization.name,
                    "instructions": election.ballot_instructions,
                    "status": election.status,
                    "primary_color_override": election.organization.primary_color_override,
                },
                "posts": posts,
            }
        )


class VoteSubmitView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()
    throttle_classes = (TokenSubmitThrottle,)

    def post(self, request, slug):
        session_data = _get_voter_session(request)
        if not session_data or session_data.get("election_slug") != slug:
            return error_response("Session invalid", status_code=401)

        election = Election.objects.prefetch_related("posts").filter(slug=slug).first()
        token = Token.objects.filter(id=session_data.get("token_id"), election=election).first()
        if not election or not token:
            return error_response("Unauthorized", status_code=401)

        serializer = BallotSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            ballot = submit_ballot(
                election=election,
                token=token,
                selections=serializer.validated_data["selections"],
                actor_ip=request.META.get("REMOTE_ADDR"),
            )
        except BallotValidationError as exc:
            return error_response(str(exc), status_code=400)

        next_path = f"/e/{slug}/status"
        if election.post_vote_access_mode == PostVoteAccessMode.FULLY_BLOCK_AFTER_VOTE:
            next_path = "/vote"

        return success_response(
            {
                "receipt_code": ballot.receipt_code,
                "submitted_at": ballot.submitted_at,
                "redirect": next_path,
                "mode": election.post_vote_access_mode,
            },
            "Ballot submitted",
        )


class VoteStatusView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    def get(self, request, slug):
        session_data = _get_voter_session(request)
        if not session_data or session_data.get("election_slug") != slug:
            return error_response("Session invalid", status_code=401)

        election = Election.objects.select_related("organization").filter(slug=slug).first()
        token = Token.objects.filter(id=session_data.get("token_id"), election=election).first()
        if not election or not token:
            return error_response("Unauthorized", status_code=401)
        if election.post_vote_access_mode == PostVoteAccessMode.FULLY_BLOCK_AFTER_VOTE:
            return error_response("Token already used", status_code=403)

        ballot = Ballot.objects.filter(token=token).first()
        if not ballot:
            return error_response("No ballot submitted yet", status_code=404)

        voter_results_available, voter_results_view_from, voter_results_view_until = _voter_results_window(
            election=election,
            token=token,
            ballot=ballot,
        )

        return success_response(
            {
                "receipt_code": ballot.receipt_code,
                "submitted_at": ballot.submitted_at,
                "voter_results_access_enabled": election.voter_results_after_vote_enabled,
                "voter_results_available": voter_results_available,
                "voter_results_view_from": voter_results_view_from,
                "voter_results_view_until": voter_results_view_until,
                "organization_name": election.organization.name,
                "primary_color_override": election.organization.primary_color_override,
                "public_results_available": (
                    election.status == ElectionStatus.CLOSED
                    and election.publish_results
                    and election.public_results_enabled
                ),
            }
        )


class VotePublicResultsView(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    def get(self, request, slug):
        election = Election.objects.select_related("organization").prefetch_related("posts__candidates").filter(slug=slug).first()
        if not election:
            return error_response("Election not found", status_code=404)

        is_public_allowed = (
            election.status in (ElectionStatus.CLOSED, ElectionStatus.ARCHIVED)
            and election.publish_results
            and election.public_results_enabled
        )

        if not is_public_allowed:
            token = _resolve_voter_session_token(request=request, election=election)
            ballot = Ballot.objects.filter(token=token).first() if token else None
            voter_allowed, _, _ = _voter_results_window(
                election=election,
                token=token,
                ballot=ballot,
            )
            if not voter_allowed:
                return error_response("Public results are unavailable", status_code=403)

        return success_response(get_results_payload(election))
