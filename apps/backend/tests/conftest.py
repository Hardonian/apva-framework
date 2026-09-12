"""Hermetic SQLite configuration for backend tests."""

from __future__ import annotations

import asyncio
import importlib
import os
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOTS = [
    ROOT,
    ROOT / "packages" / "cli" / "src",
    ROOT / "packages" / "sdk" / "src",
    ROOT / "packages" / "apva-langchain",
    ROOT / "packages" / "apva-llamaindex",
]

for source_root in reversed(SOURCE_ROOTS):
    source = str(source_root)
    if source not in sys.path:
        sys.path.insert(0, source)

os.environ["APVA_DATABASE_URL"] = "sqlite+aiosqlite:///./.apva-test.db"
os.environ["APVA_REDIS_URL"] = "redis://localhost:6380/0"
os.environ["APVA_CELERY_BROKER_URL"] = "redis://localhost:6380/0"
os.environ["APVA_CELERY_RESULT_BACKEND"] = "redis://localhost:6380/1"


def pytest_sessionstart(session):
    """Create local SQLite tables and seed default tenant."""
    database = importlib.import_module("apps.backend.apps.backend.database")
    models = importlib.import_module("apps.backend.apps.backend.models")

    database.engine = database.build_engine(os.environ["APVA_DATABASE_URL"])
    database.AsyncSessionLocal = async_sessionmaker(database.engine, expire_on_commit=False)
    database.async_session_maker = database.AsyncSessionLocal

    async def _init_db():
        async with database.engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
        async with database.async_session_maker() as s:
            from sqlalchemy import select
            t = await s.scalar(select(models.Tenant).where(models.Tenant.id == 1))
            if not t:
                import secrets
                t = models.Tenant(id=1, name="Acme Corp", api_key_hash=secrets.token_urlsafe(32))
                s.add(t)
                await s.commit()

    asyncio.run(_init_db())
