from __future__ import annotations

from collections import defaultdict

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from voting_system.apps.audit.services import log_event
from voting_system.apps.ballots.models import Ballot, BallotChoice
from voting_system.apps.common.utils import generate_receipt_code
from voting_system.apps.elections.models import Candidate, CandidateStatus, ElectionStatus
from voting_system.apps.tokens.models import TokenStatus


class BallotValidationError(Exception):
    pass


@transaction.atomic
def submit_ballot(*, election, token, selections: list[dict], actor_ip: str | None = None):
    if election.status != ElectionStatus.LIVE:
        raise BallotValidationError("Election is not live")

    locked_token = token.__class__.objects.select_for_update().get(id=token.id)
    if locked_token.status != TokenStatus.ACTIVE:
        raise BallotValidationError("Token cannot submit a ballot")

    posts = list(election.posts.prefetch_related("candidates").all())
    post_map = {post.id: post for post in posts}
    by_post = {item["post_id"]: item for item in selections}

    if len(by_post) != len(posts):
        raise BallotValidationError("Selections must include every post")

    ballot = Ballot.objects.create(
        election=election,
        token=locked_token,
        receipt_code=generate_receipt_code(),
    )

    for post in posts:
        item = by_post.get(post.id)
        if not item:
            raise BallotValidationError("Missing selection for a post")

        candidate_ids = item.get("candidate_ids", [])
        abstain = item.get("abstain", False)

        if abstain:
            if not post.allow_abstain:
                raise BallotValidationError(f"Skipping this position is not allowed for post {post.title}")
            if candidate_ids:
                raise BallotValidationError(f"Cannot choose candidates and skip this position for post {post.title}")
            BallotChoice.objects.create(ballot=ballot, post=post, candidate=None, abstained=True)
            continue

        if len(candidate_ids) == 0:
            raise BallotValidationError(f"At least one candidate must be selected for post {post.title}")
        if len(candidate_ids) > post.max_selections:
            raise BallotValidationError(f"Selections exceed max selections for post {post.title}")

        valid_candidates = set(
            Candidate.objects.filter(
                id__in=candidate_ids,
                post=post,
                status="APPROVED",
            ).values_list("id", flat=True)
        )
        if len(valid_candidates) != len(set(candidate_ids)):
            raise BallotValidationError(f"Invalid candidate selection for post {post.title}")

        for candidate_id in set(candidate_ids):
            BallotChoice.objects.create(ballot=ballot, post=post, candidate_id=candidate_id, abstained=False)

    locked_token.status = TokenStatus.USED
    locked_token.used_at = timezone.now()
    locked_token.save(update_fields=["status", "used_at", "updated_at"])

    log_event(
        actor=None,
        organization=election.organization,
        action="BALLOT_SUBMITTED",
        target_type="ballot",
        target_id=str(ballot.id),
        metadata={"election": election.slug, "ip": actor_ip},
    )

    return ballot


def get_results_payload(election):
    result = []
    total_ballots = Ballot.objects.filter(election=election).count()
    for post in election.posts.prefetch_related("candidates").all():
        candidate_vote_rows = (
            BallotChoice.objects.filter(ballot__election=election, post=post, candidate__isnull=False)
            .values("candidate_id")
            .annotate(votes=Count("id"))
        )
        votes_by_candidate_id = {item["candidate_id"]: item["votes"] for item in candidate_vote_rows}
        ranked_candidates = sorted(
            [
                {
                    "candidate_id": str(candidate.id),
                    "name": candidate.name,
                    "votes": votes_by_candidate_id.get(candidate.id, 0),
                }
                for candidate in post.candidates.filter(status=CandidateStatus.APPROVED)
            ],
            key=lambda item: (-item["votes"], item["name"]),
        )

        top_votes = ranked_candidates[0]["votes"] if ranked_candidates else 0
        tied_leaders_count = sum(1 for item in ranked_candidates if item["votes"] == top_votes)

        result.append(
            {
                "post_id": str(post.id),
                "post_title": post.title,
                "total_ballots": total_ballots,
                "tie_detected": bool(top_votes and tied_leaders_count > 1),
                "candidates": [
                    {
                        "candidate_id": item["candidate_id"],
                        "name": item["name"],
                        "votes": item["votes"],
                        "percentage": (item["votes"] / total_ballots * 100) if total_ballots else 0,
                        "is_tied_leader": bool(top_votes and item["votes"] == top_votes),
                    }
                    for item in ranked_candidates
                ],
            }
        )
    return {
        "election": {
            "id": str(election.id),
            "title": election.title,
            "slug": election.slug,
            "organization_name": election.organization.name,
            "status": election.status,
            "publish_results": election.publish_results,
            "public_results_enabled": election.public_results_enabled,
            "primary_color_override": election.organization.primary_color_override,
        },
        "posts": result,
        "ballots_submitted": total_ballots,
    }
