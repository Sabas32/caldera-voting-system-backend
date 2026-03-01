from __future__ import annotations

import os
import sys
from datetime import timedelta
from pathlib import Path

import django
from django.utils import timezone

# Allow running via `python scripts/seed_demo_data.py` from any shell.
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voting_system.config.settings_dev")
django.setup()

from voting_system.apps.accounts.models import MembershipRole, OrgMembership, User
from voting_system.apps.common.utils import hash_token
from voting_system.apps.elections.models import Election, ElectionStatus, Post
from voting_system.apps.organizations.models import Organization
from voting_system.apps.tokens.models import Token, TokenBatch


def run():
    org, _ = Organization.objects.get_or_create(name="Demo University", slug="demo-university")

    system_admin, _ = User.objects.get_or_create(
        email="system@demo.local",
        defaults={"is_system_admin": True, "is_staff": True, "is_active": True},
    )
    system_admin.set_password("Admin12345!")
    system_admin.save()

    org_admin, _ = User.objects.get_or_create(email="orgadmin@demo.local", defaults={"is_active": True})
    org_admin.set_password("Admin12345!")
    org_admin.save()

    OrgMembership.objects.get_or_create(
        user=org_admin,
        organization=org,
        defaults={"role": MembershipRole.ORG_ADMIN, "is_active": True},
    )

    election, _ = Election.objects.get_or_create(
        organization=org,
        slug="student-council-2026",
        defaults={
            "title": "Student Council Election 2026",
            "status": ElectionStatus.LIVE,
            "opens_at": timezone.now() - timedelta(hours=1),
            "closes_at": timezone.now() + timedelta(days=1),
            "created_by": org_admin,
            "public_results_enabled": True,
        },
    )

    post, _ = Post.objects.get_or_create(
        election=election,
        title="President",
        defaults={"max_selections": 1, "sort_order": 1},
    )
    post.candidates.get_or_create(name="Alex Morgan", defaults={"sort_order": 1, "status": "APPROVED"})
    post.candidates.get_or_create(name="Taylor Reed", defaults={"sort_order": 2, "status": "APPROVED"})

    batch, _ = TokenBatch.objects.get_or_create(
        election=election,
        label="Demo Batch",
        defaults={"quantity": 2, "expires_at": timezone.now() + timedelta(days=1), "created_by": org_admin},
    )

    for token in ("DEMO0001", "DEMO0002"):
        Token.objects.get_or_create(
            batch=batch,
            election=election,
            token_hash=hash_token(token),
            defaults={"token_hint": token[-6:]},
        )

    print("Demo data ready")
    print("System admin: system@demo.local / Admin12345!")
    print("Org admin: orgadmin@demo.local / Admin12345!")
    print("Demo tokens: DEMO0001, DEMO0002")


if __name__ == "__main__":
    run()
