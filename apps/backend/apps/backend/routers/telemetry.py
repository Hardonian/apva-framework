"""Telemetry ingestion API routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.database import get_session
from apps.backend.models import TelemetryEvent
from apps.backend.schemas import TelemetryIngestRequest, TelemetryIngestResponse

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post(
    "/ingest",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_telemetry(
    payload: TelemetryIngestRequest,
    session: AsyncSession = Depends(get_session),
) -> TelemetryIngestResponse:
    """Persist one SDK telemetry payload.

    Args:
        payload: Validated telemetry payload.
        session: Async database session.

    Returns:
        TelemetryIngestResponse: Persisted event ID and acceptance flag.
    """
    event = TelemetryEvent(
        app_name=payload.app_name,
        session_id=payload.session_id,
        run_id=payload.run_id,
        human_baseline_time=payload.human_baseline_time,
        ai_augmented_time=payload.ai_augmented_time,
        guardrail_latency_tax=payload.guardrail_latency_tax,
        session_iterations=payload.session_iterations,
        event_metadata=payload.metadata,
        created_at=datetime.now(timezone.utc),
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return TelemetryIngestResponse(event_id=event.id)
