"""FastAPI application factory for APVA backend."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from apps.backend.database import engine
from apps.backend.models import Base
from apps.backend.routers.eval import router as eval_router
from apps.backend.routers.health import router as health_router
from apps.backend.routers.metrics import router as metrics_router
from apps.backend.routers.telemetry import router as telemetry_router
from apps.backend.routers.auth import router as auth_router

logger = logging.getLogger(__name__)

# Global httpx client for reuse
http_client: httpx.AsyncClient | None = None

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


async def create_tables() -> None:
    """Create database tables for local/dev deployments.

    This is intentionally only used at application startup in this MVP. In
    production, Alembic migrations should own schema changes.
    """
    from apps.backend.config import settings
    if settings.environment.lower() == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        from sqlalchemy import select
        from apps.backend.database import async_session_maker
        from apps.backend.models import Tenant
        import secrets
        
        async with async_session_maker() as session:
            tenant = await session.scalar(select(Tenant).where(Tenant.id == 1))
            if not tenant:
                tenant = Tenant(id=1, name="Acme Corp", api_key_hash=secrets.token_urlsafe(32))
                session.add(tenant)
                await session.commit()


async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage backend startup and shutdown lifecycle.

    Args:
        app: FastAPI application instance.

    Yields:
        None: Yields control back to FastAPI after startup.
    """
    global http_client
    
    await create_tables()
    
    http_client = httpx.AsyncClient(timeout=10.0)
    
    yield
    
    if http_client is not None:
        await http_client.aclose()


app = FastAPI(
    title="APVA Enterprise Backend",
    description="Cloud-native APVA telemetry ingestion, async RAG evaluation, and TVY metrics.",
    version="2.0.0",
    lifespan=lifespan,
)

# Apply rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add Enterprise-grade security headers to all responses."""
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://dashboard.apva.ai"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telemetry_router, prefix="/api/v1")
app.include_router(eval_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return structured JSON for unexpected application errors.

    Args:
        request: Incoming request.
        exc: Unexpected exception.

    Returns:
        JSONResponse: Structured error response.
    """
    logger.error("Unhandled exception processing request %s %s", request.method, request.url, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Dispose the SQLAlchemy engine on shutdown."""
    await engine.dispose()
