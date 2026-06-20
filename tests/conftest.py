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
    ROOT / "apps" / "backend",
    ROOT / "packages" / "cli" / "src",
    ROOT / "packages" / "sdk" / "src",
]

for source_root in reversed(SOURCE_ROOTS):
    source = str(source_root)
    if source not in sys.path:
        sys.path.insert(0, source)

# Keep backend tests local-first and independent of a running Postgres service.
os.environ.setdefault("APVA_DATABASE_URL", "sqlite+aiosqlite:///./.apva-test.db")
os.environ.setdefault("APVA_REDIS_URL", "redis://localhost:6380/0")
os.environ.setdefault("APVA_CELERY_BROKER_URL", "redis://localhost:6380/0")
os.environ.setdefault("APVA_CELERY_RESULT_BACKEND", "redis://localhost:6380/1")


def pytest_sessionstart(session):  # type: ignore[no-untyped-def]
    """Create local SQLite tables for ASGITransport tests.

    httpx.ASGITransport does not automatically run FastAPI lifespan events in
    every supported version, so tests bootstrap the schema explicitly.
    """
    import asyncio
    import importlib

    database = importlib.import_module("apps.backend.database")
    models = importlib.import_module("apps.backend.models")

    async def create_schema() -> None:
        async with database.engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

    asyncio.run(create_schema())
