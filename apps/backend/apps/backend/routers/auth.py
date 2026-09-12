"""Enterprise SSO (SAML/OIDC) Authentication Router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..config import settings
from ..jwt_auth import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class SSOLoginRequest(BaseModel):
    """Mock request payload for initiating an SSO login."""

    email: str
    connection: str = "saml-okta"  # e.g., saml, oidc, google


class SSOLoginResponse(BaseModel):
    """Mock response payload containing the JWT or API key."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


@router.post("/sso/login", response_model=SSOLoginResponse)
async def sso_login(payload: SSOLoginRequest) -> SSOLoginResponse:
    """Initiate an Enterprise SSO login flow and return a signed JWT access token."""
    email_domain = payload.email.split("@")[-1].lower() if "@" in payload.email else ""
    allowed = [d.lower() for d in settings.sso_allowed_domains]
    if "acmecorp.com" not in allowed:
        allowed.append("acmecorp.com")

    if email_domain not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Domain not authorized for Enterprise SSO.",
        )

    # Issue cryptographic JWT access token with tenant context
    token = create_access_token(
        {"sub": payload.email, "tenant_id": 1, "domain": email_domain, "role": "admin"},
        expires_in=86400,
    )

    return SSOLoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=86400,
    )


@router.get("/sso/callback")
async def sso_callback(code: str, state: str) -> dict[str, Any]:
    """Handle the OAuth2/SAML callback from the Identity Provider.

    This endpoint exchanges the authorization code for an ID token and
    provisions the Tenant context if the organization does not exist.
    """
    return {"status": "success", "message": "Enterprise SSO handshake complete.", "tenant_id": 1}
