"""
Unit tests for Clerk JWT verification and the FastAPI dependency.

These tests sign tokens locally with an RSA key and monkey-patch the JWKS
client so we never hit the network.  The backend's ``verify_clerk_jwt``
path is exercised end-to-end: config gating, signing-key resolution,
issuer/audience claim checks, and expiry handling.
"""

from __future__ import annotations

import time
from unittest.mock import patch
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core import auth as auth_module
from app.core.auth import ClerkAuthError, extract_bearer_token, verify_clerk_jwt


ISSUER = "https://test.clerk.accounts.dev"
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def rsa_keypair():
    """Generate a throwaway RSA keypair for signing test tokens."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key = private_key.public_key()
    return private_pem, public_key


def _make_token(private_pem: bytes, **overrides) -> str:
    now = int(time.time())
    claims = {
        "sub": f"user_{uuid4().hex[:12]}",
        "iss": ISSUER,
        "iat": now,
        "exp": now + 300,
        "email": "analyst@example.com",
    }
    claims.update(overrides)
    return jwt.encode(claims, private_pem, algorithm="RS256")


@pytest.fixture(autouse=True)
def _configure_clerk(monkeypatch):
    """Point settings at the test issuer and reset the JWKS cache."""
    monkeypatch.setattr(auth_module.settings, "CLERK_ISSUER", ISSUER, raising=False)
    monkeypatch.setattr(auth_module.settings, "CLERK_JWKS_URL", JWKS_URL, raising=False)
    monkeypatch.setattr(auth_module.settings, "CLERK_AUDIENCE", "", raising=False)
    auth_module._jwks_client = None
    auth_module._jwks_client_url = None
    auth_module._jwks_client_loaded_at = 0.0
    yield


@pytest.fixture
def patched_jwks(rsa_keypair):
    """Replace the JWKS client with a stub that returns our local public key."""
    _, public_key = rsa_keypair

    class _StubSigningKey:
        def __init__(self, key):
            self.key = key

    class _StubClient:
        def get_signing_key_from_jwt(self, _token):
            return _StubSigningKey(public_key)

    with patch.object(auth_module, "PyJWKClient", return_value=_StubClient()):
        yield


# ---------------------------------------------------------------------------
# extract_bearer_token
# ---------------------------------------------------------------------------


def test_extract_bearer_token_accepts_standard_header():
    assert extract_bearer_token("Bearer abc.def.ghi") == "abc.def.ghi"


def test_extract_bearer_token_case_insensitive():
    assert extract_bearer_token("bearer abc") == "abc"


def test_extract_bearer_token_rejects_missing_scheme():
    assert extract_bearer_token("abc.def.ghi") is None


def test_extract_bearer_token_rejects_empty():
    assert extract_bearer_token(None) is None
    assert extract_bearer_token("") is None
    assert extract_bearer_token("Bearer ") is None


# ---------------------------------------------------------------------------
# verify_clerk_jwt — happy paths and common failures
# ---------------------------------------------------------------------------


def test_verify_clerk_jwt_accepts_valid_token(rsa_keypair, patched_jwks):
    private_pem, _ = rsa_keypair
    token = _make_token(private_pem)

    claims = verify_clerk_jwt(token)
    assert claims["iss"] == ISSUER
    assert claims["email"] == "analyst@example.com"
    assert claims["sub"].startswith("user_")


def test_verify_clerk_jwt_rejects_expired_token(rsa_keypair, patched_jwks):
    private_pem, _ = rsa_keypair
    now = int(time.time())
    token = _make_token(private_pem, iat=now - 600, exp=now - 60)

    with pytest.raises(ClerkAuthError):
        verify_clerk_jwt(token)


def test_verify_clerk_jwt_rejects_wrong_issuer(rsa_keypair, patched_jwks):
    private_pem, _ = rsa_keypair
    token = _make_token(private_pem, iss="https://attacker.example.com")

    with pytest.raises(ClerkAuthError):
        verify_clerk_jwt(token)


def test_verify_clerk_jwt_rejects_when_audience_required_but_missing(
    rsa_keypair, patched_jwks, monkeypatch
):
    monkeypatch.setattr(auth_module.settings, "CLERK_AUDIENCE", "my-api", raising=False)
    private_pem, _ = rsa_keypair
    token = _make_token(private_pem)  # no aud claim

    with pytest.raises(ClerkAuthError):
        verify_clerk_jwt(token)


def test_verify_clerk_jwt_accepts_matching_audience(rsa_keypair, patched_jwks, monkeypatch):
    monkeypatch.setattr(auth_module.settings, "CLERK_AUDIENCE", "my-api", raising=False)
    private_pem, _ = rsa_keypair
    token = _make_token(private_pem, aud="my-api")

    claims = verify_clerk_jwt(token)
    assert claims["aud"] == "my-api"


def test_verify_clerk_jwt_raises_when_clerk_disabled(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "CLERK_ISSUER", "", raising=False)
    monkeypatch.setattr(auth_module.settings, "CLERK_JWKS_URL", "", raising=False)

    with pytest.raises(ClerkAuthError):
        verify_clerk_jwt("any.token.value")


def test_verify_clerk_jwt_rejects_empty_token():
    with pytest.raises(ClerkAuthError):
        verify_clerk_jwt("")


def test_verify_clerk_jwt_rejects_garbage_token(patched_jwks):
    with pytest.raises(ClerkAuthError):
        verify_clerk_jwt("not-a-real-jwt")
