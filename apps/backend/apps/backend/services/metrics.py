"""Metrics computation service for macro TVY and Prometheus export."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import EvaluationJob, TelemetryEvent


@dataclass(frozen=True)
class MacroTVYMetrics:
    """Aggregated TVY metrics across a tenant's historical telemetry."""

    telemetry_count: int
    evaluation_count: int
    avg_human_baseline_min: float
    avg_ai_augmented_min: float
    avg_gross_time_saved_min: float
    avg_guardrail_tax_min: float
    avg_rag_reliability_coefficient: float
    macro_tvy_min: float
    macro_tvy_usd: float | None
    is_net_positive: bool


async def compute_macro_tvy_metrics(
    session: AsyncSession,
    tenant_id: int,
) -> MacroTVYMetrics:
    """Compute aggregate macro TVY metrics for a tenant from database records.

    Args:
        session: Async SQLAlchemy database session.
        tenant_id: Tenant identifier.

    Returns:
        MacroTVYMetrics: Structured aggregate metrics.
    """
    telemetry_result = await session.execute(
        select(
            func.count(TelemetryEvent.id),
            func.avg(TelemetryEvent.human_baseline_time),
            func.avg(TelemetryEvent.ai_augmented_time),
            func.avg(TelemetryEvent.guardrail_latency_tax),
            func.avg(TelemetryEvent.hourly_rate_usd),
        ).where(TelemetryEvent.tenant_id == tenant_id)
    )
    telemetry_count, avg_human, avg_ai, avg_guardrail, avg_hourly_rate = telemetry_result.one()

    eval_result = await session.execute(
        select(
            func.count(EvaluationJob.id),
            func.avg(EvaluationJob.rag_reliability_coefficient),
        ).where(
            EvaluationJob.status == "completed",
            EvaluationJob.tenant_id == tenant_id,
        )
    )
    evaluation_count, avg_reliability = eval_result.one()

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

    return MacroTVYMetrics(
        telemetry_count=telemetry_count_int,
        evaluation_count=evaluation_count_int,
        avg_human_baseline_min=avg_human_float,
        avg_ai_augmented_min=avg_ai_float,
        avg_gross_time_saved_min=avg_gross_time_saved,
        avg_guardrail_tax_min=avg_guardrail_float,
        avg_rag_reliability_coefficient=avg_reliability_float,
        macro_tvy_min=macro_tvy,
        macro_tvy_usd=macro_tvy_usd,
        is_net_positive=macro_tvy > 0.0,
    )
