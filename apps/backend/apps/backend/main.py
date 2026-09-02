"""FastAPI application factory for APVA backend."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncGenerator

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apva.constants import FRAMEWORK_VERSION
from .config import settings
from .database import engine
from .limiter import RateLimitError, rate_limit
from .models import Base
from .routers.auth import router as auth_router
from .routers.billing import router as billing_router
from .routers.eval import router as eval_router
from .routers.export import router as export_router
from .routers.health import router as health_router
from .routers.metrics import router as metrics_router
from .routers.safeguards import router as safeguards_router
from .routers.telemetry import router as telemetry_router
from .routers.tenants import router as tenants_router
from .routers.webhooks import router as webhooks_router

logger = logging.getLogger(__name__)


async def create_tables() -> None:
    """Create database tables for local/dev deployments."""
    from sqlalchemy import select

    if settings.environment.lower() == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        import secrets

        from .database import async_session_maker
        from .models import Tenant

        async with async_session_maker() as session:
            tenant = await session.scalar(select(Tenant).where(Tenant.id == 1))
            if not tenant:
                tenant = Tenant(id=1, name="Acme Corp", api_key_hash=secrets.token_urlsafe(32))
                session.add(tenant)
                await session.commit()


async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage backend startup and shutdown lifecycle."""
    await create_tables()

    app.state.http_client = httpx.AsyncClient(timeout=10.0)

    yield

    if hasattr(app.state, "http_client") and app.state.http_client is not None:
        await app.state.http_client.aclose()

    await engine.dispose()


app = FastAPI(
    title="APVA Enterprise Backend",
    description="Cloud-native APVA telemetry ingestion, async RAG evaluation, and TVY metrics.",
    version=FRAMEWORK_VERSION,
    lifespan=lifespan,
)


@app.exception_handler(RateLimitError)
async def _rate_limit_handler(request: Request, exc: RateLimitError) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
    )


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add enterprise security headers, request ID, timing, and version to responses."""
    req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    start_time = time.perf_counter()

    response = await call_next(request)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
    response.headers["X-APVA-Version"] = FRAMEWORK_VERSION
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telemetry_router, prefix="/api/v1", dependencies=[Depends(rate_limit)])
app.include_router(eval_router, prefix="/api/v1", dependencies=[Depends(rate_limit)])
app.include_router(metrics_router, prefix="/api/v1", dependencies=[Depends(rate_limit)])
app.include_router(billing_router, prefix="/api/v1", dependencies=[Depends(rate_limit)])
app.include_router(health_router, prefix="/api/v1", dependencies=[Depends(rate_limit)])
app.include_router(auth_router, prefix="/api/v1", dependencies=[Depends(rate_limit)])
app.include_router(safeguards_router, prefix="/api/v1", dependencies=[Depends(rate_limit)])
app.include_router(tenants_router, prefix="/api/v1", dependencies=[Depends(rate_limit)])
app.include_router(export_router, prefix="/api/v1", dependencies=[Depends(rate_limit)])
app.include_router(webhooks_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return structured JSON for unexpected application errors."""
    logger.error("Unhandled exception processing request %s %s", request.method, request.url, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )
