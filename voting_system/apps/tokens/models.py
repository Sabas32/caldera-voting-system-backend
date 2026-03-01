from __future__ import annotations

from django.conf import settings
from django.db import models

from voting_system.apps.common.models import TimeStampedModel, UUIDModel
from voting_system.apps.elections.models import Election


class TokenBatch(UUIDModel, TimeStampedModel):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name="token_batches")
    label = models.CharField(max_length=120)
    quantity = models.PositiveIntegerField()
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked = models.BooleanField(default=False)
    encrypted_tokens_blob = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_token_batches",
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.election.title} / {self.label}"


class TokenStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    USED = "USED", "Used"
    REVOKED = "REVOKED", "Revoked"


class Token(UUIDModel, TimeStampedModel):
    batch = models.ForeignKey(TokenBatch, on_delete=models.CASCADE, related_name="tokens")
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name="tokens")
    token_hash = models.CharField(max_length=128, unique=True)
    token_hint = models.CharField(max_length=8)
    status = models.CharField(max_length=12, choices=TokenStatus.choices, default=TokenStatus.ACTIVE)
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"{self.election.slug}:{self.token_hint}"
