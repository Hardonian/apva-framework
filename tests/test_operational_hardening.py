"""Regression tests for performance, observability, and tenant hardening."""

from __future__ import annotations

import base64
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select

from apps.backend.apps.backend.config import settings
from apps.backend.apps.backend.database import async_session_maker
from apps.backend.apps.backend.dependencies import get_tenant_context
from apps.backend.apps.backend.jwt_auth import create_access_token, decode_access_token
from apps.backend.apps.backend.main import app
from apps.backend.apps.backend.models import EvaluationJob, TelemetryEvent, Tenant, UsageRecord
from apps.backend.apps.backend.observability import RuntimeMetrics
from apps.backend.apps.backend.services.billing import StripeBillingService
from apps.backend.apps.backend.services.metrics import reset_metrics_cache


def _unique_tenant_id() -> int:
    return 100_000 + (uuid.uuid4().int % 1_000_000_000)


@pytest.mark.anyio
async def test_request_size_limit_and_runtime_metrics() -> None:
    RuntimeMetrics.reset()
    original_limit = settings.max_request_size_bytes
    settings.max_request_size_bytes = 8
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/sso/login",
                content=b'{"email":"too-large@example.com"}',
                headers={"content-type": "application/json", "x-request-id": "bad id with spaces"},
            )
        assert response.status_code == 413
        assert response.headers["x-request-id"] != "bad id with spaces"
        assert "server-timing" in response.headers

        metrics = RuntimeMetrics.render_prometheus()
        assert 'route="__unmatched__",status="413"' in metrics
        assert "apva_http_requests_in_flight 0" in metrics
    finally:
        settings.max_request_size_bytes = original_limit


def test_jwt_rejects_unapproved_algorithm_header() -> None:
    token = create_access_token({"sub": "user@example.com", "tenant_id": 1})
    _, payload, signature = token.split(".")
    bad_header = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "typ": "JWT"}).encode()
    ).decode().rstrip("=")
    assert decode_access_token(f"{bad_header}.{payload}.{signature}") is None


@pytest.mark.anyio
async def test_jwt_for_missing_tenant_is_not_reassigned() -> None:
    token = create_access_token({"sub": "user@example.com", "tenant_id": 2_147_483_647})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/metrics/tvy",
            headers={"authorization": f"Bearer {token}"},
        )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_batch_ingestion_uses_one_persisted_meter_row_and_invalidates_cache() -> None:
    tenant_id = _unique_tenant_id()
    api_key_hash = f"test-{uuid.uuid4().hex}"
    app.dependency_overrides[get_tenant_context] = lambda: {
        "tenant_id": tenant_id,
        "name": "Batch Efficiency",
    }
    reset_metrics_cache()
    RuntimeMetrics.reset()
    StripeBillingService.reset_ledger()

    async with async_session_maker() as session:
        session.add(Tenant(id=tenant_id, name="Batch Efficiency", api_key_hash=api_key_hash))
        await session.commit()

    payload = {
        "events": [
            {
                "app_name": "batch-efficient",
                "session_id": f"session-{index}",
                "run_id": f"run-{uuid.uuid4().hex}",
                "human_baseline_time": 20.0,
                "ai_augmented_time": 5.0,
                "guardrail_latency_tax": 0.2,
                "session_iterations": 1,
                "hourly_rate_usd": 100.0,
            }
            for index in range(3)
        ]
    }
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first_metrics = await client.get("/api/v1/metrics/tvy")
            assert first_metrics.status_code == 200
            cached_metrics = await client.get("/api/v1/metrics/tvy")
            assert cached_metrics.status_code == 200
            ingest = await client.post("/api/v1/telemetry/ingest/batch", json=payload)
            assert ingest.status_code == 201
            refreshed_metrics = await client.get("/api/v1/metrics/tvy")
            assert refreshed_metrics.json()["telemetry_count"] == 3

        async with async_session_maker() as session:
            row_count = await session.scalar(
                select(func.count(UsageRecord.id)).where(UsageRecord.tenant_id == tenant_id)
            )
            metered_units = await session.scalar(
                select(func.sum(UsageRecord.count)).where(UsageRecord.tenant_id == tenant_id)
            )
        assert row_count == 1
        assert metered_units == 3
        process_metrics = RuntimeMetrics.render_prometheus()
        assert 'apva_metrics_cache_events_total{outcome="hit"} 1' in process_metrics
        assert 'apva_metrics_cache_events_total{outcome="miss"} 2' in process_metrics
        assert 'apva_metrics_cache_events_total{outcome="invalidation"} 1' in process_metrics
    finally:
        app.dependency_overrides.clear()
        async with async_session_maker() as session:
            await session.execute(delete(UsageRecord).where(UsageRecord.tenant_id == tenant_id))
            await session.execute(delete(TelemetryEvent).where(TelemetryEvent.tenant_id == tenant_id))
            await session.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await session.commit()


@pytest.mark.anyio
async def test_evaluation_lookup_is_tenant_scoped() -> None:
    owner_id = _unique_tenant_id()
    other_id = _unique_tenant_id()
    async with async_session_maker() as session:
        session.add_all(
            [
                Tenant(id=owner_id, name="Owner", api_key_hash=f"owner-{uuid.uuid4().hex}"),
                Tenant(id=other_id, name="Other", api_key_hash=f"other-{uuid.uuid4().hex}"),
            ]
        )
        job = EvaluationJob(
            tenant_id=owner_id,
            transcript_id=f"private-{uuid.uuid4().hex}",
            query="private query",
            context="private context",
            answer="private answer",
            expected_answer="private expected answer",
            status="completed",
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    app.dependency_overrides[get_tenant_context] = lambda: {
        "tenant_id": other_id,
        "name": "Other",
    }
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/eval/{job_id}")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
        async with async_session_maker() as session:
            await session.execute(delete(EvaluationJob).where(EvaluationJob.id == job_id))
            await session.execute(delete(Tenant).where(Tenant.id.in_([owner_id, other_id])))
            await session.commit()


@pytest.mark.anyio
async def test_timeseries_reports_observed_samples_without_synthetic_values() -> None:
    tenant_id = _unique_tenant_id()
    app.dependency_overrides[get_tenant_context] = lambda: {
        "tenant_id": tenant_id,
        "name": "Empty Trends",
    }
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/metrics/timeseries?days=3")
        assert response.status_code == 200
        points = response.json()
        assert len(points) == 3
        for point in points:
            assert point["tvy"] == 0.0
            assert point["tvyUsd"] == 0.0
            assert point["sample_count"] == 0
            assert point["data_source"] == "no_data"
    finally:
        app.dependency_overrides.clear()
