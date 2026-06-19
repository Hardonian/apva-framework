"""System health API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.config import settings
from apps.backend.database import get_session
from apps.backend.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health(
    session: AsyncSession = Depends(get_session),
) -> HealthResponse:
    """Return backend, database, Redis, and broker health status.

    Args:
        session: Async database session.

    Returns:
        HealthResponse: System health summary.
    """
    database_status = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        database_status = "error"

    redis_status = "ok"
    try:
        redis = Redis.from_url(settings.redis_url)
        await redis.ping()
        await redis.aclose()
    except Exception:
        redis_status = "error"

    celery_broker_status = "ok"
    try:
        broker = Redis.from_url(settings.celery_broker_url)
        await broker.ping()
        await broker.aclose()
    except Exception:
        celery_broker_status = "error"

    status = "ok" if all(
        value == "ok"
        for value in (database_status, redis_status, celery_broker_status)
    ) else "degraded"
    return HealthResponse(
        status=status,
        service=settings.app_name,
        database=database_status,
        redis=redis_status,
        celery_broker=celery_broker_status,
    )
