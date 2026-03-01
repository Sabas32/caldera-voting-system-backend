from __future__ import annotations

from voting_system.apps.audit.services import log_event


def log_org_created(*, actor, organization):
    log_event(
        actor=actor,
        organization=organization,
        action="ORG_CREATED",
        target_type="organization",
        target_id=str(organization.id),
        metadata={"name": organization.name, "slug": organization.slug},
    )


def log_org_updated(*, actor, organization):
    log_event(
        actor=actor,
        organization=organization,
        action="ORG_UPDATED",
        target_type="organization",
        target_id=str(organization.id),
        metadata={"name": organization.name, "slug": organization.slug, "status": organization.status},
    )
