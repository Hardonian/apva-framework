"""Tests for multi-tenant provisioning, key rotation, export, and webhooks."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from apps.backend.apps.backend.database import async_session_maker, engine
from apps.backend.apps.backend.dependencies import hash_api_key
from apps.backend.apps.backend.main import app
from apps.backend.apps.backend.models import Base, EvaluationJob, TelemetryEvent, Tenant


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        # Upsert or retrieve tenant 1
        t = await session.get(Tenant, 1)
        if not t:
            t = Tenant(
                id=1,
                name="Alpha Corp",
                api_key_hash=hash_api_key("test_api_key_123"),
                tier="business",
                stripe_customer_id="cus_stripe_123",
            )
            session.add(t)
        else:
            t.api_key_hash = hash_api_key("test_api_key_123")
            t.tier = "business"
            t.stripe_customer_id = "cus_stripe_123"

        # Check telemetry event
        ev_exists = await session.scalar(
            select(TelemetryEvent).where(TelemetryEvent.run_id == "run-export-1")
        )
        if not ev_exists:
            ev = TelemetryEvent(
                tenant_id=1,
                app_name="export-app",
                session_id="sess-export-1",
                run_id="run-export-1",
                human_baseline_time=25.0,
                ai_augmented_time=2.5,
                guardrail_latency_tax=0.4,
                session_iterations=1,
                hourly_rate_usd=90.0,
                is_shadow=False,
                event_metadata={"test": "export"},
            )
            session.add(ev)

        # Check evaluation job
        job_exists = await session.scalar(
            select(EvaluationJob).where(EvaluationJob.transcript_id == "trans-export-1")
        )
        if not job_exists:
            job = EvaluationJob(
                tenant_id=1,
                transcript_id="trans-export-1",
                query="What is TVY?",
                context="TVY is True Value Yield",
                answer="TVY is True Value Yield",
                expected_answer="TVY is True Value Yield",
                status="completed",
                exact_span_recall=1.0,
                llm_faithfulness_score=0.98,
                precision_score=1.0,
                rag_reliability_coefficient=0.99,
            )
            session.add(job)

        await session.commit()

    yield


@pytest.mark.anyio
async def test_tenant_creation_and_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create new tenant
        res = await client.post(
            "/api/v1/tenants",
            json={"name": "Beta Org", "tier": "enterprise"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Beta Org"
        assert data["tier"] == "enterprise"
        new_key = data["api_key"]
        assert new_key.startswith("apva_")

        # 2. Authenticate with new key to get /me
        res_me = await client.get(
            "/api/v1/tenants/me",
            headers={"Authorization": f"Bearer {new_key}"},
        )
        assert res_me.status_code == 200
        assert res_me.json()["name"] == "Beta Org"

        # 3. Rotate key
        res_rot = await client.post(
            "/api/v1/tenants/rotate-key",
            headers={"Authorization": f"Bearer {new_key}"},
        )
        assert res_rot.status_code == 200
        rotated_key = res_rot.json()["new_api_key"]
        assert rotated_key != new_key

        # 4. Prior key fails
        res_fail = await client.get(
            "/api/v1/tenants/me",
            headers={"Authorization": f"Bearer {new_key}"},
        )
        assert res_fail.status_code == 401

        # 5. Rotated key succeeds
        res_succ = await client.get(
            "/api/v1/tenants/me",
            headers={"Authorization": f"Bearer {rotated_key}"},
        )
        assert res_succ.status_code == 200


@pytest.mark.anyio
async def test_export_telemetry():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer test_api_key_123"}

        # JSON Export
        res_json = await client.get("/api/v1/export/telemetry?format=json", headers=headers)
        assert res_json.status_code == 200
        assert res_json.headers["content-type"] == "application/json"
        data = res_json.json()
        assert len(data) >= 1
        assert any(item["app_name"] == "export-app" for item in data)

        # CSV Export
        res_csv = await client.get("/api/v1/export/telemetry?format=csv", headers=headers)
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]
        assert "export-app" in res_csv.text


@pytest.mark.anyio
async def test_export_evaluations():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer test_api_key_123"}

        # JSON Export
        res_json = await client.get("/api/v1/export/evaluations?format=json", headers=headers)
        assert res_json.status_code == 200
        assert res_json.headers["content-type"] == "application/json"
        data = res_json.json()
        assert len(data) >= 1
        assert data[0]["transcript_id"] == "trans-export-1"

        # CSV Export
        res_csv = await client.get("/api/v1/export/evaluations?format=csv", headers=headers)
        assert res_csv.status_code == 200
        assert "trans-export-1" in res_csv.text


@pytest.mark.anyio
async def test_stripe_webhook_subscription_update():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "customer": "cus_stripe_123",
                    "plan": {"nickname": "APVA Enterprise Annual"},
                }
            },
        }
        res = await client.post("/api/v1/webhooks/stripe", json=payload)
        assert res.status_code == 200
        assert res.json()["status"] == "received"

        # Verify tier updated in DB
        res_me = await client.get(
            "/api/v1/tenants/me",
            headers={"Authorization": "Bearer test_api_key_123"},
        )
        assert res_me.status_code == 200
        assert res_me.json()["tier"] == "enterprise"
