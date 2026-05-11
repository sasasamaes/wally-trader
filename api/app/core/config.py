"""Application settings loaded from environment via Pydantic."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "wally-api"
    ENV: Literal["dev", "staging", "production"] = "dev"
    DEBUG: bool = False
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    API_V1_PREFIX: str = "/api/v1"

    # --- CORS ---
    CORS_ALLOWED_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    # --- Database ---
    DATABASE_URL: PostgresDsn
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # --- Redis ---
    REDIS_URL: RedisDsn

    # --- Auth (Clerk) ---
    CLERK_SECRET_KEY: SecretStr | None = None
    CLERK_PUBLISHABLE_KEY: str | None = None
    CLERK_JWT_ISSUER: str | None = None
    CLERK_WEBHOOK_SECRET: SecretStr | None = None

    # --- Encryption ---
    # 32 bytes base64-encoded master Key Encryption Key.
    # Generate once: `python -c "import secrets,base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"`
    # NEVER commit. Rotate via the rotate_kek admin command.
    MASTER_KEK: SecretStr

    # --- Billing (Stripe) ---
    STRIPE_SECRET_KEY: SecretStr | None = None
    STRIPE_WEBHOOK_SECRET: SecretStr | None = None
    STRIPE_PRICE_ID_BASE: str | None = None
    STRIPE_METER_AGENT_CALLS_ID: str | None = None

    # --- Beta access ---
    BETA_ALLOWED_EMAILS: list[str] = Field(default_factory=list)

    # --- Observability ---
    SENTRY_DSN: str | None = None

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
