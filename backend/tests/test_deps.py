"""
Tests for the ``get_current_user_id`` FastAPI dependency.

Exercises the three configuration branches (Clerk on, dev-bypass on, both off)
and the lazy-upsert call into ``UsersBroker`` on successful JWT verification.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api import deps as deps_module
from app.api.deps import get_current_user_id


def _make_request(headers: dict[str, str] | None = None):
    """Minimal stand-in for a Starlette Request with only .headers used."""
    return SimpleNamespace(headers=headers or {})


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch):
    monkeypatch.setattr(deps_module.settings, "CLERK_ISSUER", "", raising=False)
    monkeypatch.setattr(deps_module.settings, "CLERK_JWKS_URL", "", raising=False)
    monkeypatch.setattr(deps_module.settings, "AUTH_DEV_BYPASS", "0", raising=False)
    yield


# ---------------------------------------------------------------------------
# Clerk path
# ---------------------------------------------------------------------------


def test_clerk_path_upserts_and_returns_local_uuid(monkeypatch):
    monkeypatch.setattr(deps_module.settings, "CLERK_ISSUER", "https://clerk.test", raising=False)
    monkeypatch.setattr(deps_module.settings, "CLERK_JWKS_URL", "https://clerk.test/jwks", raising=False)

    claims = {"sub": "user_abc", "email": "ada@example.com"}
    monkeypatch.setattr(deps_module, "verify_clerk_jwt", lambda token: claims)

    local_id = uuid4()
    fake_user = SimpleNamespace(id=local_id)
    mock_broker = MagicMock()
    mock_broker.upsert_from_clerk.return_value = fake_user
    monkeypatch.setattr(deps_module, "_users_broker", mock_broker)

    request = _make_request({"Authorization": "Bearer eyJ.test.jwt"})
    result = get_current_user_id(request)

    assert result == local_id
    mock_broker.upsert_from_clerk.assert_called_once_with(
        clerk_user_id="user_abc", email="ada@example.com"
    )


def test_clerk_path_falls_back_placeholder_email_when_claim_missing(monkeypatch):
    monkeypatch.setattr(deps_module.settings, "CLERK_ISSUER", "https://clerk.test", raising=False)
    monkeypatch.setattr(deps_module.settings, "CLERK_JWKS_URL", "https://clerk.test/jwks", raising=False)
    monkeypatch.setattr(deps_module, "verify_clerk_jwt", lambda token: {"sub": "user_no_email"})

    fake_user = SimpleNamespace(id=uuid4())
    mock_broker = MagicMock()
    mock_broker.upsert_from_clerk.return_value = fake_user
    monkeypatch.setattr(deps_module, "_users_broker", mock_broker)

    request = _make_request({"Authorization": "Bearer eyJ.test.jwt"})
    get_current_user_id(request)

    args, kwargs = mock_broker.upsert_from_clerk.call_args
    assert kwargs["email"].endswith("@clerk.local")
    assert kwargs["clerk_user_id"] == "user_no_email"


def test_clerk_path_returns_401_when_header_missing(monkeypatch):
    monkeypatch.setattr(deps_module.settings, "CLERK_ISSUER", "https://clerk.test", raising=False)
    monkeypatch.setattr(deps_module.settings, "CLERK_JWKS_URL", "https://clerk.test/jwks", raising=False)

    with pytest.raises(HTTPException) as exc:
        get_current_user_id(_make_request({}))
    assert exc.value.status_code == 401


def test_clerk_path_returns_401_on_verification_failure(monkeypatch):
    monkeypatch.setattr(deps_module.settings, "CLERK_ISSUER", "https://clerk.test", raising=False)
    monkeypatch.setattr(deps_module.settings, "CLERK_JWKS_URL", "https://clerk.test/jwks", raising=False)

    def _raise(_token):
        raise deps_module.ClerkAuthError("bad sig")
    monkeypatch.setattr(deps_module, "verify_clerk_jwt", _raise)

    with pytest.raises(HTTPException) as exc:
        get_current_user_id(_make_request({"Authorization": "Bearer x.y.z"}))
    assert exc.value.status_code == 401


def test_clerk_path_rejects_token_without_subject(monkeypatch):
    monkeypatch.setattr(deps_module.settings, "CLERK_ISSUER", "https://clerk.test", raising=False)
    monkeypatch.setattr(deps_module.settings, "CLERK_JWKS_URL", "https://clerk.test/jwks", raising=False)
    monkeypatch.setattr(deps_module, "verify_clerk_jwt", lambda token: {"email": "x@y.z"})

    with pytest.raises(HTTPException) as exc:
        get_current_user_id(_make_request({"Authorization": "Bearer x.y.z"}))
    assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# Dev bypass path
# ---------------------------------------------------------------------------


def test_dev_bypass_accepts_valid_uuid(monkeypatch):
    monkeypatch.setattr(deps_module.settings, "AUTH_DEV_BYPASS", "1", raising=False)
    fake_id = uuid4()

    result = get_current_user_id(_make_request({"X-User-Id": str(fake_id)}))
    assert result == fake_id


def test_dev_bypass_rejects_missing_header(monkeypatch):
    monkeypatch.setattr(deps_module.settings, "AUTH_DEV_BYPASS", "1", raising=False)

    with pytest.raises(HTTPException) as exc:
        get_current_user_id(_make_request({}))
    assert exc.value.status_code == 401


def test_dev_bypass_rejects_malformed_uuid(monkeypatch):
    monkeypatch.setattr(deps_module.settings, "AUTH_DEV_BYPASS", "1", raising=False)

    with pytest.raises(HTTPException) as exc:
        get_current_user_id(_make_request({"X-User-Id": "not-a-uuid"}))
    assert exc.value.status_code == 401


def test_dev_bypass_ignored_when_clerk_enabled(monkeypatch):
    """AUTH_DEV_BYPASS must not grant access once Clerk is configured."""
    monkeypatch.setattr(deps_module.settings, "CLERK_ISSUER", "https://clerk.test", raising=False)
    monkeypatch.setattr(deps_module.settings, "CLERK_JWKS_URL", "https://clerk.test/jwks", raising=False)
    monkeypatch.setattr(deps_module.settings, "AUTH_DEV_BYPASS", "1", raising=False)

    # No Authorization header, but an X-User-Id present.
    with pytest.raises(HTTPException) as exc:
        get_current_user_id(_make_request({"X-User-Id": str(uuid4())}))
    assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# Both off
# ---------------------------------------------------------------------------


def test_auth_disabled_returns_503():
    with pytest.raises(HTTPException) as exc:
        get_current_user_id(_make_request({"X-User-Id": str(uuid4())}))
    assert exc.value.status_code == 503
