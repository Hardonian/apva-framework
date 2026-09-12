"""Async database session management for the APVA backend."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import settings


def build_engine(database_url: str = settings.database_url):
    """Create the SQLAlchemy async engine.

    Args:
        database_url: SQLAlchemy async database URL.

    Returns:
        AsyncEngine: Configured SQLAlchemy async engine.
    """
    engine_options = {"pool_pre_ping": True}
    if not database_url.startswith("sqlite"):
        engine_options.update(
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout_seconds,
            pool_recycle=settings.db_pool_recycle_seconds,
        )
    return create_async_engine(database_url, **engine_options)


engine = build_engine()
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
async_session_maker = AsyncSessionLocal


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for FastAPI dependencies.

    Yields:
        AsyncSession: An active async session.
    """
    async with AsyncSessionLocal() as session:
        yield session


get_db = get_session
