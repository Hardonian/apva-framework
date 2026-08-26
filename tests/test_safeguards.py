"""Tests for APVA enterprise safeguard policies, circuit breaker, and PII redaction."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from apps.backend.apps.backend.dependencies import get_tenant_context
from apps.backend.apps.backend.main import app
from apps.backend.apps.backend.services.policy import SafeguardCircuitBreaker


@pytest.fixture()
async def api():
    app.dependency_overrides[get_tenant_context] = lambda: {"tenant_id": 1, "name": "Acme Corp"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_get_safeguard_policy(api: AsyncClient):
    response = await api.get("/api/v1/safeguards")
    assert response.status_code == 200
    data = response.json()
    assert "max_guardrail_tax_min" in data
    assert "pii_redaction_enabled" in data
    assert "strict_mode" in data


@pytest.mark.anyio
async def test_update_safeguard_policy(api: AsyncClient):
    payload = {
        "max_guardrail_tax_min": 1.5,
        "pii_redaction_enabled": True,
        "strict_mode": True,
    }
    response = await api.put("/api/v1/safeguards", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["max_guardrail_tax_min"] == 1.5
    assert data["strict_mode"] is True

    # Check that GET returns updated policy
    get_res = await api.get("/api/v1/safeguards")
    assert get_res.json()["max_guardrail_tax_min"] == 1.5


def test_circuit_breaker_latency():
    SafeguardCircuitBreaker.set_policy(10, {"max_guardrail_tax_min": 2.0, "pii_redaction_enabled": True})
    cb = SafeguardCircuitBreaker(tenant_id=10)
    assert cb.validate_guardrail_latency(1.0) is True
    assert cb.validate_guardrail_latency(3.0) is False


def test_circuit_breaker_pii_redaction():
    cb = SafeguardCircuitBreaker(tenant_id=1)
    raw = "User email is john.doe@example.com and SSN is 123-45-6789 with phone 555-123-4567"
    redacted = cb.redact_pii(raw)
    assert "[REDACTED_EMAIL]" in redacted
    assert "john.doe@example.com" not in redacted
    assert "[REDACTED_SSN]" in redacted
    assert "123-45-6789" not in redacted
    assert "[REDACTED_PHONE]" in redacted


def test_circuit_breaker_metadata_sanitization():
    cb = SafeguardCircuitBreaker(tenant_id=1)
    meta = {
        "user": "alice@company.com",
        "nested": {
            "card": "4111 1111 1111 1111",
            "tags": ["contact:bob@test.com", "normal-tag"],
        },
    }
    sanitized = cb.sanitize_metadata(meta)
    assert sanitized["user"] == "[REDACTED_EMAIL]"
    assert "[REDACTED_CARD]" in sanitized["nested"]["card"]
    assert "[REDACTED_EMAIL]" in sanitized["nested"]["tags"][0]
    assert sanitized["nested"]["tags"][1] == "normal-tag"
