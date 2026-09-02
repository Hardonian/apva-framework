"""Async evaluation API routes."""

from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_tenant_context
from ..models import EvaluationJob
from ..schemas import (
    BatchEvalTriggerRequest,
    BatchEvalTriggerResponse,
    EvalTriggerRequest,
    EvalTriggerResponse,
    EvaluationJobRead,
    PaginatedEvaluationJobs,
)
from ..services.streaming import EventStreamer
from ..worker import evaluate_rag_transcript

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
    """Ingest a new evaluation job and queue it for async processing."""
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
        payload=job_payload,
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


@router.post(
    "/batch-trigger",
    response_model=BatchEvalTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def batch_trigger_evaluation(
    payload: BatchEvalTriggerRequest,
    session: AsyncSession = Depends(get_session),
    tenant_context: dict = Depends(get_tenant_context),
) -> BatchEvalTriggerResponse:
    """Submit multiple evaluation jobs concurrently."""
    job_ids: list[int] = []
    for req in payload.jobs:
        job_payload = {
            "transcript_id": req.transcript_id,
            "query": req.query,
            "context": req.context,
            "answer": req.answer,
            "expected_answer": req.expected_answer,
        }
        job = await EventStreamer.publish_eval(
            session=session,
            tenant_id=tenant_context["tenant_id"],
            payload=job_payload,
        )
        evaluate_rag_transcript.delay(
            {
                "job_id": job.id,
                "query": job.query,
                "context": job.context,
                "answer": job.answer,
                "expected_answer": job.expected_answer,
            }
        )
        job_ids.append(job.id)

    return BatchEvalTriggerResponse(
        submitted_count=len(job_ids),
        job_ids=job_ids,
    )


@router.get("", response_model=PaginatedEvaluationJobs)
async def list_eval_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
    tenant_context: dict = Depends(get_tenant_context),
) -> PaginatedEvaluationJobs:
    """List evaluation jobs for the tenant with pagination and optional status filter."""
    tenant_id = tenant_context["tenant_id"]

    query = select(EvaluationJob).where(EvaluationJob.tenant_id == tenant_id)
    count_query = select(func.count(EvaluationJob.id)).where(EvaluationJob.tenant_id == tenant_id)

    if status_filter:
        query = query.where(EvaluationJob.status == status_filter)
        count_query = count_query.where(EvaluationJob.status == status_filter)

    total_res = await session.execute(count_query)
    total = total_res.scalar() or 0

    query = query.order_by(EvaluationJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    jobs = result.scalars().all()

    items = [
        EvaluationJobRead(
            id=j.id,
            transcript_id=j.transcript_id,
            status=j.status,
            exact_span_recall=j.exact_span_recall,
            llm_faithfulness_score=j.llm_faithfulness_score,
            precision_score=j.precision_score,
            rag_reliability_coefficient=j.rag_reliability_coefficient,
            error_message=j.error_message,
            created_at=j.created_at,
            updated_at=j.updated_at,
            completed_at=j.completed_at,
        )
        for j in jobs
    ]

    total_pages = max(1, math.ceil(total / page_size))
    return PaginatedEvaluationJobs(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{job_id}", response_model=dict[str, Any])
async def get_eval_job(
    job_id: int,
    session: AsyncSession = Depends(get_session),
    tenant_context: dict = Depends(get_tenant_context),
) -> dict[str, Any]:
    """Return a persisted evaluation job by ID."""
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
