from __future__ import annotations

import hashlib
import hmac
import secrets
import string
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.core import signing

TOKEN_ALPHABET = string.ascii_uppercase + string.digits


def hash_token(plaintext_token: str) -> str:
    digest = hmac.new(
        key=settings.TOKEN_HASH_PEPPER.encode("utf-8"),
        msg=plaintext_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    )
    return digest.hexdigest()


def generate_plaintext_token(length: int = 16) -> str:
    return "".join(secrets.choice(TOKEN_ALPHABET) for _ in range(length))


def generate_receipt_code(length: int = 10) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def build_voter_session(payload: dict, max_age_seconds: int | None = None) -> str:
    signer = signing.TimestampSigner(salt="voter-session")
    max_age = max_age_seconds or settings.VOTER_SESSION_MAX_AGE_SECONDS
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=max_age)
    signed_payload = {**payload, "exp": expires_at.isoformat()}
    return signer.sign_object(signed_payload)


def parse_voter_session(token: str, max_age_seconds: int | None = None) -> dict:
    signer = signing.TimestampSigner(salt="voter-session")
    max_age = max_age_seconds or settings.VOTER_SESSION_MAX_AGE_SECONDS
    return signer.unsign_object(token, max_age=max_age)
