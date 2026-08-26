"""Tests for APVA macro metrics, Prometheus export, agentic insights, and global benchmarks."""

from __future__ import annotations

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
async def test_get_macro_tvy_endpoint(api: AsyncClient):
    response = await api.get("/api/v1/metrics/tvy")
    assert response.status_code == 200
    data = response.json()
    assert "macro_tvy_min" in data
    assert "avg_gross_time_saved_min" in data
    assert "avg_guardrail_tax_min" in data
    assert "avg_rag_reliability_coefficient" in data
    assert "is_net_positive" in data


@pytest.mark.anyio
async def test_prometheus_metrics_endpoint(api: AsyncClient):
    response = await api.get("/api/v1/metrics/prometheus")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    text = response.text
    assert "apva_telemetry_count" in text
    assert "apva_macro_tvy_min" in text
    assert "apva_avg_rag_reliability" in text


@pytest.mark.anyio
async def test_agentic_insights_endpoint(api: AsyncClient):
    response = await api.get("/api/v1/metrics/insights")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "severity" in data[0]
    assert "prescription" in data[0]


@pytest.mark.anyio
async def test_global_benchmarks_endpoint(api: AsyncClient):
    response = await api.get("/api/v1/metrics/benchmarks")
    assert response.status_code == 200
    data = response.json()
    assert "global_percentiles" in data
    assert "rag_reliability" in data["global_percentiles"]
    assert "guardrail_tax_ms" in data["global_percentiles"]
