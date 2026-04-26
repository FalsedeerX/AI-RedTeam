from __future__ import annotations

from urllib.parse import urlparse

from fastapi import HTTPException

from app.core.config import settings

PURDUE_ONLY_MESSAGE = "Error: Only @purdue.edu email addresses can be used for this deployment."
PURDUE_ALLOWLIST_MESSAGE = (
    "Error: The email you entered is not part of the senior design class for ECE 49595."
)
APPROVED_TARGET_MESSAGE = (
    "Error: Only http://falsedeer.com/ is approved for testing in this deployment."
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def approved_emails() -> set[str]:
    return {normalize_email(email) for email in settings.purdue_allowed_emails if email.strip()}


def enforce_purdue_email(email: str) -> str:
    normalized = normalize_email(email)
    if not normalized.endswith("@purdue.edu"):
        raise HTTPException(status_code=400, detail=PURDUE_ONLY_MESSAGE)
    if normalized not in approved_emails():
        raise HTTPException(status_code=403, detail=PURDUE_ALLOWLIST_MESSAGE)
    return normalized


def normalize_target_url(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise HTTPException(status_code=400, detail=APPROVED_TARGET_MESSAGE)

    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        parsed = urlparse(f"http://{raw}")

    scheme = parsed.scheme.lower()
    host = parsed.netloc.lower()
    path = parsed.path or "/"

    normalized = f"{scheme}://{host}{path}"
    if parsed.query:
        normalized = f"{normalized}?{parsed.query}"
    if parsed.fragment:
        normalized = f"{normalized}#{parsed.fragment}"
    return normalized


def enforce_approved_target(value: str) -> str:
    normalized = normalize_target_url(value)
    if normalized != settings.APPROVED_TARGET_URL:
        raise HTTPException(status_code=400, detail=APPROVED_TARGET_MESSAGE)
    return normalized
