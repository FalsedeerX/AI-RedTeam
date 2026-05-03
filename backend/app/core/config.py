from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DB_PORT: int
    DB_HOST: str
    DB_NAME: str
    DB_SCHEMA: str
    DB_OWNER_USER: str
    DB_OWNER_PASSWORD: str
    DB_RUNTIME_USER: str
    DB_RUNTIME_PASSWORD: str
    DB_MIGRATE_USER: str
    DB_MIGRATE_PASSWORD: str
    PURDUE_ALLOWED_EMAILS: str = ""
    APPROVED_TARGET_URL: str = ""

    # Clerk JWT verification. Empty strings disable Clerk (dev-only fallback path).
    CLERK_ISSUER: str = ""
    CLERK_JWKS_URL: str = ""
    CLERK_AUDIENCE: str = ""

    # When "1" *and* CLERK_ISSUER is empty, accept the legacy X-User-Id header.
    # Default off. CI and production must keep this unset.
    AUTH_DEV_BYPASS: str = "0"

    @field_validator("CLERK_ISSUER", "CLERK_JWKS_URL", mode="before")
    @classmethod
    def _normalize_url(cls, v: str) -> str:
        """Strip whitespace and a trailing slash so PyJWT issuer comparison
        cannot fail due to an invisible env-var typo."""
        if isinstance(v, str):
            return v.strip().rstrip("/")
        return v

    @property
    def DB_OWNER_URL(self) -> str:
        return (
                f"postgresql+psycopg://{self.DB_OWNER_USER}:{self.DB_OWNER_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def DB_RUNTIME_URL(self) -> str:
        return (
                f"postgresql+psycopg://{self.DB_RUNTIME_USER}:{self.DB_RUNTIME_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def DB_MIGRATE_URL(self) -> str:
        return (
                f"postgresql+psycopg://{self.DB_MIGRATE_USER}:{self.DB_MIGRATE_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def purdue_allowed_emails(self) -> list[str]:
        return [email.strip() for email in self.PURDUE_ALLOWED_EMAILS.split(",") if email.strip()]

    @property
    def clerk_enabled(self) -> bool:
        return bool(self.CLERK_ISSUER) and bool(self.CLERK_JWKS_URL)

    @property
    def auth_dev_bypass_enabled(self) -> bool:
        return self.AUTH_DEV_BYPASS == "1" and not self.clerk_enabled


settings = Settings()


if __name__ == "__main__":
    pass
