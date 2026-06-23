"""FastAPI dependencies for APVA backend."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apps.backend.config import settings

security = HTTPBearer()

def get_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Validate the provided API key against application settings.

    Args:
        credentials: Bearer token from the Authorization header.

    Returns:
        str: The validated API key.

    Raises:
        HTTPException: If the API key is missing or invalid.
    """
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not settings.api_key or credentials.credentials != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials
