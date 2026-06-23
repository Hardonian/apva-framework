"""ClickHouse OLAP Analytics Interface (Mock)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

class ClickHouseClient:
    """Mock interface for connecting to a ClickHouse OLAP cluster.
    
    In a true enterprise environment with millions of rows, PostgreSQL is too slow
    for aggregating True Value Yield metrics. ClickHouse provides sub-second analytics
    over massive datasets. This client simulates that connection.
    """
    
    @classmethod
    async def insert_telemetry(cls, payload: dict[str, Any]) -> None:
        """Insert a flattened telemetry event directly into ClickHouse."""
        # Represents: clickhouse.execute('INSERT INTO apva.telemetry VALUES ...', [payload])
        logger.debug("[CLICKHOUSE] Inserted telemetry event for tenant_id=%s", payload.get("tenant_id"))
        
    @classmethod
    async def insert_evaluation(cls, payload: dict[str, Any]) -> None:
        """Insert a flattened evaluation result directly into ClickHouse."""
        # Represents: clickhouse.execute('INSERT INTO apva.evaluations VALUES ...', [payload])
        logger.debug("[CLICKHOUSE] Inserted evaluation result for tenant_id=%s", payload.get("tenant_id"))
        
    @classmethod
    async def query_tvy_metrics(cls, tenant_id: int) -> dict[str, Any]:
        """Execute a blazingly fast OLAP query to aggregate TVY."""
        logger.debug("[CLICKHOUSE] Executing aggregation query for tenant_id=%d", tenant_id)
        # Mocking the sub-second response
        return {
            "telemetry_count": 5201,
            "evaluation_count": 489,
            "avg_gross_time_saved_min": 14.5,
            "avg_guardrail_tax_min": 0.5,
            "avg_rag_reliability_coefficient": 0.94,
        }
