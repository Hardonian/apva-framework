"""Tests for APVA backend API ingestion endpoint."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient, ASGITransport

from apps.backend.main import app


@pytest.fixture()
async def api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


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
