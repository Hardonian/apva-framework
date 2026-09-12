"""Tenant-scoped value analytics and operational observability routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_tenant_context
from ..observability import RuntimeMetrics
from ..schemas import TvyMetricResponse
from ..services.metrics import compute_macro_tvy_metrics, compute_tvy_timeseries

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/tvy", response_model=TvyMetricResponse)
async def get_macro_tvy(
    session: AsyncSession = Depends(get_session),
    tenant_context: dict = Depends(get_tenant_context),
) -> TvyMetricResponse:
    """Calculate tenant value, quality, and coverage metrics."""
    metrics = await compute_macro_tvy_metrics(session, tenant_context["tenant_id"])
    return TvyMetricResponse(
        telemetry_count=metrics.telemetry_count,
        evaluation_count=metrics.evaluation_count,
        avg_gross_time_saved_min=metrics.avg_gross_time_saved_min,
        avg_guardrail_tax_min=metrics.avg_guardrail_tax_min,
        avg_rag_reliability_coefficient=metrics.avg_rag_reliability_coefficient,
        macro_tvy_min=metrics.macro_tvy_min,
        avg_true_value_yield_usd=metrics.macro_tvy_usd,
        total_tvy_min=metrics.total_tvy_min,
        total_tvy_usd=metrics.total_tvy_usd,
        value_per_1000_events_usd=metrics.value_per_1000_events_usd,
        shadow_event_count=metrics.shadow_event_count,
        shadow_event_rate=metrics.shadow_event_rate,
        hourly_rate_coverage=metrics.hourly_rate_coverage,
        is_net_positive=metrics.is_net_positive,
    )


@router.get("/prometheus", response_class=PlainTextResponse)
async def get_prometheus_metrics(
    session: AsyncSession = Depends(get_session),
    tenant_context: dict = Depends(get_tenant_context),
) -> str:
    """Export business and process-level metrics in Prometheus format."""
    m = await compute_macro_tvy_metrics(session, tenant_context["tenant_id"])
    business_lines = [
        "# HELP apva_telemetry_count Total ingested telemetry events",
        "# TYPE apva_telemetry_count gauge",
        f"apva_telemetry_count {m.telemetry_count}",
        "# HELP apva_evaluation_count Total completed evaluations",
        "# TYPE apva_evaluation_count gauge",
        f"apva_evaluation_count {m.evaluation_count}",
        "# HELP apva_macro_tvy_min Average True Value Yield in minutes",
        "# TYPE apva_macro_tvy_min gauge",
        f"apva_macro_tvy_min {m.macro_tvy_min}",
        "# HELP apva_total_tvy_min Aggregate True Value Yield in minutes",
        "# TYPE apva_total_tvy_min gauge",
        f"apva_total_tvy_min {m.total_tvy_min}",
        "# HELP apva_macro_tvy_usd Average True Value Yield in USD",
        "# TYPE apva_macro_tvy_usd gauge",
        f"apva_macro_tvy_usd {m.macro_tvy_usd or 0.0}",
        "# HELP apva_avg_rag_reliability Average RAG reliability coefficient",
        "# TYPE apva_avg_rag_reliability gauge",
        f"apva_avg_rag_reliability {m.avg_rag_reliability_coefficient}",
        "# HELP apva_avg_guardrail_tax_min Average guardrail friction in minutes",
        "# TYPE apva_avg_guardrail_tax_min gauge",
        f"apva_avg_guardrail_tax_min {m.avg_guardrail_tax_min}",
        "# HELP apva_shadow_event_ratio Fraction of telemetry in shadow mode",
        "# TYPE apva_shadow_event_ratio gauge",
        f"apva_shadow_event_ratio {m.shadow_event_rate}",
        "# HELP apva_hourly_rate_coverage Fraction of events with financial inputs",
        "# TYPE apva_hourly_rate_coverage gauge",
        f"apva_hourly_rate_coverage {m.hourly_rate_coverage}",
    ]
    return "\n".join(business_lines) + "\n" + RuntimeMetrics.render_prometheus()


@router.get("/insights", response_model=list[dict[str, Any]])
async def get_agentic_insights(
    session: AsyncSession = Depends(get_session),
    tenant_context: dict = Depends(get_tenant_context),
) -> list[dict[str, Any]]:
    """Return explainable, data-derived optimization recommendations."""
    m = await compute_macro_tvy_metrics(session, tenant_context["tenant_id"])
    confidence = min(1.0, m.telemetry_count / 100.0)
    hourly_rate = m.avg_hourly_rate_usd or 0.0
    insights: list[dict[str, Any]] = []

    if m.telemetry_count and m.avg_guardrail_tax_min > 1.0:
        avoidable_minutes = m.avg_guardrail_tax_min - 1.0
        savings = (avoidable_minutes / 60.0) * hourly_rate * 10_000
        insights.append(
            {
                "severity": "high",
                "metric": "Guardrail Tax Latency",
                "observation": (
                    f"Mean guardrail friction is {m.avg_guardrail_tax_min:.2f}m, "
                    "above the 1.00m operating target."
                ),
                "prescription": (
                    "Profile policy stages, cache deterministic decisions, and move redaction "
                    "closer to ingestion."
                ),
                "estimated_savings_usd_per_10k": round(savings, 2),
                "sample_size": m.telemetry_count,
                "confidence": round(confidence, 2),
            }
        )

    if m.evaluation_count and m.avg_rag_reliability_coefficient < 0.8:
        recoverable_minutes = (
            m.avg_gross_time_saved_min * (0.8 - m.avg_rag_reliability_coefficient)
        )
        savings = max(0.0, recoverable_minutes / 60.0 * hourly_rate * 10_000)
        insights.append(
            {
                "severity": "critical",
                "metric": "RAG Reliability Coefficient",
                "observation": (
                    f"Reliability is {m.avg_rag_reliability_coefficient:.1%}, below the 80% SLA."
                ),
                "prescription": (
                    "Review failed transcripts by corpus and model, then tune retrieval depth "
                    "against the golden set before rollout."
                ),
                "estimated_savings_usd_per_10k": round(savings, 2),
                "sample_size": m.evaluation_count,
                "confidence": round(min(1.0, m.evaluation_count / 50.0), 2),
            }
        )

    if m.telemetry_count and m.hourly_rate_coverage < 0.8:
        insights.append(
            {
                "severity": "high",
                "metric": "Financial Data Coverage",
                "observation": (
                    f"Only {m.hourly_rate_coverage:.1%} of telemetry includes an hourly rate."
                ),
                "prescription": (
                    "Set hourly_rate_usd in SDK defaults so value and savings estimates are complete."
                ),
                "estimated_savings_usd_per_10k": 0.0,
                "sample_size": m.telemetry_count,
                "confidence": round(confidence, 2),
            }
        )

    if not insights:
        insights.append(
            {
                "severity": "info",
                "metric": "System Optimization",
                "observation": (
                    "Observed value, reliability, guardrail, and data-coverage metrics are within "
                    "configured operating targets."
                ),
                "prescription": "Maintain the current configuration and monitor trend changes.",
                "estimated_savings_usd_per_10k": 0.0,
                "sample_size": m.telemetry_count,
                "confidence": round(confidence, 2),
            }
        )
    return insights


@router.get("/benchmarks", response_model=dict[str, Any])
async def get_reference_benchmarks(
    session: AsyncSession = Depends(get_session),
    tenant_context: dict = Depends(get_tenant_context),
) -> dict[str, Any]:
    """Compare observed tenant values with explicit reference thresholds."""
    m = await compute_macro_tvy_metrics(session, tenant_context["tenant_id"])
    return {
        "benchmark_type": "reference_thresholds",
        "global_percentiles": {
            "rag_reliability": {
                "your_value": round(m.avg_rag_reliability_coefficient, 4),
                "your_percentile": min(99, round(m.avg_rag_reliability_coefficient * 100)),
                "p50": 0.82,
                "p90": 0.95,
                "p99": 0.98,
                "message": "Reference targets, not claims derived from cross-tenant customer data.",
            },
            "guardrail_tax_ms": {
                "your_value": round(m.avg_guardrail_tax_min * 60_000.0, 2),
                "your_percentile": max(1, min(99, round(100 - m.avg_guardrail_tax_min * 25))),
                "p50": 1500.0,
                "p90": 400.0,
                "p99": 120.0,
                "message": "Reference targets, normalized against observed tenant guardrail time.",
            },
        },
    }


@router.get("/timeseries", response_model=list[dict[str, Any]])
async def get_timeseries_metrics(
    days: int = Query(default=5, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
    tenant_context: dict = Depends(get_tenant_context),
) -> list[dict[str, Any]]:
    """Return observed daily trends without synthetic fallback data."""
    return await compute_tvy_timeseries(session, tenant_context["tenant_id"], days)
