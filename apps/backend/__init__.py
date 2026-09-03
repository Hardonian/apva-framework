"""APVA Framework - backend package."""

# Re-export key modules for backward compatibility
from .apps.backend.config import settings
from .apps.backend.database import AsyncSessionLocal, async_session_maker, engine
from .apps.backend.models import Base, EvaluationJob, TelemetryEvent, Tenant, UsageRecord
from .apps.backend.routers import auth, health, metrics, telemetry
from .apps.backend.routers import eval as eval_router
from .apps.backend.schemas import (
    EvalTriggerRequest,
    EvalTriggerResponse,
    HealthResponse,
    TelemetryIngestRequest,
    TelemetryIngestResponse,
)

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
    "health",
    "metrics",
    "telemetry",
    "eval_router",
    "auth",
]
