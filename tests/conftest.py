"""Test path bootstrap for the APVA mono-repo.

The repo intentionally keeps the core package, enterprise backend, CLI, and SDK
as separate distributable units. Local tests should still run from a fresh clone
without requiring editable installs first, so we expose those source roots here.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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

# Keep backend tests local-first and independent of a running Postgres service.
# FORCE the hermetic values (not setdefault) so an inherited/external
# APVA_DATABASE_URL cannot leak in and make tests hit a real database.
os.environ["APVA_DATABASE_URL"] = "sqlite+aiosqlite:///./.apva-test.db"
os.environ["APVA_REDIS_URL"] = "redis://localhost:6380/0"
os.environ["APVA_CELERY_BROKER_URL"] = "redis://localhost:6380/0"
os.environ["APVA_CELERY_RESULT_BACKEND"] = "redis://localhost:6380/1"


def pytest_sessionstart(session):  # type: ignore[no-untyped-def]
    """Create local SQLite tables for ASGITransport tests.

    httpx.ASGITransport does not automatically run FastAPI lifespan events in
    every supported version, so tests bootstrap the schema explicitly.

    The backend builds its engine eagerly at import time from settings, so the
    hermetic SQLite URL must be forced BEFORE the database module is imported,
    and the engine rebuilt afterward to point at the in-memory test database.
    """
    import asyncio
    import importlib

    from sqlalchemy.ext.asyncio import async_sessionmaker

    database = importlib.import_module("apps.backend.apps.backend.database")
    models = importlib.import_module("apps.backend.apps.backend.models")

    # Rebuild the eager engine against the forced SQLite URL so tests never
    # touch a real Postgres instance.
    database.engine = database.build_engine(os.environ["APVA_DATABASE_URL"])
    database.AsyncSessionLocal = async_sessionmaker(
        database.engine, expire_on_commit=False
    )
    database.async_session_maker = database.AsyncSessionLocal

    async def create_schema() -> None:
        async with database.engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

    asyncio.run(create_schema())
