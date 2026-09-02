"""Billing API routes for usage metering and invoice estimation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ..dependencies import get_tenant_context
from ..schemas import BillingEstimateResponse, BillingUsageResponse
from ..services.billing import StripeBillingService

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/usage", response_model=BillingUsageResponse)
async def get_tenant_usage(
    tenant_context: dict[str, Any] = Depends(get_tenant_context),
) -> BillingUsageResponse:
    """Return metered usage counts for the current tenant."""
    tenant_id = tenant_context["tenant_id"]
    usage = StripeBillingService.get_tenant_usage(tenant_id)
    return BillingUsageResponse(tenant_id=tenant_id, usage=usage)


@router.get("/estimate", response_model=BillingEstimateResponse)
async def get_estimated_bill(
    tenant_context: dict[str, Any] = Depends(get_tenant_context),
) -> BillingEstimateResponse:
    """Calculate and return estimated bill based on metered usage."""
    tenant_id = tenant_context["tenant_id"]
    bill = StripeBillingService.calculate_estimated_bill(tenant_id)
    return BillingEstimateResponse(
        tenant_id=bill["tenant_id"],
        line_items=bill["line_items"],
        total_estimated_usd=bill["total_estimated_usd"],
    )
