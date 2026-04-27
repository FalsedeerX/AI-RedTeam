"""
auth.py — Clerk JWT verification.

Verifies Clerk-issued JWTs against Clerk's JWKS endpoint and returns the
parsed claims dict on success.  Keys are fetched lazily and cached in memory
for `JWKS_CACHE_TTL_SECONDS`.  `CLERK_ISSUER` and `CLERK_JWKS_URL` must be
set for verification to be available.

Public surface
--------------
    verify_clerk_jwt(token: str) -> dict
        Raises ClerkAuthError on any failure; returns claims on success.

The FastAPI dependency in ``app.api.deps`` wraps this and handles the
HTTP translation (401 on error, lazy user upsert, dev bypass).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import jwt
from jwt import PyJWKClient, InvalidTokenError

from app.core.config import settings

logger = logging.getLogger(__name__)

JWKS_CACHE_TTL_SECONDS = 60 * 60  # 1 hour

# Tolerate up to 10 s of clock drift between this server and Clerk.
# Clerk session JWTs are short-lived (60 s default), so even a small
# skew causes "Token is expired" / "Token is not yet valid" in prod.
CLOCK_SKEW_LEEWAY_SECONDS = 10


class ClerkAuthError(Exception):
    """Raised when a JWT fails verification for any reason."""


_jwks_lock = threading.Lock()
_jwks_client: PyJWKClient | None = None
_jwks_client_url: str | None = None
_jwks_client_loaded_at: float = 0.0


def _get_jwks_client() -> PyJWKClient:
    """Return a PyJWKClient for the configured JWKS URL, cached for TTL."""
    global _jwks_client, _jwks_client_url, _jwks_client_loaded_at

    if not settings.CLERK_JWKS_URL:
        raise ClerkAuthError("CLERK_JWKS_URL is not configured")

    now = time.time()
    with _jwks_lock:
        expired = (now - _jwks_client_loaded_at) > JWKS_CACHE_TTL_SECONDS
        url_changed = _jwks_client_url != settings.CLERK_JWKS_URL
        if _jwks_client is None or expired or url_changed:
            _jwks_client = PyJWKClient(settings.CLERK_JWKS_URL)
            _jwks_client_url = settings.CLERK_JWKS_URL
            _jwks_client_loaded_at = now
        return _jwks_client


def verify_clerk_jwt(token: str) -> dict[str, Any]:
    """Verify a Clerk JWT and return its claims.

    Raises ``ClerkAuthError`` if:
      - Clerk env vars are not configured
      - the token is malformed, expired, or signed with an unknown key
      - the issuer / audience claims do not match configuration
    """
    if not settings.clerk_enabled:
        raise ClerkAuthError("Clerk is not configured")

    if not token:
        raise ClerkAuthError("Empty token")

    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token).key
    except Exception as exc:  # noqa: BLE001
        logger.warning("JWKS key lookup failed: %s", exc, exc_info=True)
        raise ClerkAuthError(f"Failed to resolve signing key: {exc}") from exc

    decode_kwargs: dict[str, Any] = {
        "algorithms": ["RS256"],
        "issuer": settings.CLERK_ISSUER,
        "leeway": CLOCK_SKEW_LEEWAY_SECONDS,
        "options": {"require": ["exp", "iat", "sub"]},
    }
    if settings.CLERK_AUDIENCE:
        decode_kwargs["audience"] = settings.CLERK_AUDIENCE

    try:
        claims = jwt.decode(token, signing_key, **decode_kwargs)
    except InvalidTokenError as exc:
        logger.warning(
            "JWT decode failed (issuer=%r, audience=%r): %s",
            settings.CLERK_ISSUER,
            settings.CLERK_AUDIENCE or "<not set>",
            exc,
        )
        raise ClerkAuthError(f"Invalid token: {exc}") from exc

    logger.debug("Clerk JWT verified for sub=%s", claims.get("sub"))
    return claims


def extract_bearer_token(authorization_header: str | None) -> str | None:
    """Pull the raw JWT out of an `Authorization: Bearer <jwt>` header."""
    if not authorization_header:
        return None
    parts = authorization_header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


if __name__ == "__main__":
    pass
