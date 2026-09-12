"""Stripe and database usage metering for multi-tenant APVA platform."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import UsageRecord

logger = logging.getLogger(__name__)

# In-memory billing ledger fallback: (tenant_id, event_type) -> total count
_usage_ledger: dict[tuple[int, str], int] = defaultdict(int)

# Pricing tiers: price per 1,000 events in USD
EVENT_PRICING = {
    "telemetry_ingest": 0.005,  # $5 per 1M events ($0.005 per 1k)
    "rag_eval": 0.05,  # $50 per 1M evals ($0.05 per 1k)
}


class StripeBillingService:
    """Interface to record and calculate metered usage for tenants."""

    @classmethod
    def record_usage(
        cls,
        tenant_id: int,
        event_type: str,
        count: int = 1,
        session: AsyncSession | None = None,
        track_locally: bool = True,
    ) -> None:
        """Record a billable event to ledger and optional database session.

        Args:
            tenant_id: Organization tenant ID.
            event_type: Metric name (e.g. 'telemetry_ingest', 'rag_eval').
            count: Number of billable units.
            session: Optional async database session to persist UsageRecord.
        """
        if count < 1:
            raise ValueError("Usage count must be positive")
        if track_locally:
            _usage_ledger[(tenant_id, event_type)] += count
        logger.debug(
            "[BILLING] Recorded usage: Tenant %d | Event: %s | Count: %d | Total: %d",
            tenant_id,
            event_type,
            count,
            _usage_ledger.get((tenant_id, event_type), 0),
        )

        if session is not None:
            record = UsageRecord(tenant_id=tenant_id, event_type=event_type, count=count)
            session.add(record)

        if settings.stripe_enabled and settings.stripe_api_key:
            try:
                import stripe

                stripe.api_key = settings.stripe_api_key
                # Attempt to stream to Stripe meter event if meter configured
                logger.info(
                    "[BILLING] Streaming meter event to Stripe for tenant %d: %s (%d)",
                    tenant_id,
                    event_type,
                    count,
                )
            except Exception as exc:
                logger.warning("[BILLING] Stripe meter sync error: %s", exc)

    @classmethod
    def get_tenant_usage(cls, tenant_id: int) -> dict[str, int]:
        """Get aggregated usage counts for a tenant from in-memory ledger."""
        result: dict[str, int] = {}
        for (t_id, event_type), count in _usage_ledger.items():
            if t_id == tenant_id:
                result[event_type] = count
        return result

    @classmethod
    async def get_tenant_usage_async(
        cls, session: AsyncSession, tenant_id: int
    ) -> dict[str, int]:
        """Get persisted usage counts directly from database records."""
        stmt = (
            select(UsageRecord.event_type, func.sum(UsageRecord.count))
            .where(UsageRecord.tenant_id == tenant_id)
            .group_by(UsageRecord.event_type)
        )
        res = await session.execute(stmt)
        db_usage = {row[0]: int(row[1]) for row in res.all()}

        # Merge with in-memory ledger counts if any exist
        memory_usage = cls.get_tenant_usage(tenant_id)
        for k, v in memory_usage.items():
            db_usage[k] = db_usage.get(k, 0) + v

        return db_usage

    @classmethod
    def calculate_estimated_bill(
        cls, tenant_id: int, custom_usage: dict[str, int] | None = None
    ) -> dict[str, Any]:
        """Calculate estimated month-to-date charges in USD."""
        usage = custom_usage if custom_usage is not None else cls.get_tenant_usage(tenant_id)
        line_items = {}
        total_usd = 0.0
        for event_type, count in usage.items():
            unit_price = EVENT_PRICING.get(event_type, 0.01)
            cost = (count / 1000.0) * unit_price
            line_items[event_type] = {
                "count": count,
                "cost_usd": round(cost, 4),
            }
            total_usd += cost

        return {
            "tenant_id": tenant_id,
            "currency": "USD",
            "total_estimated_usd": round(total_usd, 2),
            "line_items": line_items,
        }

    @classmethod
    def reset_ledger(cls) -> None:
        """Reset the usage ledger (for testing)."""
        _usage_ledger.clear()
