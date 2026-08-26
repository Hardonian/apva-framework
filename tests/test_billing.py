"""Tests for APVA multi-tenant billing and Stripe usage metering."""

from __future__ import annotations

from apps.backend.apps.backend.services.billing import StripeBillingService


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
