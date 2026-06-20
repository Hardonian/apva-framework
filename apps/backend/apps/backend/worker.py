"""Celery worker for asynchronous APVA evaluations."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

try:  # Celery is optional for local tests and lightweight installs.
    from celery import Celery  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - exercised when celery extra is absent
    class Celery:  # type: ignore[no-redef]
        """Tiny local fallback that preserves the @task decorator contract."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs

        def task(self, *args: Any, **kwargs: Any):
            def decorator(fn):
                fn.delay = fn  # type: ignore[attr-defined]
                return fn
            return decorator

from apps.backend.config import settings
from apps.backend.database import AsyncSessionLocal
from apps.backend.models import EvaluationJob
from apps.backend.schemas import EvalTriggerRequest
from apps.backend.services.eval import run_local_or_target_score

celery_app = Celery(
    "apva",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["apps.backend.worker"],
)


@celery_app.task(name="apva.evaluate_rag_transcript")
def evaluate_rag_transcript(payload: dict[str, Any]) -> dict[str, Any]:
    """Run async RAG evaluation without blocking FastAPI request threads.

    Args:
        payload: Serialized evaluation request payload.

    Returns:
        dict[str, Any]: Completed evaluation scores and job ID.
    """
    return asyncio.run(_evaluate_rag_transcript_async(payload))


async def _evaluate_rag_transcript_async(payload: dict[str, Any]) -> dict[str, Any]:
    """Persist and score an evaluation job asynchronously.

    Args:
        payload: Serialized evaluation request payload.

    Returns:
        dict[str, Any]: Completed evaluation scores and job ID.
    """
    request = EvalTriggerRequest.model_validate(payload)
    async with AsyncSessionLocal() as session:
        job = await session.get(EvaluationJob, payload["job_id"])
        if job is None:
            raise ValueError(f"Evaluation job not found: {payload['job_id']}")
        job.status = "running"
        await session.commit()

    try:
        scores = await run_local_or_target_score(request, settings.target_app_url)
        async with AsyncSessionLocal() as session:
            job = await session.get(EvaluationJob, payload["job_id"])
            if job is None:
                raise ValueError(f"Evaluation job not found: {payload['job_id']}")
            job.status = "completed"
            job.exact_span_recall = float(scores["exact_span_recall"])
            job.llm_faithfulness_score = float(scores["llm_faithfulness_score"])
            job.precision_score = float(scores["precision_score"])
            job.rag_reliability_coefficient = float(
                scores["rag_reliability_coefficient"]
            )
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()
        return {
            "job_id": payload["job_id"],
            "status": "completed",
            **scores,
        }
    except Exception as exc:  # pragma: no cover - exercised through worker logs
        async with AsyncSessionLocal() as session:
            job = await session.get(EvaluationJob, payload["job_id"])
            if job is not None:
                job.status = "failed"
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
                await session.commit()
        raise
