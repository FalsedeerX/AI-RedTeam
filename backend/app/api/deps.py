"""
deps.py — FastAPI dependency that resolves the current authenticated user.

Auth flow (production path)
---------------------------
  1. Read ``Authorization: Bearer <jwt>`` header.
  2. Verify the JWT against Clerk JWKS (see ``app.core.auth``).
  3. Upsert a row in ``app.users`` keyed by the Clerk ``sub`` claim, using the
     token's ``email`` claim (or a placeholder when absent).
  4. Return the local ``users.id`` UUID so every existing route signature
     (``user_id: UUID = Depends(get_current_user_id)``) keeps working.

Dev-only fallback
-----------------
When ``CLERK_ISSUER``/``CLERK_JWKS_URL`` are unset *and* ``AUTH_DEV_BYPASS=1``,
the legacy ``X-User-Id`` header is accepted verbatim.  This keeps local tooling
working before Clerk env vars are configured, and is gated so production deploys
cannot silently fall back to the insecure path.
"""

from uuid import UUID

from fastapi import HTTPException, Request

from app.core.auth import ClerkAuthError, extract_bearer_token, verify_clerk_jwt
from app.core.config import settings
from app.db.broker import ProjectsBroker, UsersBroker


_users_broker = UsersBroker()
_projects_broker = ProjectsBroker()


def require_project_owner(project_id: UUID, user_id: UUID) -> None:
    """Raise 404 if the project is missing or not owned by the caller.

    Kept as 404 (not 403) so unowned ids are indistinguishable from deleted
    ones, denying any existence oracle to an attacker.
    """
    project = _projects_broker.get(project_id)
    if project is None or project.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Project not found")


def require_run_owner(run_id: UUID | str, user_id: UUID) -> UUID:
    """Resolve a run to its project and assert ownership. Returns project_id."""
    if isinstance(run_id, str):
        try:
            run_id = UUID(run_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Run not found")
    # Import locally to avoid a circular import at module load.
    from app.db.broker import RunsBroker
    run = RunsBroker().get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    require_project_owner(run.project_id, user_id)
    return run.project_id


def _resolve_via_clerk(request: Request) -> UUID:
    token = extract_bearer_token(request.headers.get("Authorization"))
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": 'Bearer realm="clerk"'},
        )

    try:
        claims = verify_clerk_jwt(token)
    except ClerkAuthError as exc:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid session token: {exc}",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )

    sub = claims.get("sub")
    if not sub or not isinstance(sub, str):
        raise HTTPException(status_code=401, detail="Token missing subject claim")

    email = _extract_email_claim(claims) or f"{sub}@clerk.local"
    user = _users_broker.upsert_from_clerk(clerk_user_id=sub, email=email)
    return user.id


def _resolve_via_dev_bypass(request: Request) -> UUID:
    raw_data = request.headers.get("X-User-Id")
    if not raw_data:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return UUID(raw_data)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session identification")


def _extract_email_claim(claims: dict) -> str | None:
    """Clerk JWT templates commonly expose email under one of these keys."""
    for key in ("email", "email_address", "primary_email_address"):
        value = claims.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def get_current_user_id(request: Request) -> UUID:
    """
    Dependency for extracting the local user's UUID from the request.

    Production: verifies a Clerk JWT and lazily upserts the matching row in
    ``app.users``.  Dev bypass: accepts ``X-User-Id`` when Clerk is not
    configured and ``AUTH_DEV_BYPASS=1``.
    """
    if settings.clerk_enabled:
        return _resolve_via_clerk(request)

    if settings.auth_dev_bypass_enabled:
        return _resolve_via_dev_bypass(request)

    raise HTTPException(
        status_code=503,
        detail=(
            "Auth is not configured. Set CLERK_ISSUER and CLERK_JWKS_URL, "
            "or set AUTH_DEV_BYPASS=1 for local-only development."
        ),
    )


if __name__ == "__main__":
    pass
