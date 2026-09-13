"""Workflow-ready enterprise business-case and portfolio analysis API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from apva.enterprise import (
    BusinessCaseAssumptions,
    DecisionPolicy,
    EnterpriseAnalysisRequest,
    EnterpriseBusinessCaseReport,
    EnterpriseValueEngine,
    PortfolioAnalysisReport,
    PortfolioAnalysisRequest,
    ScenarioMatrix,
    XFactorInputs,
)
from apva.models import BenchmarkInput, GuardrailMetrics, ProductivityMetrics, RAGMetrics

from ..database import get_session
from ..dependencies import get_tenant_context
from ..services.metrics import compute_macro_tvy_metrics

router = APIRouter(prefix="/analysis", tags=["enterprise-analysis"])


class ObservedBusinessCaseRequest(BaseModel):
    """Business assumptions applied directly to the tenant's observed telemetry."""

    model_config = ConfigDict(extra="forbid")

    use_case_name: str = Field(default="Observed AI Workflow", min_length=1, max_length=255)
    business_case: BusinessCaseAssumptions
    x_factors: XFactorInputs = Field(default_factory=XFactorInputs)
    policy: DecisionPolicy = Field(default_factory=DecisionPolicy)
    scenario_matrix: ScenarioMatrix = Field(default_factory=ScenarioMatrix)
    include_scenario_matrix: bool = True
    monte_carlo_simulations: int = Field(default=1000, ge=100, le=10_000)
    uncertainty_fraction: float = Field(default=0.1, gt=0.0, le=0.5)
    confidence_level: float = Field(default=0.95, ge=0.5, lt=1.0)
    random_seed: int | None = None


@router.post("/business-case", response_model=EnterpriseBusinessCaseReport)
async def analyze_business_case(
    payload: EnterpriseAnalysisRequest,
    response: Response,
    tenant_context: dict[str, Any] = Depends(get_tenant_context),
) -> EnterpriseBusinessCaseReport:
    """Produce a board-ready, policy-gated, multivariate AI business case."""
    report = await run_in_threadpool(EnterpriseValueEngine.analyze, payload)
    report.audit_trail["tenant_id"] = tenant_context["tenant_id"]
    report.audit_trail["tenant_name"] = tenant_context["name"]
    response.headers["X-APVA-Report-ID"] = report.report_id
    return report


@router.post("/observed-business-case", response_model=EnterpriseBusinessCaseReport)
async def analyze_observed_business_case(
    payload: ObservedBusinessCaseRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
    tenant_context: dict[str, Any] = Depends(get_tenant_context),
) -> EnterpriseBusinessCaseReport:
    """Turn live tenant telemetry into an investment case without re-keying measurements."""
    metrics = await compute_macro_tvy_metrics(session, tenant_context["tenant_id"])
    if metrics.telemetry_count == 0:
        raise HTTPException(status_code=422, detail="At least one telemetry event is required")
    if metrics.avg_hourly_rate_usd is None:
        raise HTTPException(
            status_code=422,
            detail="Observed telemetry must include hourly_rate_usd for financial analysis",
        )

    request = EnterpriseAnalysisRequest(
        benchmark=BenchmarkInput(
            name=payload.use_case_name,
            description="Generated from tenant-observed APVA telemetry aggregates.",
            tags=["observed", "enterprise-business-case"],
            productivity=ProductivityMetrics(
                reference_human_baseline_min=metrics.avg_human_baseline_min,
                ai_generation_time_min=metrics.avg_ai_augmented_min,
                epistemic_verification_time_min=0.0,
                hourly_rate_usd=metrics.avg_hourly_rate_usd,
            ),
            rag=RAGMetrics(
                exact_span_recall=metrics.avg_rag_reliability_coefficient,
                llm_faithfulness_score=metrics.avg_rag_reliability_coefficient,
            ),
            guardrail=GuardrailMetrics(
                base_latency_overhead_min=metrics.avg_guardrail_tax_min,
                false_positive_rate=0.0,
                resolution_penalty_time_min=0.0,
                cra_session_drop_penalty_min=0.0,
            ),
        ),
        business_case=payload.business_case.model_copy(
            update={"organization": tenant_context["name"]}
        ),
        x_factors=payload.x_factors,
        policy=payload.policy,
        scenario_matrix=payload.scenario_matrix,
        include_scenario_matrix=payload.include_scenario_matrix,
        monte_carlo_simulations=payload.monte_carlo_simulations,
        uncertainty_fraction=payload.uncertainty_fraction,
        confidence_level=payload.confidence_level,
        random_seed=payload.random_seed,
    )
    report = await run_in_threadpool(EnterpriseValueEngine.analyze, request)
    report.audit_trail.update(
        {
            "tenant_id": tenant_context["tenant_id"],
            "tenant_name": tenant_context["name"],
            "telemetry_sample_size": metrics.telemetry_count,
            "evaluation_sample_size": metrics.evaluation_count,
            "hourly_rate_coverage": metrics.hourly_rate_coverage,
            "source": "observed_tenant_aggregates",
        }
    )
    response.headers["X-APVA-Report-ID"] = report.report_id
    return report


@router.post("/portfolio", response_model=PortfolioAnalysisReport)
async def analyze_portfolio(
    payload: PortfolioAnalysisRequest,
    response: Response,
    tenant_context: dict[str, Any] = Depends(get_tenant_context),
) -> PortfolioAnalysisReport:
    """Rank AI investments and allocate a constrained implementation budget."""
    report = await run_in_threadpool(EnterpriseValueEngine.analyze_portfolio, payload)
    for case in report.cases:
        case.audit_trail["tenant_id"] = tenant_context["tenant_id"]
        case.audit_trail["tenant_name"] = tenant_context["name"]
    response.headers["X-APVA-Report-ID"] = report.report_id
    return report


@router.get("/policy-template", response_model=dict[str, Any])
async def get_policy_template(
    tenant_context: dict[str, Any] = Depends(get_tenant_context),
) -> dict[str, Any]:
    """Return transparent defaults teams can commit as governance policy-as-code."""
    return {
        "tenant_id": tenant_context["tenant_id"],
        "decision_policy": DecisionPolicy().model_dump(),
        "scenario_matrix": ScenarioMatrix().model_dump(),
        "explanation": {
            "scale": "Every financial, reliability, downside, evidence, and friction gate passes.",
            "controlled_pilot": "Core value and reliability pass, but one or more scale gates remain.",
            "optimize": "Value exists, but economics or quality require remediation before a pilot.",
            "do_not_scale": "Current evidence indicates non-positive value or recurring economics.",
        },
    }
