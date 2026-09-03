"""Pydantic request and response schemas for the APVA backend."""

from __future__ import annotations

from datetime import datetime
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class TelemetryIngestRequest(BaseModel):
    """Request payload accepted from the APVA SDK.

    Attributes:
        app_name: Client application identifier.
        session_id: Client session identifier.
        run_id: Client run identifier.
        human_baseline_time: Human baseline time in minutes.
        ai_augmented_time: AI-augmented time in minutes.
        guardrail_latency_tax: Guardrail latency tax in minutes.
        session_iterations: Number of session iterations.
        hourly_rate_usd: Optional hourly rate for practitioner.
        is_shadow: Shadow mode evaluation flag.
        metadata: Optional structured metadata.
    """

    model_config = ConfigDict(extra="forbid")

    app_name: str = Field(..., min_length=1, max_length=255)
    session_id: str = Field(..., min_length=1, max_length=255)
    run_id: str = Field(..., min_length=1, max_length=255)
    human_baseline_time: float = Field(..., ge=0.0)
    ai_augmented_time: float = Field(..., ge=0.0)
    guardrail_latency_tax: float = Field(..., ge=0.0)
    session_iterations: int = Field(default=1, ge=0)
    hourly_rate_usd: float | None = Field(default=None, ge=0.0)
    is_shadow: bool = Field(default=False)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TelemetryIngestResponse(BaseModel):
    """Response returned after telemetry ingestion."""

    event_id: int
    accepted: bool = True


class BatchTelemetryIngestRequest(BaseModel):
    """Batch ingestion request containing up to 100 events."""

    events: list[TelemetryIngestRequest] = Field(..., min_length=1, max_length=100)


class BatchTelemetryIngestResponse(BaseModel):
    """Response for batch telemetry ingestion."""

    accepted_count: int
    event_ids: list[int]


class EvalTriggerRequest(BaseModel):
    """Request to enqueue an async RAG evaluation job."""

    model_config = ConfigDict(extra="forbid")

    transcript_id: str = Field(..., min_length=1, max_length=255)
    query: str = Field(..., min_length=1, max_length=65536)
    context: str = Field(..., min_length=1, max_length=65536)
    answer: str = Field(..., min_length=1, max_length=65536)
    expected_answer: str = Field(..., min_length=1, max_length=65536)


class EvalTriggerResponse(BaseModel):
    """Response returned when an async evaluation is queued."""

    job_id: int
    status: str
    celery_task_id: str


class BatchEvalTriggerRequest(BaseModel):
    """Request to enqueue multiple evaluation jobs."""

    jobs: list[EvalTriggerRequest] = Field(..., min_length=1, max_length=50)


class BatchEvalTriggerResponse(BaseModel):
    """Response for batch evaluation submission."""

    submitted_count: int
    job_ids: list[int]


class TvyMetricResponse(BaseModel):
    """Macro TVY dashboard response."""

    telemetry_count: int
    evaluation_count: int
    avg_gross_time_saved_min: float
    avg_guardrail_tax_min: float
    avg_rag_reliability_coefficient: float
    macro_tvy_min: float
    avg_true_value_yield_usd: float | None = None
    is_net_positive: bool


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    database: str
    redis: str
    celery_broker: str


class EvaluationJobRead(BaseModel):
    """Persisted evaluation job read model."""

    id: int
    transcript_id: str
    status: str
    exact_span_recall: float | None = None
    llm_faithfulness_score: float | None = None
    precision_score: float | None = None
    rag_reliability_coefficient: float | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    completed_at: datetime | None = None


class PaginatedEvaluationJobs(BaseModel):
    """Paginated list of evaluation jobs."""

    items: list[EvaluationJobRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class BillingUsageResponse(BaseModel):
    """Current tenant billing usage."""

    tenant_id: int
    usage: dict[str, int]


class BillingEstimateResponse(BaseModel):
    """Estimated bill breakdown for tenant."""

    tenant_id: int
    line_items: dict[str, Any]
    total_estimated_usd: float
