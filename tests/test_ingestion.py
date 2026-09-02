"""Tests for APVA backend API ingestion endpoint."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from apps.backend.apps.backend.dependencies import get_tenant_context
from apps.backend.apps.backend.main import app


@pytest.fixture()
async def api():
    app.dependency_overrides[get_tenant_context] = lambda: {"tenant_id": 1, "name": "Acme Corp"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_ingest_event(api: Any):
    payload = {
        "app_name": "test",
        "session_id": "s1",
        "run_id": "r1",
        "human_baseline_time": 60.0,
        "ai_augmented_time": 10.0,
        "guardrail_latency_tax": 1.0,
        "session_iterations": 1,
        "metadata": {},
    }
    response = await api.post("/api/v1/telemetry/ingest", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["accepted"] is True
    assert isinstance(body["event_id"], int)


@pytest.mark.anyio
async def test_ingest_batch_events(api: Any):
    payload = {
        "events": [
            {
                "app_name": "batch-app",
                "session_id": f"s-{i}",
                "run_id": f"r-{i}",
                "human_baseline_time": 30.0,
                "ai_augmented_time": 5.0,
                "guardrail_latency_tax": 0.5,
                "session_iterations": 1,
                "metadata": {"batch_index": i},
            }
            for i in range(5)
        ]
    }
    response = await api.post("/api/v1/telemetry/ingest/batch", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["accepted_count"] == 5
    assert len(body["event_ids"]) == 5


@pytest.mark.anyio
async def test_ingest_validation_error(api: Any):
    payload = {
        "app_name": "test",
        "session_id": "s1",
        "run_id": "r1",
        "human_baseline_time": -1.0,
        "ai_augmented_time": 10.0,
        "guardrail_latency_tax": 1.0,
        "session_iterations": 1,
    }
    response = await api.post("/api/v1/telemetry/ingest", json=payload)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_health_endpoint(api: Any):
    response = await api.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "apva-backend"
