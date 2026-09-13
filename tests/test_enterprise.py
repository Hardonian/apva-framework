"""Tests for enterprise business cases, portfolios, API, SDK, and workflow gates."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import httpx
import pytest
from apva_sdk.enterprise import APVAEnterpriseClient, APVAWorkflowGateError
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import delete

from apps.backend.apps.backend.database import async_session_maker
from apps.backend.apps.backend.dependencies import get_tenant_context
from apps.backend.apps.backend.main import app
from apps.backend.apps.backend.models import TelemetryEvent, Tenant
from apps.backend.apps.backend.services.metrics import reset_metrics_cache
from apva.cli import main
from apva.enterprise import (
    DecisionStatus,
    EnterpriseAnalysisRequest,
    EnterpriseValueEngine,
    PortfolioAnalysisRequest,
    ScenarioMatrix,
)


def _request(*, matrix: bool = True) -> EnterpriseAnalysisRequest:
    payload = json.loads(Path("examples/enterprise-business-case.json").read_text(encoding="utf-8"))
    payload["monte_carlo_simulations"] = 100
    payload["include_scenario_matrix"] = matrix
    if matrix:
        payload["scenario_matrix"] = {
            "adoption_rates": [0.5, 0.8],
            "reliability_multipliers": [0.9, 1.0],
            "cost_multipliers": [0.8, 1.2],
            "volume_multipliers": [0.75, 1.25],
        }
    return EnterpriseAnalysisRequest.model_validate(payload)


def test_enterprise_business_case_is_auditable_and_deterministic() -> None:
    request = _request()
    first = EnterpriseValueEngine.analyze(request)
    second = EnterpriseValueEngine.analyze(request)

    assert first.report_id == second.report_id
    assert first.downside_tvy_min == second.downside_tvy_min
    assert first.decision == DecisionStatus.SCALE
    assert first.first_year_net_value_usd > 0
    assert first.net_present_value_usd > first.first_year_net_value_usd
    assert first.payback_months is not None and first.payback_months < 18
    assert first.positive_scenario_rate == 1.0
    assert len(first.scenario_matrix) == 16
    assert len(first.gate_checks) == 7
    assert all(check.passed for check in first.gate_checks)
    assert first.top_levers
    assert len(first.audit_trail["input_sha256"]) == 64
    assert len(first.projections) == request.business_case.analysis_years


def test_enterprise_request_requires_financial_inputs() -> None:
    payload = _request(matrix=False).model_dump()
    payload["benchmark"]["productivity"]["hourly_rate_usd"] = None
    with pytest.raises(ValidationError, match="hourly_rate_usd"):
        EnterpriseAnalysisRequest.model_validate(payload)


def test_scenario_matrix_has_bounded_computational_cost() -> None:
    with pytest.raises(ValidationError, match="500 combinations"):
        ScenarioMatrix(
            adoption_rates=[index / 10 for index in range(1, 10)],
            reliability_multipliers=[0.8, 0.9, 1.0, 1.1],
            cost_multipliers=[0.8, 0.9, 1.0, 1.1],
            volume_multipliers=[0.7, 0.8, 0.9, 1.0],
        )


def test_portfolio_ranks_and_funds_only_eligible_cases() -> None:
    strong = _request(matrix=False)
    weak_payload = strong.model_dump()
    weak_payload["benchmark"]["name"] = "high-friction-negative-case"
    weak_payload["benchmark"]["productivity"]["ai_generation_time_min"] = 45.0
    weak_payload["benchmark"]["productivity"]["epistemic_verification_time_min"] = 20.0
    weak_payload["business_case"]["annual_risk_avoidance_usd"] = 0.0
    weak = EnterpriseAnalysisRequest.model_validate(weak_payload)

    portfolio = EnterpriseValueEngine.analyze_portfolio(
        PortfolioAnalysisRequest(
            cases=[weak, strong],
            investment_budget_usd=strong.business_case.implementation_cost_usd,
        )
    )

    assert portfolio.rankings[0].use_case == strong.benchmark.name
    assert portfolio.rankings[0].funded is True
    assert portfolio.rankings[1].funded is False
    assert portfolio.recommended_capital_usd == strong.business_case.implementation_cost_usd
    assert portfolio.scale_ready_count == 1


@pytest.mark.anyio
async def test_observed_telemetry_becomes_enterprise_business_case() -> None:
    tenant_id = 100_000 + uuid.uuid4().int % 1_000_000_000
    async with async_session_maker() as session:
        session.add(Tenant(id=tenant_id, name="Observed Enterprise", api_key_hash=uuid.uuid4().hex))
        session.add(
            TelemetryEvent(
                tenant_id=tenant_id,
                app_name="copilot",
                session_id=uuid.uuid4().hex,
                run_id=uuid.uuid4().hex,
                human_baseline_time=40.0,
                ai_augmented_time=8.0,
                guardrail_latency_tax=0.3,
                session_iterations=1,
                hourly_rate_usd=100.0,
                is_shadow=False,
                event_metadata={},
            )
        )
        await session.commit()
    reset_metrics_cache()
    app.dependency_overrides[get_tenant_context] = lambda: {
        "tenant_id": tenant_id,
        "name": "Observed Enterprise",
    }
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/analysis/observed-business-case",
                json={
                    "use_case_name": "Observed Copilot",
                    "business_case": {
                        "practitioners": 100,
                        "tasks_per_practitioner_per_day": 3.0,
                        "implementation_cost_usd": 50000.0,
                        "annual_platform_cost_usd": 25000.0,
                    },
                    "include_scenario_matrix": False,
                    "monte_carlo_simulations": 100,
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["use_case"] == "Observed Copilot"
        assert data["audit_trail"]["source"] == "observed_tenant_aggregates"
        assert data["audit_trail"]["telemetry_sample_size"] == 1
        assert response.headers["x-apva-report-id"] == data["report_id"]
    finally:
        app.dependency_overrides.clear()
        async with async_session_maker() as session:
            await session.execute(delete(TelemetryEvent).where(TelemetryEvent.tenant_id == tenant_id))
            await session.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await session.commit()


def test_enterprise_sdk_analysis_and_gate() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "report_id": "apva-test",
                "decision": "controlled_pilot",
                "gate_checks": [
                    {"label": "Evidence Confidence", "passed": False},
                ],
            },
        )

    with APVAEnterpriseClient(
        api_url="https://apva.example/api/v1",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    ) as client:
        report = client.analyze_business_case({"benchmark": {}})
        client.require_decision(report, allowed=("scale", "controlled_pilot"))
        with pytest.raises(APVAWorkflowGateError, match="Evidence Confidence"):
            client.require_decision(report)


def test_business_case_cli_and_policy_exit_code(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "case.json"
    path.write_text(json.dumps(_request(matrix=False).model_dump(mode="json")), encoding="utf-8")
    assert main(["business-case", str(path), "--format", "json", "--require-decision", "scale"]) == 0
    assert '"decision": "scale"' in capsys.readouterr().out
    assert (
        main(
            [
                "business-case",
                str(path),
                "--require-decision",
                "do_not_scale",
            ]
        )
        == 1
    )
