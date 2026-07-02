"""High-throughput event streaming backbone for Enterprise APVA."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import EvaluationJob, TelemetryEvent, UsageRecord
from ..services.billing import StripeBillingService
from ..services.clickhouse import ClickHouseClient

logger = logging.getLogger(__name__)


class EventStreamer:
    """Facade for publishing events to Kafka/ClickHouse and billing.

    This abstracts away the underlying datastores. In this MVP, it falls back
    to synchronous SQLAlchemy writes to simulate exactly what the message queue
    consumer would do asynchronously.
    """

    @classmethod
    async def publish_telemetry(
        cls,
        session: AsyncSession,
        tenant_id: int,
        payload: dict[str, Any]
    ) -> TelemetryEvent:
        """Publish a telemetry event into the ingestion pipeline."""
        # 1. Fire to Billing Meter
        StripeBillingService.record_usage(tenant_id, "telemetry_ingest", 1)

        # 2. Fire to ClickHouse (OLAP Engine)
        await ClickHouseClient.insert_telemetry(payload)

        # 3. Write to persistent store (simulating Kafka consumer sinking to Postgres)
        event = TelemetryEvent(
            tenant_id=tenant_id,
            **payload
        )
        session.add(event)

        # Also track the usage explicitly in the local DB
        usage = UsageRecord(tenant_id=tenant_id, event_type="telemetry_ingest", count=1)
        session.add(usage)

        await session.commit()
        await session.refresh(event)
        return event

    @classmethod
    async def publish_eval(
        cls,
        session: AsyncSession,
        tenant_id: int,
        payload: dict[str, Any]
    ) -> EvaluationJob:
        """Publish an evaluation job to the processing queue."""
        # 1. Fire to Billing Meter
        StripeBillingService.record_usage(tenant_id, "rag_eval", 1)

        # 2. Fire to ClickHouse (OLAP Engine)
        await ClickHouseClient.insert_evaluation(payload)

        # 3. Write to persistent store
        job = EvaluationJob(
            tenant_id=tenant_id,
            **payload
        )
        session.add(job)

        usage = UsageRecord(tenant_id=tenant_id, event_type="rag_eval", count=1)
        session.add(usage)

        await session.commit()
        await session.refresh(job)
        return job