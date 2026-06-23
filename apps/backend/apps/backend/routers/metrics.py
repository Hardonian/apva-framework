"""Macro TVY metrics API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.config import settings
from apps.backend.database import get_session
from apps.backend.dependencies import get_api_key
from apps.backend.models import EvaluationJob, TelemetryEvent
from apps.backend.schemas import TvyMetricResponse

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/tvy", response_model=TvyMetricResponse)
async def get_macro_tvy(
    session: AsyncSession = Depends(get_session),
    api_key: str = Depends(get_api_key),
) -> TvyMetricResponse:
    """Calculate macro True Value Yield for the dashboard.

    Args:
        session: Async database session.

    Returns:
        TvyMetricResponse: Aggregated TVY metrics.
    """
    telemetry_count, avg_human, avg_ai, avg_guardrail = await session.execute(
        select(
            func.count(TelemetryEvent.id),
            func.avg(TelemetryEvent.human_baseline_time),
            func.avg(TelemetryEvent.ai_augmented_time),
            func.avg(TelemetryEvent.guardrail_latency_tax),
        )
    ).one()
    evaluation_count, avg_reliability = await session.execute(
        select(
            func.count(EvaluationJob.id),
            func.avg(EvaluationJob.rag_reliability_coefficient),
        ).where(EvaluationJob.status == "completed")
    ).one()

    telemetry_count_int = int(telemetry_count or 0)
    evaluation_count_int = int(evaluation_count or 0)
    avg_human_float = float(avg_human or 0.0)
    avg_ai_float = float(avg_ai or 0.0)
    avg_guardrail_float = float(avg_guardrail or 0.0)
    avg_reliability_float = float(
        avg_reliability if avg_reliability is not None else settings.default_rag_reliability
    )
    avg_gross_time_saved = avg_human_float - avg_ai_float
    macro_tvy = (avg_gross_time_saved * avg_reliability_float) - avg_guardrail_float
    return TvyMetricResponse(
        telemetry_count=telemetry_count_int,
        evaluation_count=evaluation_count_int,
        avg_gross_time_saved_min=avg_gross_time_saved,
        avg_guardrail_tax_min=avg_guardrail_float,
        avg_rag_reliability_coefficient=avg_reliability_float,
        macro_tvy_min=macro_tvy,
        is_net_positive=macro_tvy > 0.0,
    )
