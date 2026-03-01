from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from voting_system.apps.accounts.models import OrgMembership
from voting_system.apps.audit.services import log_event

User = get_user_model()


def create_or_update_membership(*, organization, payload, actor):
    user, created = User.objects.get_or_create(
        email=payload["email"],
        defaults={
            "first_name": payload.get("first_name", ""),
            "last_name": payload.get("last_name", ""),
            "is_active": True,
        },
    )
    password = payload.get("password") or get_random_string(12)
    if created or payload.get("password"):
        user.set_password(password)
        user.save(update_fields=["password", "updated_at"])

    membership, membership_created = OrgMembership.objects.update_or_create(
        user=user,
        organization=organization,
        defaults={"role": payload["role"], "is_active": True},
    )
    log_event(
        actor=actor,
        organization=organization,
        action="ORG_USER_CREATED" if membership_created else "ORG_USER_ROLE_CHANGED",
        target_type="membership",
        target_id=str(membership.id),
        metadata={"email": user.email, "role": membership.role},
    )
    return membership, password if created or payload.get("password") else None


def update_membership(*, membership, payload, actor):
    reset_password = payload.pop("reset_password", False)
    requested_password = payload.pop("password", None)

    old_role = membership.role
    old_active = membership.is_active
    for field, value in payload.items():
        setattr(membership, field, value)
    membership.save()

    if old_role != membership.role:
        log_event(
            actor=actor,
            organization=membership.organization,
            action="ORG_USER_ROLE_CHANGED",
            target_type="membership",
            target_id=str(membership.id),
            metadata={"from": old_role, "to": membership.role},
        )
    if old_active and not membership.is_active:
        log_event(
            actor=actor,
            organization=membership.organization,
            action="ORG_USER_DEACTIVATED",
            target_type="membership",
            target_id=str(membership.id),
            metadata={"email": membership.user.email},
        )

    generated_password = None
    if reset_password:
        generated_password = requested_password or get_random_string(12)
        membership.user.set_password(generated_password)
        membership.user.save(update_fields=["password", "updated_at"])
        log_event(
            actor=actor,
            organization=membership.organization,
            action="ORG_USER_PASSWORD_RESET",
            target_type="membership",
            target_id=str(membership.id),
            metadata={"email": membership.user.email},
        )

    return membership, generated_password
