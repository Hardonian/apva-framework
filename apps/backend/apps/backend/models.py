"""SQLAlchemy models for APVA backend persistence."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all APVA ORM models."""


class TelemetryEvent(Base):
    """Persistent SDK telemetry event.

    Attributes:
        id: Primary key.
        app_name: Client application identifier.
        session_id: Client session identifier.
        run_id: Client run identifier.
        human_baseline_time: Human baseline time in minutes.
        ai_augmented_time: AI-augmented time in minutes.
        guardrail_latency_tax: Guardrail latency tax in minutes.
        session_iterations: Session iteration count.
        metadata: Optional structured metadata from the SDK.
        created_at: UTC creation timestamp.
    """

    __tablename__ = "telemetry_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    app_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    human_baseline_time: Mapped[float] = mapped_column(Float, nullable=False)
    ai_augmented_time: Mapped[float] = mapped_column(Float, nullable=False)
    guardrail_latency_tax: Mapped[float] = mapped_column(Float, nullable=False)
    session_iterations: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )


class EvaluationJob(Base):
    """Async RAG evaluation job and score record.

    Attributes:
        id: Primary key.
        transcript_id: Client-provided transcript identifier.
        query: User query.
        context: Retrieved context.
        answer: RAG system answer.
        expected_answer: Golden expected answer.
        status: pending, running, completed, or failed.
        exact_span_recall: Deterministic span recall score.
        llm_faithfulness_score: LLM-as-judge faithfulness score.
        precision_score: LLM-as-judge precision score.
        rag_reliability_coefficient: Blended RAG reliability coefficient.
        error_message: Failure message when status is failed.
        created_at: UTC creation timestamp.
        updated_at: UTC update timestamp.
        completed_at: UTC completion timestamp when available.
    """

    __tablename__ = "evaluation_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transcript_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    exact_span_recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    llm_faithfulness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    precision_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rag_reliability_coefficient: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
