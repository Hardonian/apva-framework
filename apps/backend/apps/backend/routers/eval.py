"""Async evaluation API routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.database import get_session
from apps.backend.dependencies import get_tenant_context
from apps.backend.models import EvaluationJob
from apps.backend.schemas import EvalTriggerRequest, EvalTriggerResponse
from apps.backend.services.streaming import EventStreamer
from apps.backend.worker import evaluate_rag_transcript

router = APIRouter(prefix="/eval", tags=["eval"])


@router.post(
    "/async-trigger",
    response_model=EvalTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_evaluation(
    payload: EvalTriggerRequest,
    session: AsyncSession = Depends(get_session),
    tenant_context: dict = Depends(get_tenant_context),
) -> EvalTriggerResponse:
    """Ingest a new evaluation job and queue it for async processing.

    Args:
        payload: The evaluation job inputs.
        session: Async database session.
        tenant_context: Resolved multi-tenant organization context.

    Returns:
        EvalTriggerResponse: Acknowledged job ID.
    """
    job_payload = {
        "transcript_id": payload.transcript_id,
        "query": payload.query,
        "context": payload.context,
        "answer": payload.answer,
        "expected_answer": payload.expected_answer,
    }
    
    job = await EventStreamer.publish_eval(
        session=session,
        tenant_id=tenant_context["tenant_id"],
        payload=job_payload
    )

    task = evaluate_rag_transcript.delay(
        {
            "job_id": job.id,
            "query": job.query,
            "context": job.context,
            "answer": job.answer,
            "expected_answer": job.expected_answer,
        }
    )

    return EvalTriggerResponse(
        job_id=job.id,
        status="pending",
        celery_task_id=task.id,
    )


@router.get("/{job_id}", response_model=dict, tags=["eval"])
async def get_eval_job(
    job_id: int,
    session: AsyncSession = Depends(get_session),
    tenant_context: dict = Depends(get_tenant_context),
) -> EvaluationJob:
    """Return a persisted evaluation job by ID.

    Args:
        job_id: Evaluation job ID.
        session: Async database session.
        tenant_context: Resolved multi-tenant organization context.

    Returns:
        dict: Job fields serialized for JSON response.
    """
    job = await session.get(EvaluationJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Evaluation job not found")
    return {
        "id": job.id,
        "transcript_id": job.transcript_id,
        "status": job.status,
        "exact_span_recall": job.exact_span_recall,
        "llm_faithfulness_score": job.llm_faithfulness_score,
        "precision_score": job.precision_score,
        "rag_reliability_coefficient": job.rag_reliability_coefficient,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
