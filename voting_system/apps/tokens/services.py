from __future__ import annotations

import base64
import hashlib
import json

try:
    from celery import shared_task
except ImportError:  # pragma: no cover - fallback for environments without celery installed
    def shared_task(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from voting_system.apps.audit.services import log_event
from voting_system.apps.ballots.models import Ballot
from voting_system.apps.common.utils import generate_plaintext_token, hash_token
from voting_system.apps.tokens.models import Token, TokenBatch, TokenStatus

CACHE_TTL_SECONDS = 60 * 60 * 24


def _plaintext_cache_key(batch_id):
    return f"token-batch-plaintext:{batch_id}"


def _default_encryption_key() -> str:
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8")


def _get_fernet() -> Fernet:
    configured_key = (getattr(settings, "TOKEN_ARCHIVE_ENCRYPTION_KEY", "") or "").strip()
    key = configured_key or _default_encryption_key()
    try:
        return Fernet(key.encode("utf-8"))
    except Exception:
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        derived_key = base64.urlsafe_b64encode(digest)
        return Fernet(derived_key)


def _encrypt_export_payload(payload: dict) -> str:
    return _get_fernet().encrypt(json.dumps(payload).encode("utf-8")).decode("utf-8")


def _decrypt_export_payload(blob: str) -> dict | None:
    if not blob:
        return None
    try:
        decrypted = _get_fernet().decrypt(blob.encode("utf-8"))
        payload = json.loads(decrypted.decode("utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("tokens"), list):
            return payload
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError):
        return None
    return None


@transaction.atomic
def generate_token_batch(*, election, created_by, label: str, quantity: int, expires_at=None):
    batch = TokenBatch.objects.create(
        election=election,
        created_by=created_by,
        label=label,
        quantity=quantity,
        expires_at=expires_at,
    )
    plaintext_tokens: list[str] = []
    token_rows: list[Token] = []

    seen_hashes: set[str] = set()
    while len(plaintext_tokens) < quantity:
        plaintext = generate_plaintext_token()
        token_hash = hash_token(plaintext)
        if token_hash in seen_hashes:
            continue
        if Token.objects.filter(token_hash=token_hash).exists():
            continue

        token_rows.append(
            Token(
                batch=batch,
                election=election,
                token_hash=token_hash,
                token_hint=plaintext[-6:],
            )
        )
        plaintext_tokens.append(plaintext)
        seen_hashes.add(token_hash)

    Token.objects.bulk_create(token_rows)

    archived_payload = {"label": label, "election_slug": election.slug, "tokens": plaintext_tokens}
    batch.encrypted_tokens_blob = _encrypt_export_payload(archived_payload)
    batch.save(update_fields=["encrypted_tokens_blob", "updated_at"])

    cache.set(
        _plaintext_cache_key(batch.id),
        archived_payload,
        timeout=CACHE_TTL_SECONDS,
    )

    log_event(
        actor=created_by,
        organization=election.organization,
        action="TOKENS_GENERATED",
        target_type="token_batch",
        target_id=str(batch.id),
        metadata={"label": label, "quantity": quantity, "election": election.slug},
    )

    return batch, plaintext_tokens


@transaction.atomic
def revoke_batch(*, batch: TokenBatch, actor):
    now = timezone.now()
    if batch.revoked:
        return batch
    batch.revoked = True
    batch.save(update_fields=["revoked", "updated_at"])

    Token.objects.filter(batch=batch, status=TokenStatus.ACTIVE).update(
        status=TokenStatus.REVOKED,
        revoked_at=now,
    )

    log_event(
        actor=actor,
        organization=batch.election.organization,
        action="TOKEN_BATCH_REVOKED",
        target_type="token_batch",
        target_id=str(batch.id),
        metadata={"label": batch.label},
    )
    return batch


def get_plaintext_tokens_for_export(batch: TokenBatch):
    cached = cache.get(_plaintext_cache_key(batch.id))
    if cached:
        return cached

    restored = _decrypt_export_payload(batch.encrypted_tokens_blob)
    if restored:
        cache.set(_plaintext_cache_key(batch.id), restored, timeout=CACHE_TTL_SECONDS)
    return restored


@transaction.atomic
def reset_token_vote(*, token: Token, actor):
    locked_token = (
        Token.objects.select_related("batch", "election__organization")
        .select_for_update()
        .get(id=token.id)
    )

    if locked_token.status != TokenStatus.USED:
        raise ValueError("Only used tokens can be reset")

    if locked_token.batch.revoked:
        raise ValueError("Cannot reset a token from a revoked batch")

    ballot = Ballot.objects.filter(token=locked_token).first()
    if ballot:
        ballot.delete()

    locked_token.status = TokenStatus.ACTIVE
    locked_token.used_at = None
    locked_token.revoked_at = None
    locked_token.save(update_fields=["status", "used_at", "revoked_at", "updated_at"])

    log_event(
        actor=actor,
        organization=locked_token.election.organization,
        action="TOKEN_VOTE_RESET",
        target_type="token",
        target_id=str(locked_token.id),
        metadata={"token_hint": locked_token.token_hint, "election": locked_token.election.slug},
    )
    return locked_token


@transaction.atomic
def delete_token_with_ballot(*, token: Token, actor):
    locked_token = (
        Token.objects.select_related("election__organization")
        .select_for_update()
        .get(id=token.id)
    )
    ballot = Ballot.objects.filter(token=locked_token).first()
    if ballot:
        ballot.delete()

    token_id = str(locked_token.id)
    token_hint = locked_token.token_hint
    election_slug = locked_token.election.slug
    organization = locked_token.election.organization
    locked_token.delete()

    log_event(
        actor=actor,
        organization=organization,
        action="TOKEN_DELETED",
        target_type="token",
        target_id=token_id,
        metadata={"token_hint": token_hint, "election": election_slug},
    )
    return {"id": token_id}


@transaction.atomic
def delete_batch_with_tokens(*, batch: TokenBatch, actor):
    locked_batch = (
        TokenBatch.objects.select_related("election__organization")
        .select_for_update()
        .get(id=batch.id)
    )
    organization = locked_batch.election.organization

    token_qs = Token.objects.filter(batch=locked_batch)
    token_count = token_qs.count()
    ballot_count = Ballot.objects.filter(token__batch=locked_batch).count()

    Ballot.objects.filter(token__batch=locked_batch).delete()
    token_qs.delete()
    batch_id = str(locked_batch.id)
    label = locked_batch.label
    election_slug = locked_batch.election.slug
    locked_batch.delete()
    cache.delete(_plaintext_cache_key(batch_id))

    log_event(
        actor=actor,
        organization=organization,
        action="TOKEN_BATCH_DELETED",
        target_type="token_batch",
        target_id=batch_id,
        metadata={
            "label": label,
            "election": election_slug,
            "tokens_deleted": token_count,
            "ballots_deleted": ballot_count,
        },
    )
    return {"id": batch_id}


def run_expired_batch_cleanup(*, now=None):
    effective_now = now or timezone.now()
    expired_batches = list(
        TokenBatch.objects.filter(
            expires_at__isnull=False,
            expires_at__lte=effective_now,
        )
    )
    for batch in expired_batches:
        delete_batch_with_tokens(batch=batch, actor=None)
    return len(expired_batches)


@shared_task(name="voting_system.apps.tokens.services.run_expired_batch_cleanup_task")
def run_expired_batch_cleanup_task():
    run_expired_batch_cleanup()
