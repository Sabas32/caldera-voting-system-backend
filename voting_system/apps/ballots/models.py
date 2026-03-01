from __future__ import annotations

from django.db import models

from voting_system.apps.common.models import TimeStampedModel, UUIDModel
from voting_system.apps.elections.models import Election, Post
from voting_system.apps.tokens.models import Token


class Ballot(UUIDModel, TimeStampedModel):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name="ballots")
    token = models.OneToOneField(Token, on_delete=models.PROTECT, related_name="ballot")
    receipt_code = models.CharField(max_length=16, unique=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-submitted_at",)
        constraints = [
            models.UniqueConstraint(fields=("token",), name="uniq_ballot_per_token"),
        ]


class BallotChoice(UUIDModel, TimeStampedModel):
    ballot = models.ForeignKey(Ballot, on_delete=models.CASCADE, related_name="choices")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="choices")
    candidate = models.ForeignKey(
        "elections.Candidate",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="choices",
    )
    abstained = models.BooleanField(default=False)

    class Meta:
        ordering = ("post__sort_order", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("ballot", "post", "candidate"),
                name="uniq_ballot_post_candidate",
            ),
        ]
