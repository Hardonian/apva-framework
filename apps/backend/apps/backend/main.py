"""FastAPI application factory for APVA backend."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from .database import engine
from .limiter import RateLimitError, rate_limit
from .models import Base
from .routers.auth import router as auth_router
from .routers.eval import router as eval_router
from .routers.health import router as health_router
from .routers.metrics import router as metrics_router
from .routers.telemetry import router as telemetry_router

logger = logging.getLogger(__name__)

# Global httpx client for reuse
http_client: httpx.AsyncClient | None = None


async def create_tables() -> None:
    """Create database tables for local/dev deployments.

    This is intentionally only used at application startup in this MVP. In
    production, Alembic migrations should own schema changes.
    """
    from sqlalchemy import select

    from .config import settings
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
        
    await engine.dispose()


app = FastAPI(
    title="APVA Enterprise Backend",
    description="Cloud-native APVA telemetry ingestion, async RAG evaluation, and TVY metrics.",
    version="2.0.0",
    lifespan=lifespan,
)

# Rate limiting: real enforcement is done by the ``rate_limit`` dependency
# (mounted on every router in the include_router calls below). The SlowAPI
# limiter/middleware are kept only so ``app.state.limiter`` exists and the
# legacy middleware does not crash on startup; they do not perform enforcement.
app.state.limiter = Limiter(key_func=get_remote_address)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitError)
async def _rate_limit_handler(request: Request, exc: RateLimitError):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
    )

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

app.include_router(telemetry_router, prefix="/api/v1", dependencies=[Depends(rate_limit)])
app.include_router(eval_router, prefix="/api/v1", dependencies=[Depends(rate_limit)])
app.include_router(metrics_router, prefix="/api/v1", dependencies=[Depends(rate_limit)])
app.include_router(health_router, prefix="/api/v1", dependencies=[Depends(rate_limit)])
app.include_router(auth_router, prefix="/api/v1", dependencies=[Depends(rate_limit)])


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


