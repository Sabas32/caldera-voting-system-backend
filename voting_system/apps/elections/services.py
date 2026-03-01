from __future__ import annotations

try:
    from celery import shared_task
except ImportError:  # pragma: no cover - fallback for environments without celery installed
    def shared_task(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator
from django.db import transaction
from django.utils.text import slugify
from django.utils import timezone

from voting_system.apps.audit.services import log_event
from voting_system.apps.elections.models import Candidate, Election, ElectionStatus, Post


class ElectionTransitionError(Exception):
    pass


def _build_unique_slug(*, organization, base_slug: str) -> str:
    slug = base_slug
    index = 2
    while Election.objects.filter(organization=organization, slug=slug).exists():
        slug = f"{base_slug}-{index}"
        index += 1
    return slug


@transaction.atomic
def duplicate_election(*, source: Election, actor, title: str | None = None, slug: str | None = None):
    base_title = title or f"{source.title} Copy"
    base_slug = slugify(slug or f"{source.slug}-copy")
    if not base_slug:
        base_slug = slugify(source.title) or "election-copy"
    unique_slug = _build_unique_slug(organization=source.organization, base_slug=base_slug)

    duplicate = Election.objects.create(
        organization=source.organization,
        title=base_title,
        slug=unique_slug,
        description=source.description,
        status=ElectionStatus.DRAFT,
        opens_at=source.opens_at,
        closes_at=source.closes_at,
        results_visibility=source.results_visibility,
        publish_results=False,
        public_results_enabled=source.public_results_enabled,
        post_vote_access_mode=source.post_vote_access_mode,
        voter_auto_logout_seconds=source.voter_auto_logout_seconds,
        voter_results_after_vote_enabled=source.voter_results_after_vote_enabled,
        voter_results_view_window_seconds=source.voter_results_view_window_seconds,
        voter_results_window_starts_at=source.voter_results_window_starts_at,
        voter_results_window_ends_at=source.voter_results_window_ends_at,
        ballot_instructions=source.ballot_instructions,
        created_by=actor,
    )

    for source_post in Post.objects.filter(election=source).order_by("sort_order", "created_at"):
        duplicated_post = Post.objects.create(
            election=duplicate,
            title=source_post.title,
            description=source_post.description,
            max_selections=source_post.max_selections,
            allow_abstain=source_post.allow_abstain,
            sort_order=source_post.sort_order,
        )
        candidate_rows = [
            Candidate(
                post=duplicated_post,
                name=candidate.name,
                description=candidate.description,
                image_url=candidate.image_url,
                sort_order=candidate.sort_order,
                status=candidate.status,
            )
            for candidate in Candidate.objects.filter(post=source_post).order_by("sort_order", "created_at")
        ]
        if candidate_rows:
            Candidate.objects.bulk_create(candidate_rows)

    log_event(
        actor=actor,
        organization=source.organization,
        action="ELECTION_CREATED",
        target_type="election",
        target_id=str(duplicate.id),
        metadata={"duplicated_from": str(source.id), "title": duplicate.title, "slug": duplicate.slug},
    )
    return duplicate


def change_election_status(*, election, action: str, actor, actor_role: str | None = None):
    if action == "schedule":
        if election.status != ElectionStatus.DRAFT:
            raise ElectionTransitionError("Only draft elections can be scheduled")
        if not election.opens_at:
            raise ElectionTransitionError("opens_at must be set before scheduling")
        # If opens_at is already in the past, transition directly to LIVE.
        election.status = ElectionStatus.LIVE if election.opens_at <= timezone.now() else ElectionStatus.SCHEDULED
    elif action == "close":
        if election.status not in (ElectionStatus.SCHEDULED, ElectionStatus.LIVE):
            raise ElectionTransitionError("Only scheduled/live elections can be closed")
        election.status = ElectionStatus.CLOSED
    elif action == "archive":
        if actor_role == "ELECTION_MANAGER":
            raise ElectionTransitionError("Only org admin can archive elections")
        if election.status != ElectionStatus.CLOSED:
            raise ElectionTransitionError("Only closed elections can be archived")
        election.status = ElectionStatus.ARCHIVED
    else:
        raise ElectionTransitionError("Unsupported action")

    election.save(update_fields=["status", "updated_at"])
    log_event(
        actor=actor,
        organization=election.organization,
        action="ELECTION_STATUS_CHANGED",
        target_type="election",
        target_id=str(election.id),
        metadata={"action": action, "status": election.status},
    )
    return election


def run_scheduled_transitions():
    now = timezone.now()
    scheduled = Election.objects.filter(status=ElectionStatus.SCHEDULED, opens_at__lte=now)
    live = Election.objects.filter(status=ElectionStatus.LIVE, closes_at__lte=now)

    for election in scheduled:
        election.status = ElectionStatus.LIVE
        election.save(update_fields=["status", "updated_at"])
        log_event(
            actor=None,
            organization=election.organization,
            action="ELECTION_STATUS_CHANGED",
            target_type="election",
            target_id=str(election.id),
            metadata={"action": "auto_open", "status": election.status},
        )

    for election in live:
        election.status = ElectionStatus.CLOSED
        election.save(update_fields=["status", "updated_at"])
        log_event(
            actor=None,
            organization=election.organization,
            action="ELECTION_STATUS_CHANGED",
            target_type="election",
            target_id=str(election.id),
            metadata={"action": "auto_close", "status": election.status},
        )


@shared_task(name="voting_system.apps.elections.services.run_scheduled_transitions_task")
def run_scheduled_transitions_task():
    run_scheduled_transitions()
