"""Pydantic request and response schemas for the APVA backend."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
        metadata: Optional structured metadata.
    """

    model_config = ConfigDict(extra="forbid")

    app_name: str = Field(..., min_length=1, max_length=255)
    session_id: str = Field(..., min_length=1, max_length=255)
    run_id: str = Field(..., min_length=1, max_length=255)
    human_baseline_time: float = Field(..., ge=0.0)
    ai_augmented_time: float = Field(..., ge=0.0)
    guardrail_latency_tax: float = Field(..., ge=0.0)
    session_iterations: int = Field(..., ge=0)
    hourly_rate_usd: float | None = Field(default=None, ge=0.0)
    is_shadow: bool = Field(default=False)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TelemetryIngestResponse(BaseModel):
    """Response returned after telemetry ingestion.

    Attributes:
        event_id: Persisted event ID.
        accepted: Whether the event was accepted.
    """

    event_id: int
    accepted: bool = True


class EvalTriggerRequest(BaseModel):
    """Request to enqueue an async RAG evaluation job.

    Attributes:
        transcript_id: Client-provided transcript identifier.
        query: User query.
        context: Retrieved context.
        answer: RAG system answer.
        expected_answer: Golden expected answer.
    """

    model_config = ConfigDict(extra="forbid")

    transcript_id: str = Field(..., min_length=1, max_length=255)
    query: str = Field(..., min_length=1, max_length=65536)
    context: str = Field(..., min_length=1, max_length=65536)
    answer: str = Field(..., min_length=1, max_length=65536)
    expected_answer: str = Field(..., min_length=1, max_length=65536)


class EvalTriggerResponse(BaseModel):
    """Response returned when an async evaluation is queued.

    Attributes:
        job_id: Persisted job ID.
        status: Current job status.
        celery_task_id: Celery task identifier.
    """

    job_id: int
    status: str
    celery_task_id: str


class TvyMetricResponse(BaseModel):
    """Macro TVY dashboard response.

    Attributes:
        telemetry_count: Number of telemetry events included.
        evaluation_count: Number of completed evaluation jobs included.
        avg_gross_time_saved_min: Average gross time saved in minutes.
        avg_guardrail_tax_min: Average guardrail tax in minutes.
        avg_rag_reliability_coefficient: Average RAG reliability coefficient.
        macro_tvy_min: Macro True Value Yield in minutes.
        is_net_positive: Whether macro TVY is positive.
    """

    telemetry_count: int
    evaluation_count: int
    avg_gross_time_saved_min: float
    avg_guardrail_tax_min: float
    avg_rag_reliability_coefficient: float
    macro_tvy_min: float
    avg_true_value_yield_usd: float | None = None
    is_net_positive: bool


class HealthResponse(BaseModel):
    """Health check response.

    Attributes:
        status: Overall health status.
        service: Service name.
        database: Database health status.
        redis: Redis health status.
        celery_broker: Celery broker health status.
    """

    status: str
    service: str
    database: str
    redis: str
    celery_broker: str


class EvaluationJobRead(BaseModel):
    """Persisted evaluation job read model.

    Attributes:
        id: Job ID.
        transcript_id: Transcript ID.
        status: Job status.
        exact_span_recall: Exact span recall score.
        llm_faithfulness_score: LLM faithfulness score.
        precision_score: Precision score.
        rag_reliability_coefficient: RAG reliability coefficient.
        created_at: Creation timestamp.
        completed_at: Completion timestamp.
    """

    id: int
    transcript_id: str
    status: str
    exact_span_recall: float | None = None
    llm_faithfulness_score: float | None = None
    precision_score: float | None = None
    rag_reliability_coefficient: float | None = None
    created_at: datetime
    completed_at: datetime | None = None
