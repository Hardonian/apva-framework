"""High-throughput event streaming backbone for Enterprise APVA."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import EvaluationJob, TelemetryEvent, UsageRecord
from ..services.billing import StripeBillingService
from ..services.clickhouse import ClickHouseClient
from ..services.policy import SafeguardCircuitBreaker

logger = logging.getLogger(__name__)


class EventStreamer:
    """Facade for publishing events to Kafka/ClickHouse, applying safeguards, and billing."""

    @classmethod
    async def publish_telemetry(
        cls,
        session: AsyncSession,
        tenant_id: int,
        payload: dict[str, Any],
    ) -> TelemetryEvent:
        """Publish a telemetry event into the ingestion pipeline."""
        circuit_breaker = SafeguardCircuitBreaker(tenant_id)

        # Sanitize metadata if PII redaction is enabled
        if "event_metadata" in payload and payload["event_metadata"]:
            payload["event_metadata"] = circuit_breaker.sanitize_metadata(payload["event_metadata"])

        # Check circuit breaker on latency tax
        tax = payload.get("guardrail_latency_tax", 0.0)
        circuit_breaker.validate_guardrail_latency(tax)

        # 1. Fire to Billing Meter (isolated)
        try:
            StripeBillingService.record_usage(tenant_id, "telemetry_ingest", 1)
        except Exception as exc:
            logger.warning("[EventStreamer] Failed to record billing usage: %s", exc)

        # 2. Fire to ClickHouse OLAP Engine (isolated)
        try:
            await ClickHouseClient.insert_telemetry(payload)
        except Exception as exc:
            logger.warning("[EventStreamer] Failed to insert ClickHouse telemetry: %s", exc)

        # 3. Write to persistent store
        event = TelemetryEvent(
            tenant_id=tenant_id,
            **payload,
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
        payload: dict[str, Any],
    ) -> EvaluationJob:
        """Publish an evaluation job to the processing queue."""
        circuit_breaker = SafeguardCircuitBreaker(tenant_id)

        # Sanitize text fields if PII redaction is enabled
        if "query" in payload and payload["query"]:
            payload["query"] = circuit_breaker.redact_pii(payload["query"])
        if "context" in payload and payload["context"]:
            payload["context"] = circuit_breaker.redact_pii(payload["context"])
        if "answer" in payload and payload["answer"]:
            payload["answer"] = circuit_breaker.redact_pii(payload["answer"])

        # 1. Fire to Billing Meter (isolated)
        try:
            StripeBillingService.record_usage(tenant_id, "rag_eval", 1)
        except Exception as exc:
            logger.warning("[EventStreamer] Failed to record eval billing usage: %s", exc)

        # 2. Fire to ClickHouse OLAP Engine (isolated)
        try:
            await ClickHouseClient.insert_evaluation(payload)
        except Exception as exc:
            logger.warning("[EventStreamer] Failed to insert ClickHouse evaluation: %s", exc)

        # 3. Write to persistent store
        job = EvaluationJob(
            tenant_id=tenant_id,
            **payload,
        )
        session.add(job)

        usage = UsageRecord(tenant_id=tenant_id, event_type="rag_eval", count=1)
        session.add(usage)

        await session.commit()
        await session.refresh(job)
        return job
