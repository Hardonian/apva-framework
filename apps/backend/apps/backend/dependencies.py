"""FastAPI dependencies for APVA backend."""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apps.backend.config import settings

security = HTTPBearer()

def get_tenant_context(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict[str, Any]:
    """Validate API key and resolve to a multi-tenant Organization context.

    Args:
        credentials: Bearer token from the Authorization header.

    Returns:
        dict: The tenant context mapping (e.g. tenant_id).

    Raises:
        HTTPException: If the API key is missing or invalid.
    """
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not settings.api_key or not secrets.compare_digest(credentials.credentials, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Mocking a DB lookup that would resolve the hashed key to a tenant.
    # In a full ORM implementation, this would be: `session.scalar(select(Tenant).where(...))`
    return {"tenant_id": 1, "name": "Acme Corp"}
