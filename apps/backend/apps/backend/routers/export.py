"""Data warehouse and analytical export endpoints for telemetry and evaluations."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_tenant
from ..models import EvaluationJob, TelemetryEvent, Tenant

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/telemetry")
async def export_telemetry(
    format: str = Query(
        default="json", pattern="^(json|csv)$", description="Export format: json or csv"
    ),
    limit: int = Query(default=1000, ge=1, le=10000, description="Maximum records to export"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Export telemetry events for ingestion into Snowflake, BigQuery, or Databricks."""
    stmt = (
        select(TelemetryEvent)
        .where(TelemetryEvent.tenant_id == current_tenant.id)
        .order_by(TelemetryEvent.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    events = result.scalars().all()

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "app_name",
                "session_id",
                "run_id",
                "human_baseline_time",
                "ai_augmented_time",
                "guardrail_latency_tax",
                "session_iterations",
                "hourly_rate_usd",
                "is_shadow",
                "created_at",
            ]
        )
        for ev in events:
            writer.writerow(
                [
                    ev.id,
                    ev.app_name,
                    ev.session_id,
                    ev.run_id,
                    ev.human_baseline_time,
                    ev.ai_augmented_time,
                    ev.guardrail_latency_tax,
                    ev.session_iterations,
                    ev.hourly_rate_usd,
                    bool(ev.is_shadow),
                    ev.created_at.isoformat() if ev.created_at else "",
                ]
            )
        csv_data = output.getvalue()
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="apva_telemetry.csv"'},
        )

    # JSON export
    data = [
        {
            "id": ev.id,
            "app_name": ev.app_name,
            "session_id": ev.session_id,
            "run_id": ev.run_id,
            "human_baseline_time": ev.human_baseline_time,
            "ai_augmented_time": ev.ai_augmented_time,
            "guardrail_latency_tax": ev.guardrail_latency_tax,
            "session_iterations": ev.session_iterations,
            "hourly_rate_usd": ev.hourly_rate_usd,
            "is_shadow": bool(ev.is_shadow),
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
            "metadata": ev.event_metadata,
        }
        for ev in events
    ]
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="apva_telemetry.json"'},
    )


@router.get("/evaluations")
async def export_evaluations(
    format: str = Query(
        default="json", pattern="^(json|csv)$", description="Export format: json or csv"
    ),
    limit: int = Query(default=1000, ge=1, le=10000, description="Maximum records to export"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Export RAG evaluation scores and jobs for compliance and auditing."""
    stmt = (
        select(EvaluationJob)
        .where(EvaluationJob.tenant_id == current_tenant.id)
        .order_by(EvaluationJob.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    jobs = result.scalars().all()

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "transcript_id",
                "status",
                "exact_span_recall",
                "llm_faithfulness_score",
                "precision_score",
                "rag_reliability_coefficient",
                "created_at",
            ]
        )
        for job in jobs:
            writer.writerow(
                [
                    job.id,
                    job.transcript_id,
                    job.status,
                    job.exact_span_recall,
                    job.llm_faithfulness_score,
                    job.precision_score,
                    job.rag_reliability_coefficient,
                    job.created_at.isoformat() if job.created_at else "",
                ]
            )
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="apva_evaluations.csv"'},
        )

    # JSON export
    data = [
        {
            "id": job.id,
            "transcript_id": job.transcript_id,
            "query": job.query,
            "answer": job.answer,
            "status": job.status,
            "exact_span_recall": job.exact_span_recall,
            "llm_faithfulness_score": job.llm_faithfulness_score,
            "precision_score": job.precision_score,
            "rag_reliability_coefficient": job.rag_reliability_coefficient,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }
        for job in jobs
    ]
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="apva_evaluations.json"'},
    )
