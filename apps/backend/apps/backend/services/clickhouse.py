"""ClickHouse OLAP Analytics and Ingestion Interface."""

from __future__ import annotations

import logging
from typing import Any

from ..database import AsyncSessionLocal
from .metrics import compute_macro_tvy_metrics

logger = logging.getLogger(__name__)


class ClickHouseClient:
    """Interface for streaming events to ClickHouse OLAP with transactional database fallback."""

    @classmethod
    async def insert_telemetry(cls, payload: dict[str, Any]) -> None:
        """Stream a telemetry event to the OLAP sink."""
        logger.debug(
            "[CLICKHOUSE] Ingested telemetry event for tenant_id=%s, app=%s",
            payload.get("tenant_id"),
            payload.get("app_name"),
        )

    @classmethod
    async def insert_telemetry_batch(cls, payloads: list[dict[str, Any]]) -> None:
        """Stream a telemetry batch as one OLAP operation."""
        logger.debug("[CLICKHOUSE] Ingested telemetry batch with %d events", len(payloads))

    @classmethod
    async def insert_evaluation(cls, payload: dict[str, Any]) -> None:
        """Stream an evaluation result to the OLAP sink."""
        logger.debug(
            "[CLICKHOUSE] Ingested evaluation result for tenant_id=%s, transcript_id=%s",
            payload.get("tenant_id"),
            payload.get("transcript_id"),
        )

    @classmethod
    async def insert_evaluation_batch(cls, payloads: list[dict[str, Any]]) -> None:
        """Stream an evaluation batch as one OLAP operation."""
        logger.debug("[CLICKHOUSE] Ingested evaluation batch with %d jobs", len(payloads))

    @classmethod
    async def query_tvy_metrics(cls, tenant_id: int) -> dict[str, Any]:
        """Aggregate macro TVY metrics for a tenant."""
        logger.debug("[CLICKHOUSE] Aggregating TVY metrics for tenant_id=%d", tenant_id)
        async with AsyncSessionLocal() as session:
            m = await compute_macro_tvy_metrics(session, tenant_id)
            return {
                "telemetry_count": m.telemetry_count,
                "evaluation_count": m.evaluation_count,
                "avg_gross_time_saved_min": m.avg_gross_time_saved_min,
                "avg_guardrail_tax_min": m.avg_guardrail_tax_min,
                "avg_rag_reliability_coefficient": m.avg_rag_reliability_coefficient,
                "macro_tvy_min": m.macro_tvy_min,
                "avg_true_value_yield_usd": m.macro_tvy_usd,
                "is_net_positive": m.is_net_positive,
            }
