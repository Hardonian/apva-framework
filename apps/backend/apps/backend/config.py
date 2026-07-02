"""Configuration for the APVA backend service."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the APVA backend.

    Attributes:
        app_name: Human-readable application name.
        database_url: SQLAlchemy async database URL.
        redis_url: Redis URL used for health checks and optional cache clients.
        celery_broker_url: Celery broker URL.
        celery_result_backend: Celery result backend URL.
        target_app_url: Mock target application base URL used by async workers.
        default_rag_reliability: Default RAG reliability used for macro TVY when
            no completed evaluation jobs are available.
        api_key: Optional local API key used by SDK examples. Defaults to a
            development-only value.
    """

    model_config = SettingsConfigDict(
        env_prefix="", env_file=".env", extra="ignore"
    )

    app_name: str = Field(default="apva-backend", min_length=1)
    environment: str = Field(default="development", min_length=1)
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
def get_settings() -> Settings:
    """Return cached application settings.

    Returns:
        Settings: Validated runtime settings.
    """
    return Settings()


settings = get_settings()
