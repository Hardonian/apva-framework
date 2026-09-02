"""Multi-tenant organization provisioning and API key lifecycle management."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_tenant, hash_api_key
from ..models import Tenant

router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Organization name")
    tier: str = Field(default="community", description="Subscription tier: community, team, business, enterprise")


class TenantResponse(BaseModel):
    id: int
    name: str
    tier: str
    created_at: datetime


class TenantCreateResponse(TenantResponse):
    api_key: str = Field(..., description="Raw API key. Store securely; this cannot be retrieved again.")


class KeyRotationResponse(BaseModel):
    new_api_key: str
    message: str = "API key rotated successfully. Update your clients immediately."


@router.post("", response_model=TenantCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Provision a new tenant organization workspace and generate its primary API key."""
    raw_key = f"apva_{secrets.token_urlsafe(32)}"
    key_hash = hash_api_key(raw_key)

    tenant = Tenant(
        name=body.name,
        api_key_hash=key_hash,
        tier=body.tier.lower(),
        created_at=datetime.now(timezone.utc),
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    return TenantCreateResponse(
        id=tenant.id,
        name=tenant.name,
        tier=tenant.tier,
        created_at=tenant.created_at,
        api_key=raw_key,
    )


@router.get("/me", response_model=TenantResponse)
async def get_tenant_profile(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> Any:
    """Get the profile and tier details for the authenticated organization."""
    return TenantResponse(
        id=current_tenant.id,
        name=current_tenant.name,
        tier=getattr(current_tenant, "tier", "community"),
        created_at=current_tenant.created_at,
    )


@router.post("/rotate-key", response_model=KeyRotationResponse)
async def rotate_api_key(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Rotate the organization's primary API key. The prior key will immediately stop working."""
    new_raw_key = f"apva_{secrets.token_urlsafe(32)}"
    new_hash = hash_api_key(new_raw_key)

    current_tenant.api_key_hash = new_hash
    await db.commit()

    return KeyRotationResponse(new_api_key=new_raw_key)
