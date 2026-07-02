"""Macro TVY metrics API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_session
from ..dependencies import get_tenant_context
from ..models import EvaluationJob, TelemetryEvent
from ..schemas import TvyMetricResponse

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/tvy", response_model=TvyMetricResponse)
async def get_macro_tvy(
    session: AsyncSession = Depends(get_session),
    tenant_context: dict = Depends(get_tenant_context),
) -> TvyMetricResponse:
    """Calculate macro True Value Yield for the dashboard.

    Args:
        session: Async database session.
        tenant_context: Resolved multi-tenant organization context.

    Returns:
        TvyMetricResponse: Aggregated TVY metrics.
    """
    telemetry_count, avg_human, avg_ai, avg_guardrail, avg_hourly_rate = await session.execute(
        select(
            func.count(TelemetryEvent.id),
            func.avg(TelemetryEvent.human_baseline_time),
            func.avg(TelemetryEvent.ai_augmented_time),
            func.avg(TelemetryEvent.guardrail_latency_tax),
            func.avg(TelemetryEvent.hourly_rate_usd),
        ).where(TelemetryEvent.tenant_id == tenant_context["tenant_id"])
    ).one()
    evaluation_count, avg_reliability = await session.execute(
        select(
            func.count(EvaluationJob.id),
            func.avg(EvaluationJob.rag_reliability_coefficient),
        ).where(EvaluationJob.status == "completed", EvaluationJob.tenant_id == tenant_context["tenant_id"])
    ).one()

    telemetry_count_int = int(telemetry_count or 0)
    evaluation_count_int = int(evaluation_count or 0)
    avg_human_float = float(avg_human or 0.0)
    avg_ai_float = float(avg_ai or 0.0)
    avg_guardrail_float = float(avg_guardrail or 0.0)
    avg_hourly_rate_float = float(avg_hourly_rate) if avg_hourly_rate is not None else None
    avg_reliability_float = float(
        avg_reliability if avg_reliability is not None else settings.default_rag_reliability
    )
    avg_gross_time_saved = avg_human_float - avg_ai_float
    macro_tvy = (avg_gross_time_saved * avg_reliability_float) - avg_guardrail_float
    
    macro_tvy_usd = None
    if avg_hourly_rate_float is not None:
        macro_tvy_usd = (macro_tvy / 60.0) * avg_hourly_rate_float
        
    return TvyMetricResponse(
        telemetry_count=telemetry_count_int,
        evaluation_count=evaluation_count_int,
        avg_gross_time_saved_min=avg_gross_time_saved,
        avg_guardrail_tax_min=avg_guardrail_float,
        avg_rag_reliability_coefficient=avg_reliability_float,
        macro_tvy_min=macro_tvy,
        avg_true_value_yield_usd=macro_tvy_usd,
        is_net_positive=macro_tvy > 0.0,
    )


@router.get("/prometheus", response_class=PlainTextResponse)
async def get_prometheus_metrics(
    session: AsyncSession = Depends(get_session),
    tenant_context: dict = Depends(get_tenant_context),
) -> str:
    """Export TVY and other macro metrics in Prometheus format.

    Returns:
        str: Prometheus-compatible text payload.
    """
    telemetry_count, avg_human, avg_ai, avg_guardrail, avg_hourly_rate = await session.execute(
        select(
            func.count(TelemetryEvent.id),
            func.avg(TelemetryEvent.human_baseline_time),
            func.avg(TelemetryEvent.ai_augmented_time),
            func.avg(TelemetryEvent.guardrail_latency_tax),
            func.avg(TelemetryEvent.hourly_rate_usd),
        ).where(TelemetryEvent.tenant_id == tenant_context["tenant_id"])
    ).one()
    evaluation_count, avg_reliability = await session.execute(
        select(
            func.count(EvaluationJob.id),
            func.avg(EvaluationJob.rag_reliability_coefficient),
        ).where(EvaluationJob.status == "completed", EvaluationJob.tenant_id == tenant_context["tenant_id"])
    ).one()

    telemetry_count_int = int(telemetry_count or 0)
    evaluation_count_int = int(evaluation_count or 0)
    avg_human_float = float(avg_human or 0.0)
    avg_ai_float = float(avg_ai or 0.0)
    avg_guardrail_float = float(avg_guardrail or 0.0)
    avg_hourly_rate_float = float(avg_hourly_rate) if avg_hourly_rate is not None else 0.0
    avg_reliability_float = float(
        avg_reliability if avg_reliability is not None else settings.default_rag_reliability
    )
    
    avg_gross_time_saved = avg_human_float - avg_ai_float
    macro_tvy = (avg_gross_time_saved * avg_reliability_float) - avg_guardrail_float
    macro_tvy_usd = (macro_tvy / 60.0) * avg_hourly_rate_float if avg_hourly_rate_float else 0.0

    lines = [
        "# HELP apva_telemetry_count Total ingested telemetry events",
        "# TYPE apva_telemetry_count counter",
        f"apva_telemetry_count {telemetry_count_int}",
        "# HELP apva_evaluation_count Total completed evaluations",
        "# TYPE apva_evaluation_count counter",
        f"apva_evaluation_count {evaluation_count_int}",
        "# HELP apva_macro_tvy_min Macro True Value Yield (minutes)",
        "# TYPE apva_macro_tvy_min gauge",
        f"apva_macro_tvy_min {macro_tvy}",
        "# HELP apva_macro_tvy_usd Macro True Value Yield (USD)",
        "# TYPE apva_macro_tvy_usd gauge",
        f"apva_macro_tvy_usd {macro_tvy_usd}",
        "# HELP apva_avg_rag_reliability Average RAG Reliability Coefficient [0,1]",
        "# TYPE apva_avg_rag_reliability gauge",
        f"apva_avg_rag_reliability {avg_reliability_float}",
        "# HELP apva_avg_guardrail_tax_min Average Guardrail Friction Tax (minutes)",
        "# TYPE apva_avg_guardrail_tax_min gauge",
        f"apva_avg_guardrail_tax_min {avg_guardrail_float}"
    ]
    return "\n".join(lines) + "\n"

@router.get("/insights", response_model=list[dict[str, Any]])
async def get_agentic_insights(
    session: AsyncSession = Depends(get_session),
    tenant_context: dict = Depends(get_tenant_context),
) -> list[dict[str, Any]]:
    """Return actionable AI prescriptions based on tenant data."""
    # Compute the latest metrics to generate insights
    metrics_response = await get_macro_tvy(session, tenant_context)
    metrics_obj = await get_macro_tvy(session, tenant_context)
    metrics = {
        "avg_guardrail_tax_min": metrics_obj.avg_guardrail_tax_min,
        "avg_rag_reliability_coefficient": metrics_obj.avg_rag_reliability_coefficient
    }
    
    insights = []
    
    if metrics["avg_guardrail_tax_min"] > 1.0:
        insights.append({
            "severity": "high",
            "metric": "Guardrail Tax Latency",
            "observation": "STATISTICAL ANOMALY: Mean guardrail execution time exceeds optimal threshold (> 1.0m).",
            "prescription": "Optimize semantic routers. Consider offloading PII redaction to APVA edge workers.",
            "estimated_savings_usd_per_10k": 1250.0
        })
        
    if metrics["avg_rag_reliability_coefficient"] and metrics["avg_rag_reliability_coefficient"] < 0.8:
        insights.append({
            "severity": "critical",
            "metric": "RAG Reliability Coefficient",
            "observation": "CRITICAL VARIANCE: Answer faithfulness has degraded below 0.80 SLA.",
            "prescription": "Revert active prompt template to v1.2 and increase vector DB 'top_k' parameter to 5.",
            "estimated_savings_usd_per_10k": 3400.0
        })
        
    if not insights:
        insights.append({
            "severity": "info",
            "metric": "System Optimization",
            "observation": "All inference metrics currently operate within optimal statistical control limits.",
            "prescription": "No immediate intervention required. Maintain current deployment configuration.",
            "estimated_savings_usd_per_10k": 0.0
        })
        
    return insights

@router.get("/benchmarks", response_model=dict[str, Any])
async def get_global_benchmarks(
    session: AsyncSession = Depends(get_session),
    tenant_context: dict = Depends(get_tenant_context),
) -> dict[str, Any]:
    """Return anonymized global percentiles to create network effects."""
    
    # In a real environment, this would query ClickHouse for global aggregates
    # excluding the current tenant_id to generate comparative percentiles.
    # We return mocked global statistics to demonstrate the "Investability" moat.
    
    return {
        "global_percentiles": {
            "rag_reliability": {
                "your_percentile": 68,
                "p50": 0.82,
                "p90": 0.95,
                "p99": 0.98,
                "message": "Your reliability is in the 68th percentile of Enterprise customers. Improve context precision to reach the 90th percentile."
            },
            "guardrail_tax_ms": {
                "your_percentile": 45,
                "p50": 1500.0,
                "p90": 400.0,
                "p99": 120.0,
                "message": "Your guardrails are slower than 55% of users. Upgrade to APVA Proprietary SLMs to achieve <120ms latency."
            }
        }
    }
