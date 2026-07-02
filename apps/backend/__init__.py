"""APVA Framework - backend package."""

# Re-export key modules for backward compatibility
from .apps.backend.config import settings
from .apps.backend.database import engine, AsyncSessionLocal, async_session_maker
from .apps.backend.models import Base, Tenant, EvaluationJob, TelemetryEvent, UsageRecord
from .apps.backend.schemas import (
    HealthResponse,
    EvalTriggerRequest,
    EvalTriggerResponse,
    TelemetryIngestRequest,
    TelemetryIngestResponse,
)
from .apps.backend.routers import health, metrics, telemetry, eval as eval_router, auth

__all__ = [
    "settings",
    "engine",
    "AsyncSessionLocal",
    "async_session_maker",
    "Base",
    "Tenant",
    "EvaluationJob",
    "TelemetryEvent",
    "UsageRecord",
    "HealthResponse",
    "EvalTriggerRequest",
    "EvalTriggerResponse",
    "TelemetryIngestRequest",
    "TelemetryIngestResponse",
]