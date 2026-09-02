"""Tests for APVA multi-tenant billing and Stripe usage metering."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from apps.backend.apps.backend.dependencies import get_tenant_context
from apps.backend.apps.backend.main import app
from apps.backend.apps.backend.services.billing import StripeBillingService


@pytest.fixture()
async def api():
    app.dependency_overrides[get_tenant_context] = lambda: {"tenant_id": 42, "name": "Billing Corp"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def test_billing_record_and_calculation():
    StripeBillingService.reset_ledger()

    # Record 10,000 telemetry events and 1,000 rag evals for tenant 42
    StripeBillingService.record_usage(tenant_id=42, event_type="telemetry_ingest", count=10000)
    StripeBillingService.record_usage(tenant_id=42, event_type="rag_eval", count=1000)

    usage = StripeBillingService.get_tenant_usage(tenant_id=42)
    assert usage["telemetry_ingest"] == 10000
    assert usage["rag_eval"] == 1000

    bill = StripeBillingService.calculate_estimated_bill(tenant_id=42)
    assert bill["tenant_id"] == 42
    assert "line_items" in bill
    assert bill["line_items"]["telemetry_ingest"]["count"] == 10000
    assert bill["line_items"]["rag_eval"]["count"] == 1000
    # 10k * $0.005/1k = $0.05
    # 1k * $0.05/1k = $0.05
    # total = $0.10
    assert bill["total_estimated_usd"] == 0.10


@pytest.mark.anyio
async def test_billing_api_endpoints(api: AsyncClient):
    StripeBillingService.reset_ledger()
    StripeBillingService.record_usage(tenant_id=42, event_type="telemetry_ingest", count=2000)

    # Test /api/v1/billing/usage
    res = await api.get("/api/v1/billing/usage")
    assert res.status_code == 200
    data = res.json()
    assert data["tenant_id"] == 42
    assert data["usage"]["telemetry_ingest"] == 2000

    # Test /api/v1/billing/estimate
    res_est = await api.get("/api/v1/billing/estimate")
    assert res_est.status_code == 200
    est_data = res_est.json()
    assert est_data["tenant_id"] == 42
    assert "line_items" in est_data
    assert est_data["total_estimated_usd"] > 0
