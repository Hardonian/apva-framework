"""FastAPI dependencies for APVA backend."""

from __future__ import annotations

import hashlib
import secrets
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db
from .models import Tenant

security = HTTPBearer(auto_error=True)


def hash_api_key(key: str) -> str:
    """Return the SHA-256 hex digest of an API key."""
    return hashlib.sha256(key.strip().encode("utf-8")).hexdigest()


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Resolve the authenticated Tenant model from the Bearer API key.

    Performs secure SHA-256 hash lookup in the tenants database table with
    timing-safe fallback to configured settings API key.

    Args:
        credentials: Bearer token from the Authorization header.
        db: Async database session.

    Returns:
        Tenant: The resolved Tenant SQLAlchemy model.

    Raises:
        HTTPException: 401 if authentication fails.
    """
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    provided_hash = hash_api_key(token)

    # 1. Database lookup by hashed API key
    stmt = select(Tenant).where(Tenant.api_key_hash == provided_hash)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    if tenant is not None:
        return tenant

    # 2. Check dev key fallback from settings
    if settings.api_key:
        matches_plain = secrets.compare_digest(token, settings.api_key)
        matches_hash = secrets.compare_digest(provided_hash, hash_api_key(settings.api_key))
        if matches_plain or matches_hash:
            # Return tenant id=1 if exists, or create a mock tenant representation
            stmt_default = select(Tenant).where(Tenant.id == 1)
            res_default = await db.execute(stmt_default)
            tenant_default = res_default.scalar_one_or_none()
            if tenant_default:
                return tenant_default

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_tenant_context(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    """Provide tenant context dictionary for compatibility with legacy routes."""
    return {
        "tenant_id": current_tenant.id,
        "name": current_tenant.name,
        "tier": getattr(current_tenant, "tier", "community"),
    }
