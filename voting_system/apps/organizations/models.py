from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from voting_system.apps.common.models import TimeStampedModel, UUIDModel


class OrganizationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"


class Organization(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    status = models.CharField(max_length=16, choices=OrganizationStatus.choices, default=OrganizationStatus.ACTIVE)
    primary_color_override = models.CharField(max_length=16, blank=True)
    logo_url = models.URLField(blank=True)
    default_public_results_enabled = models.BooleanField(default=False)
    default_results_visibility = models.CharField(
        max_length=32,
        choices=(
            ("HIDDEN_UNTIL_CLOSED", "Hidden until closed"),
            ("LIVE_ALLOWED", "Live allowed"),
        ),
        default="HIDDEN_UNTIL_CLOSED",
    )
    voter_auto_logout_seconds = models.PositiveIntegerField(
        default=60,
        validators=[MinValueValidator(30), MaxValueValidator(3600)],
        help_text="Voter auto logout timeout in seconds.",
    )
    default_voter_results_after_vote_enabled = models.BooleanField(
        default=False,
        help_text="Allow voters to view election results after submitting a ballot.",
    )
    default_voter_results_view_window_seconds = models.PositiveIntegerField(
        default=600,
        validators=[MinValueValidator(30), MaxValueValidator(86400)],
        help_text="How long voters can view results after submission (in seconds).",
    )

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name
