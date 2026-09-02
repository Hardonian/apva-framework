"""Configuration for the APVA backend service."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the APVA backend.

    Attributes:
        app_name: Human-readable application name.
        environment: Deployment environment (development, staging, production).
        log_level: Logging severity level (DEBUG, INFO, WARNING, ERROR).
        database_url: SQLAlchemy async database URL.
        redis_url: Redis URL used for health checks and optional cache clients.
        celery_broker_url: Celery broker URL.
        celery_result_backend: Celery result backend URL.
        target_app_url: Mock target application base URL used by async workers.
        default_rag_reliability: Default RAG reliability used for macro TVY when
            no completed evaluation jobs are available.
        api_key: Optional local API key used by SDK examples.
        cors_origins: Permitted CORS origins for the API.
        stripe_enabled: Feature flag for Stripe billing integration.
        stripe_api_key: Optional Stripe secret key.
        sso_allowed_domains: Permitted email domains for mock/real SSO.
        max_request_size_bytes: Maximum allowed request payload in bytes.
    """

    model_config = SettingsConfigDict(
        env_prefix="APVA_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = Field(default="apva-backend", min_length=1)
    environment: str = Field(default="development", min_length=1)
    log_level: str = Field(default="INFO")
    database_url: str = Field(
        default="postgresql+asyncpg://apva:apva@localhost:5432/apva",
        min_length=1,
    )
    redis_url: str = Field(default="redis://localhost:6379/0", min_length=1)
    api_key: str | None = Field(default="dev-local-key", min_length=1)
    default_rag_reliability: float = Field(default=1.0, ge=0.0, le=1.0)
    target_app_url: str = Field(default="http://localhost:8080", min_length=1)
    celery_result_backend: str = Field(default="redis://localhost:6379/1", min_length=1)
    celery_broker_url: str = Field(default="redis://localhost:6379/0", min_length=1)
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000", "https://dashboard.apva.ai"]
    )
    stripe_enabled: bool = Field(default=False)
    stripe_api_key: str | None = Field(default=None)
    sso_allowed_domains: list[str] = Field(default=["acmecorp.com"])
    max_request_size_bytes: int = Field(default=10_485_760)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton application settings.

    Returns:
        Settings: Validated runtime settings.
    """
    return Settings()


settings = get_settings()
