"""Telemetry ingestion API routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_tenant_context
from ..models import TelemetryEvent
from ..schemas import TelemetryIngestRequest, TelemetryIngestResponse
from ..services.streaming import EventStreamer

router = APIRouter(prefix="/telemetry", tags=["telemetry"])



@router.post(
    "/ingest",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_telemetry(
    payload: TelemetryIngestRequest,
    session: AsyncSession = Depends(get_session),
    tenant_context: dict = Depends(get_tenant_context),
) -> TelemetryIngestResponse:
    """Persist one SDK telemetry payload.

    Args:
        payload: Validated telemetry payload.
        session: Async database session.
        tenant_context: Resolved multi-tenant organization context.

    Returns:
        TelemetryIngestResponse: Persisted event ID and acceptance flag.
    """
    event_payload = {
        "app_name": payload.app_name,
        "session_id": payload.session_id,
        "run_id": payload.run_id,
        "human_baseline_time": payload.human_baseline_time,
        "ai_augmented_time": payload.ai_augmented_time,
        "guardrail_latency_tax": payload.guardrail_latency_tax,
        "session_iterations": payload.session_iterations,
        "hourly_rate_usd": payload.hourly_rate_usd,
        "is_shadow": payload.is_shadow,
        "event_metadata": payload.metadata,
        "created_at": datetime.now(timezone.utc),
    }
    
    event = await EventStreamer.publish_telemetry(
        session=session,
        tenant_id=tenant_context["tenant_id"],
        payload=event_payload
    )
    
    return TelemetryIngestResponse(event_id=event.id)
