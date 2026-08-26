"""Stripe usage metering for multi-tenant APVA platform."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

# In-memory billing ledger: (tenant_id, event_type) -> total count
_usage_ledger: dict[tuple[int, str], int] = defaultdict(int)

# Pricing tiers: price per 1,000 events in USD
EVENT_PRICING = {
    "telemetry_ingest": 0.005,  # $5 per 1M events ($0.005 per 1k)
    "rag_eval": 0.05,          # $50 per 1M evals ($0.05 per 1k)
}


class StripeBillingService:
    """Interface to sync APVA usage events with Stripe for PLG metering."""

    @classmethod
    def record_usage(cls, tenant_id: int, event_type: str, count: int = 1) -> None:
        """Record a billable event to Stripe Metering.

        Args:
            tenant_id: Organization tenant ID.
            event_type: The metric name (e.g. 'telemetry_ingest', 'rag_eval').
            count: Number of billable units.
        """
        _usage_ledger[(tenant_id, event_type)] += count
        logger.debug(
            "[BILLING] Recorded usage: Tenant %d | Event: %s | Count: %d | Total: %d",
            tenant_id,
            event_type,
            count,
            _usage_ledger[(tenant_id, event_type)],
        )

    @classmethod
    def get_tenant_usage(cls, tenant_id: int) -> dict[str, int]:
        """Get aggregated usage counts for a tenant."""
        result: dict[str, int] = {}
        for (t_id, event_type), count in _usage_ledger.items():
            if t_id == tenant_id:
                result[event_type] = count
        return result

    @classmethod
    def calculate_estimated_bill(cls, tenant_id: int) -> dict[str, Any]:
        """Calculate estimated month-to-date charges in USD."""
        usage = cls.get_tenant_usage(tenant_id)
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
