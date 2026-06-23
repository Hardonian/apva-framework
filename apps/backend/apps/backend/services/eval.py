"""Evaluation scoring helpers shared by API routes and Celery workers."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

from apps.backend.schemas import EvalTriggerRequest

SPAN_RECALL_WEIGHT = 0.60
FAITHFULNESS_WEIGHT = 0.40


@dataclass(frozen=True)
class RagScoreResult:
    """Structured RAG evaluation result.

    Attributes:
        exact_span_recall: Deterministic exact span recall score.
        llm_faithfulness_score: Mock LLM-as-judge faithfulness score.
        precision_score: Mock precision score.
        rag_reliability_coefficient: Blended RAG reliability coefficient.
    """

    exact_span_recall: float
    llm_faithfulness_score: float
    precision_score: float
    rag_reliability_coefficient: float


def tokenize(text: str) -> list[str]:
    """Tokenize text into lower-case word spans.

    Args:
        text: Input text.

    Returns:
        list[str]: Normalized word tokens.
    """
    return re.findall(r"[a-zA-Z0-9]+(?:[-'][a-zA-Z0-9]+)?", text.lower())


def exact_span_recall(answer: str, expected_answer: str) -> float:
    """Compute deterministic exact span recall.

    The metric counts exact token spans from the expected answer that appear in
    the generated answer.

    Args:
        answer: Generated answer text.
        expected_answer: Golden expected answer text.

    Returns:
        float: Fraction of expected spans found exactly in the answer.
    """
    expected_tokens = tokenize(expected_answer)
    answer_tokens = tokenize(answer)
    if not expected_tokens:
        return 1.0 if not answer_tokens else 0.0

    found = 0
    for token in expected_tokens:
        if token in answer_tokens:
            found += 1
    return found / len(expected_tokens)


def mock_llm_judge_score(answer: str, expected_answer: str) -> float:
    """Return a deterministic mock LLM-as-judge faithfulness score.

    This function simulates the async worker call to a target judge service. In
    production it is replaced by a real judge model, but the API contract stays
    the same.

    Args:
        answer: Generated answer text.
        expected_answer: Golden expected answer text.

    Returns:
        float: Faithfulness score in ``[0, 1]``.
    """
    recall = exact_span_recall(answer, expected_answer)
    expected_tokens = set(tokenize(expected_answer))
    answer_tokens = set(tokenize(answer))
    if not expected_tokens:
        precision = 1.0 if not answer_tokens else 0.0
    else:
        precision = len(expected_tokens & answer_tokens) / len(answer_tokens or expected_tokens)
    return min(1.0, max(0.0, 0.75 * recall + 0.25 * precision))


def mock_precision_score(answer: str, expected_answer: str) -> float:
    """Return a deterministic mock precision score.

    Args:
        answer: Generated answer text.
        expected_answer: Golden expected answer text.

    Returns:
        float: Precision score in ``[0, 1]``.
    """
    expected_tokens = set(tokenize(expected_answer))
    answer_tokens = set(tokenize(answer))
    if not expected_tokens:
        return 1.0 if not answer_tokens else 0.0
    if not answer_tokens:
        return 0.0
    return len(expected_tokens & answer_tokens) / len(answer_tokens)


def compute_rag_scores(answer: str, expected_answer: str) -> RagScoreResult:
    """Compute all RAG scoring metrics for a transcript.

    Args:
        answer: Generated answer text.
        expected_answer: Golden expected answer text.

    Returns:
        RagScoreResult: Deterministic exact span recall plus mock judge scores.
    """
    recall = exact_span_recall(answer, expected_answer)
    faithfulness = mock_llm_judge_score(answer, expected_answer)
    precision = mock_precision_score(answer, expected_answer)
    reliability = SPAN_RECALL_WEIGHT * recall + FAITHFULNESS_WEIGHT * faithfulness
    return RagScoreResult(
        exact_span_recall=recall,
        llm_faithfulness_score=faithfulness,
        precision_score=precision,
        rag_reliability_coefficient=reliability,
    )


_http_client: httpx.AsyncClient | None = None

def get_http_client() -> httpx.AsyncClient:
    """Return a global singleton HTTPX client for connection pooling."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


async def score_with_mock_target(
    request: EvalTriggerRequest, target_app_url: str
) -> dict[str, Any]:
    """Score a transcript using the mock target application.

    Args:
        request: Evaluation trigger request.
        target_app_url: Base URL of the mock target application.

    Returns:
        dict[str, Any]: Score payload returned by the target app.
    """
    payload = {
        "query": request.query,
        "context": request.context,
        "answer": request.answer,
        "expected_answer": request.expected_answer,
    }
    url = f"{target_app_url.rstrip('/')}/score-faithfulness"
    
    client = get_http_client()
    response = await client.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def compute_tvy_from_scores(
    human_baseline_time: float,
    ai_augmented_time: float,
    guardrail_latency_tax: float,
    rag_reliability_coefficient: float,
) -> float:
    """Compute TVY from telemetry and RAG score inputs.

    Args:
        human_baseline_time: Human baseline time in minutes.
        ai_augmented_time: AI-augmented time in minutes.
        guardrail_latency_tax: Guardrail latency tax in minutes.
        rag_reliability_coefficient: RAG reliability coefficient.

    Returns:
        float: TVY in minutes.
    """
    gross_time_saved = human_baseline_time - ai_augmented_time
    return (gross_time_saved * rag_reliability_coefficient) - guardrail_latency_tax


async def run_local_or_target_score(
    request: EvalTriggerRequest, target_app_url: str
) -> dict[str, Any]:
    """Run target scoring with local fallback.

    Args:
        request: Evaluation trigger request.
        target_app_url: Mock target application base URL.

    Returns:
        dict[str, Any]: Score payload.
    """
    try:
        return await score_with_mock_target(request, target_app_url)
    except httpx.HTTPError:
        scores = compute_rag_scores(request.answer, request.expected_answer)
        return {
            "exact_span_recall": scores.exact_span_recall,
            "llm_faithfulness_score": scores.llm_faithfulness_score,
            "precision_score": scores.precision_score,
            "rag_reliability_coefficient": scores.rag_reliability_coefficient,
        }


async def main() -> None:
    """CLI smoke helper for local scoring.

    This function is intentionally small and only exists to make the module
    executable for smoke checks.
    """
    request = EvalTriggerRequest(
        transcript_id="smoke",
        query="What is APVA?",
        context="APVA measures AI productivity and value.",
        answer="APVA measures AI productivity and value.",
        expected_answer="APVA measures AI productivity and value.",
    )
    result = await run_local_or_target_score(request, "http://localhost:8080")
    logger = logging.getLogger(__name__)
    logger.info("Local scoring result: %s", result)


if __name__ == "__main__":
    asyncio.run(main())
