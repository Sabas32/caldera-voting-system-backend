from __future__ import annotations

from django.conf import settings
from django.db import models

from voting_system.apps.common.models import TimeStampedModel, UUIDModel


class AuditLog(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=64)
    target_type = models.CharField(max_length=64)
    target_id = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    correlation_id = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.action} - {self.target_type}:{self.target_id}"
