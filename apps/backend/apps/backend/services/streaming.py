"""High-throughput event streaming backbone for Enterprise APVA."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import EvaluationJob, TelemetryEvent, UsageRecord
from ..services.billing import StripeBillingService
from ..services.clickhouse import ClickHouseClient
from ..services.metrics import invalidate_metrics_cache
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
        is_valid = circuit_breaker.validate_guardrail_latency(tax)
        if not is_valid:
            if circuit_breaker.strict_mode:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=400,
                    detail=f"Circuit Breaker Triggered: Guardrail tax {tax:.2f}m exceeds tenant maximum allowable threshold in strict mode.",
                )
            payload["is_shadow"] = True

        # Persist the source of truth before attempting optional external sinks.
        event = TelemetryEvent(
            tenant_id=tenant_id,
            **payload,
        )
        session.add(event)

        # Also track the usage explicitly in the local DB
        usage = UsageRecord(tenant_id=tenant_id, event_type="telemetry_ingest", count=1)
        session.add(usage)

        await session.commit()
        invalidate_metrics_cache(tenant_id)

        try:
            StripeBillingService.record_usage(
                tenant_id, "telemetry_ingest", 1, track_locally=False
            )
        except Exception as exc:
            logger.warning("[EventStreamer] Failed to record billing usage: %s", exc)
        try:
            await ClickHouseClient.insert_telemetry({**payload, "tenant_id": tenant_id})
        except Exception as exc:
            logger.warning("[EventStreamer] Failed to insert ClickHouse telemetry: %s", exc)
        return event

    @classmethod
    async def publish_telemetry_batch(
        cls,
        session: AsyncSession,
        tenant_id: int,
        payloads: list[dict[str, Any]],
    ) -> list[TelemetryEvent]:
        """Publish a batch of telemetry events in a single optimized database transaction."""
        circuit_breaker = SafeguardCircuitBreaker(tenant_id)
        events: list[TelemetryEvent] = []

        for payload in payloads:
            if "event_metadata" in payload and payload["event_metadata"]:
                payload["event_metadata"] = circuit_breaker.sanitize_metadata(payload["event_metadata"])

            tax = payload.get("guardrail_latency_tax", 0.0)
            is_valid = circuit_breaker.validate_guardrail_latency(tax)
            if not is_valid:
                if circuit_breaker.strict_mode:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=400,
                        detail=f"Circuit Breaker Triggered: Guardrail tax {tax:.2f}m exceeds threshold in strict mode.",
                    )
                payload["is_shadow"] = True

            event = TelemetryEvent(tenant_id=tenant_id, **payload)
            events.append(event)
        session.add_all(events)
        session.add(
            UsageRecord(
                tenant_id=tenant_id,
                event_type="telemetry_ingest",
                count=len(events),
            )
        )

        await session.commit()
        invalidate_metrics_cache(tenant_id)
        try:
            StripeBillingService.record_usage(
                tenant_id,
                "telemetry_ingest",
                len(payloads),
                track_locally=False,
            )
        except Exception as exc:
            logger.warning("[EventStreamer] Failed to record batch billing usage: %s", exc)
        try:
            await ClickHouseClient.insert_telemetry_batch(
                [{**payload, "tenant_id": tenant_id} for payload in payloads]
            )
        except Exception as exc:
            logger.warning("[EventStreamer] Failed to insert ClickHouse batch: %s", exc)
        return events

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
        if "expected_answer" in payload and payload["expected_answer"]:
            payload["expected_answer"] = circuit_breaker.redact_pii(payload["expected_answer"])

        # Persist the source of truth before attempting optional external sinks.
        job = EvaluationJob(
            tenant_id=tenant_id,
            **payload,
        )
        session.add(job)

        usage = UsageRecord(tenant_id=tenant_id, event_type="rag_eval", count=1)
        session.add(usage)

        await session.commit()
        invalidate_metrics_cache(tenant_id)
        try:
            StripeBillingService.record_usage(tenant_id, "rag_eval", 1, track_locally=False)
        except Exception as exc:
            logger.warning("[EventStreamer] Failed to record eval billing usage: %s", exc)
        try:
            await ClickHouseClient.insert_evaluation({**payload, "tenant_id": tenant_id})
        except Exception as exc:
            logger.warning("[EventStreamer] Failed to insert ClickHouse evaluation: %s", exc)
        return job

    @classmethod
    async def publish_eval_batch(
        cls,
        session: AsyncSession,
        tenant_id: int,
        payloads: list[dict[str, Any]],
    ) -> list[EvaluationJob]:
        """Persist and meter multiple evaluation jobs in one transaction."""
        circuit_breaker = SafeguardCircuitBreaker(tenant_id)
        jobs: list[EvaluationJob] = []
        for payload in payloads:
            sanitized = dict(payload)
            for field in ("query", "context", "answer", "expected_answer"):
                if sanitized.get(field):
                    sanitized[field] = circuit_breaker.redact_pii(sanitized[field])
            jobs.append(EvaluationJob(tenant_id=tenant_id, **sanitized))

        session.add_all(jobs)
        session.add(
            UsageRecord(tenant_id=tenant_id, event_type="rag_eval", count=len(jobs))
        )
        await session.commit()
        invalidate_metrics_cache(tenant_id)

        try:
            StripeBillingService.record_usage(
                tenant_id, "rag_eval", len(jobs), track_locally=False
            )
        except Exception as exc:
            logger.warning("[EventStreamer] Failed to record batch eval usage: %s", exc)
        try:
            await ClickHouseClient.insert_evaluation_batch(
                [{**payload, "tenant_id": tenant_id} for payload in payloads]
            )
        except Exception as exc:
            logger.warning("[EventStreamer] Failed to insert ClickHouse eval batch: %s", exc)
        return jobs
