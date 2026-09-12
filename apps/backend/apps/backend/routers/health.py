from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_session
from ..schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


async def _redis_status(url: str) -> str:
    """Ping a Redis-compatible dependency with strict time bounds."""
    client = Redis.from_url(url, socket_connect_timeout=0.2, socket_timeout=0.2)
    try:
        await client.ping()
        return "ok"
    except Exception:
        return "error"
    finally:
        await client.aclose()


async def _database_status(session: AsyncSession) -> str:
    try:
        await session.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


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
    database_check = _database_status(session)
    redis_check = _redis_status(settings.redis_url)
    if settings.celery_broker_url == settings.redis_url:
        database_status, redis_status = await asyncio.gather(database_check, redis_check)
        celery_broker_status = redis_status
    else:
        database_status, redis_status, celery_broker_status = await asyncio.gather(
            database_check,
            redis_check,
            _redis_status(settings.celery_broker_url),
        )

    status = (
        "ok"
        if all(value == "ok" for value in (database_status, redis_status, celery_broker_status))
        else "degraded"
    )
    return HealthResponse(
        status=status,
        service=settings.app_name,
        database=database_status,
        redis=redis_status,
        celery_broker=celery_broker_status,
    )
