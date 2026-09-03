"""Enterprise Safeguard Configurations Router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..dependencies import get_tenant_context
from ..services.policy import SafeguardCircuitBreaker

router = APIRouter(prefix="/safeguards", tags=["safeguards"])


class SafeguardPolicy(BaseModel):
    """Safeguard policy configuration schema."""

    max_guardrail_tax_min: float = Field(default=2.0, ge=0.0, le=60.0)
    pii_redaction_enabled: bool = Field(default=True)
    strict_mode: bool = Field(default=False)


@router.get("", response_model=SafeguardPolicy)
@router.get("/", response_model=SafeguardPolicy, include_in_schema=False)
async def get_safeguard_policy(
    tenant_context: dict[str, Any] = Depends(get_tenant_context),
) -> SafeguardPolicy:
    """Retrieve the current safeguard policies for the authenticated tenant."""
    tenant_id = tenant_context.get("tenant_id", 1)
    policy_data = SafeguardCircuitBreaker.get_policy(tenant_id)
    return SafeguardPolicy.model_validate(policy_data)


@router.put("", response_model=SafeguardPolicy)
@router.put("/", response_model=SafeguardPolicy, include_in_schema=False)
async def update_safeguard_policy(
    policy: SafeguardPolicy,
    tenant_context: dict[str, Any] = Depends(get_tenant_context),
) -> SafeguardPolicy:
    """Update the safeguard policies for the authenticated tenant."""
    tenant_id = tenant_context.get("tenant_id", 1)
    updated = SafeguardCircuitBreaker.set_policy(tenant_id, policy.model_dump())
    return SafeguardPolicy.model_validate(updated)
