from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from voting_system.apps.common.models import TimeStampedModel, UUIDModel
from voting_system.apps.organizations.models import Organization


class ElectionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SCHEDULED = "SCHEDULED", "Scheduled"
    LIVE = "LIVE", "Live"
    CLOSED = "CLOSED", "Closed"
    ARCHIVED = "ARCHIVED", "Archived"


class ResultsVisibility(models.TextChoices):
    HIDDEN_UNTIL_CLOSED = "HIDDEN_UNTIL_CLOSED", "Hidden until closed"
    LIVE_ALLOWED = "LIVE_ALLOWED", "Live allowed"


class PostVoteAccessMode(models.TextChoices):
    READ_ONLY_AFTER_VOTE = "READ_ONLY_AFTER_VOTE", "Read-only after vote"
    FULLY_BLOCK_AFTER_VOTE = "FULLY_BLOCK_AFTER_VOTE", "Fully block after vote"


class CandidateStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    APPROVED = "APPROVED", "Approved"


class Election(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="elections")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=ElectionStatus.choices, default=ElectionStatus.DRAFT)
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)

    results_visibility = models.CharField(
        max_length=32,
        choices=ResultsVisibility.choices,
        default=ResultsVisibility.HIDDEN_UNTIL_CLOSED,
    )
    publish_results = models.BooleanField(default=False)
    public_results_enabled = models.BooleanField(default=False)
    post_vote_access_mode = models.CharField(
        max_length=32,
        choices=PostVoteAccessMode.choices,
        default=PostVoteAccessMode.READ_ONLY_AFTER_VOTE,
    )
    voter_auto_logout_seconds = models.PositiveIntegerField(
        default=60,
        validators=[MinValueValidator(30), MaxValueValidator(86400)],
    )
    voter_results_after_vote_enabled = models.BooleanField(
        default=False,
        help_text="Allow voters to view results after they submit.",
    )
    voter_results_view_window_seconds = models.PositiveIntegerField(
        default=600,
        validators=[MinValueValidator(30), MaxValueValidator(86400)],
        help_text="How long voters can access results after submitting (in seconds).",
    )
    voter_results_window_starts_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional absolute start time when voters can begin viewing results.",
    )
    voter_results_window_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional absolute end time when voter results access closes.",
    )
    ballot_instructions = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_elections",
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("organization", "title"), name="uniq_election_title_per_org"),
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}: {self.title}"


class Post(UUIDModel, TimeStampedModel):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    max_selections = models.PositiveSmallIntegerField(default=1)
    allow_abstain = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ("sort_order", "created_at")

    def __str__(self) -> str:
        return f"{self.election.title} - {self.title}"


class Candidate(UUIDModel, TimeStampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="candidates")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    sort_order = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=16, choices=CandidateStatus.choices, default=CandidateStatus.APPROVED)

    class Meta:
        ordering = ("sort_order", "created_at")

    def __str__(self) -> str:
        return self.name
