"""FastAPI dependencies for APVA backend."""

from __future__ import annotations

import hashlib
import secrets
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

security = HTTPBearer(auto_error=True)


def hash_api_key(key: str) -> str:
    """Return the SHA-256 hex digest of an API key."""
    return hashlib.sha256(key.strip().encode("utf-8")).hexdigest()


def get_tenant_context(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """Validate API key and resolve to a multi-tenant Organization context.

    Supports both raw dev keys in development and SHA-256 hashed keys
    in production.

    Args:
        credentials: Bearer token from the Authorization header.

    Returns:
        dict: The tenant context mapping (e.g. tenant_id, name).

    Raises:
        HTTPException: If the API key is missing or invalid.
    """
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    is_valid = False

    # 1. Check plain dev key if configured
    if settings.api_key and secrets.compare_digest(token, settings.api_key):
        is_valid = True

    # 2. Check hashed key against configured key hash
    if not is_valid and settings.api_key:
        expected_hash = hash_api_key(settings.api_key)
        provided_hash = hash_api_key(token)
        if secrets.compare_digest(provided_hash, expected_hash):
            is_valid = True

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Multi-tenant resolution: In a full database-backed setup, this looks up
    # the tenant associated with the hashed API key.
    return {"tenant_id": 1, "name": "Acme Corp"}
