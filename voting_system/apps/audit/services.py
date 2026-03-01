from __future__ import annotations

from voting_system.apps.audit.models import AuditLog


def log_event(*, actor, organization, action: str, target_type: str, target_id: str, metadata: dict | None = None):
    AuditLog.objects.create(
        actor=actor,
        organization=organization,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata or {},
        correlation_id=getattr(actor, "_request_correlation_id", "") if actor else "",
    )
