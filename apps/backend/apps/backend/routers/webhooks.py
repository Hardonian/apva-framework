"""Stripe and external webhook handler for automated lifecycle events."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy import select

from ..config import get_settings
from ..database import AsyncSessionLocal
from ..models import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
) -> dict[str, Any]:
    """Ingest and process incoming Stripe webhook events."""
    settings = get_settings()
    payload = await request.body()

    event: dict[str, Any]
    if settings.stripe_enabled and getattr(settings, "stripe_webhook_secret", None) and stripe_signature:
        try:
            import stripe
            stripe.api_key = settings.stripe_api_key
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, settings.stripe_webhook_secret
            )
        except Exception as exc:
            logger.warning("[Webhook] Stripe signature verification failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Webhook signature verification failed: {exc}",
            )
    else:
        # Fallback to direct JSON parsing if signature check not strictly configured
        try:
            event = await request.json()
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    event_type = event.get("type", "")
    data_object = event.get("data", {}).get("object", {})
    customer_id = data_object.get("customer")

    logger.info("[Webhook] Received Stripe event: %s for customer %s", event_type, customer_id)

    if customer_id and event_type in (
        "customer.subscription.updated",
        "customer.subscription.created",
        "customer.subscription.deleted",
    ):
        async with AsyncSessionLocal() as session:
            stmt = select(Tenant).where(Tenant.stripe_customer_id == customer_id)
            result = await session.execute(stmt)
            tenant = result.scalar_one_or_none()

            if tenant:
                if event_type == "customer.subscription.deleted":
                    tenant.tier = "community"
                elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
                    # Extract tier from plan/product metadata or nickname
                    plan_nickname = data_object.get("plan", {}).get("nickname", "").lower()
                    if "enterprise" in plan_nickname:
                        tenant.tier = "enterprise"
                    elif "business" in plan_nickname:
                        tenant.tier = "business"
                    elif "team" in plan_nickname:
                        tenant.tier = "team"
                await session.commit()
                logger.info("[Webhook] Updated tenant %s tier to %s", tenant.id, tenant.tier)

    return {"status": "received", "event_type": event_type}
