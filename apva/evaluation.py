"""Canonical evaluation orchestration for the APVA framework.

This module provides the ``EvaluationResult`` / ``EvaluationSummary``
dataclasses and the ``evaluate_examples`` / ``summarize_evaluation``
functions shared by the CLI and backend services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from apva.datasets import GoldenExample
from apva.scoring import (
    bleu_score,
    exact_span_recall,
    f1_score,
    rouge_l_score,
    token_precision,
)


@dataclass(frozen=True)
class EvaluationResult:
    """Scores for a single golden example.

    Attributes:
        index: Position of the example in the dataset.
        query: The user's question.
        answer: The answer that was evaluated (generated or pre-filled).
        expected_answer: The ground-truth reference answer.
        exact_span_recall: Recall of expected tokens in the answer.
        token_precision: Precision of answer tokens against expected.
        f1: Harmonic mean of recall and precision.
        rouge_l: ROUGE-L F-measure (longest common subsequence).
        bleu: Simplified BLEU score (up to 4-grams).
    """

    index: int
    query: str
    answer: str
    expected_answer: str
    exact_span_recall: float
    token_precision: float
    f1: float
    rouge_l: float
    bleu: float


@dataclass
class EvaluationSummary:
    """Aggregate statistics across all evaluated examples.

    Attributes:
        count: Number of examples evaluated.
        avg_exact_span_recall: Mean exact-span recall.
        avg_token_precision: Mean token precision.
        avg_f1: Mean F1 score.
        avg_rouge_l: Mean ROUGE-L score.
        avg_bleu: Mean BLEU score.
        threshold: Pass/fail threshold (applied to avg recall by default).
        passed: Whether the evaluation met the threshold.
        results: Per-example result details.
    """

    count: int
    avg_exact_span_recall: float
    avg_token_precision: float
    avg_f1: float
    avg_rouge_l: float
    avg_bleu: float
    threshold: float
    passed: bool
    results: list[EvaluationResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the summary to a plain dict for JSON output."""
        return {
            "count": self.count,
            "average_exact_span_recall": round(self.avg_exact_span_recall, 4),
            "average_token_precision": round(self.avg_token_precision, 4),
            "average_f1": round(self.avg_f1, 4),
            "average_rouge_l": round(self.avg_rouge_l, 4),
            "average_bleu": round(self.avg_bleu, 4),
            "threshold": self.threshold,
            "passed": self.passed,
            "results": [
                {
                    "index": r.index,
                    "query": r.query,
                    "answer": r.answer,
                    "expected_answer": r.expected_answer,
                    "exact_span_recall": round(r.exact_span_recall, 4),
                    "token_precision": round(r.token_precision, 4),
                    "f1": round(r.f1, 4),
                    "rouge_l": round(r.rouge_l, 4),
                    "bleu": round(r.bleu, 4),
                }
                for r in self.results
            ],
        }


async def fetch_target_answer(
    target_url: str,
    example: GoldenExample,
    timeout: float = 15.0,
) -> str:
    """Fetch a generated answer from a live target RAG endpoint.

    Args:
        target_url: Base URL of the target service (e.g. ``http://localhost:8080``).
        example: The golden example to query.
        timeout: HTTP timeout in seconds.

    Returns:
        str: The generated answer text.

    Raises:
        httpx.HTTPError: On network or HTTP-level failures.
    """
    import httpx

    payload = {"query": example.query, "context": example.context}
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{target_url.rstrip('/')}/evaluate", json=payload)
        response.raise_for_status()
        data = response.json()
    if isinstance(data, dict) and "answer" in data:
        return str(data["answer"])
    if isinstance(data, str):
        return data
    return str(data)


async def evaluate_examples(
    examples: list[GoldenExample],
    target_url: str | None = None,
) -> list[EvaluationResult]:
    """Score every example, optionally fetching answers from a live target.

    If *target_url* is provided, the answer from each example is replaced
    by the response from the target service's ``/evaluate`` endpoint.

    Args:
        examples: Golden dataset examples.
        target_url: Optional target RAG service URL.

    Returns:
        list[EvaluationResult]: Per-example scores.
    """
    results: list[EvaluationResult] = []
    for index, example in enumerate(examples):
        answer = example.answer
        if target_url:
            answer = await fetch_target_answer(target_url, example)

        results.append(
            EvaluationResult(
                index=index,
                query=example.query,
                answer=answer,
                expected_answer=example.expected_answer,
                exact_span_recall=exact_span_recall(answer, example.expected_answer),
                token_precision=token_precision(answer, example.expected_answer),
                f1=f1_score(answer, example.expected_answer),
                rouge_l=rouge_l_score(answer, example.expected_answer),
                bleu=bleu_score(answer, example.expected_answer),
            )
        )
    return results


def summarize_evaluation(
    results: list[EvaluationResult],
    threshold: float = 0.85,
) -> EvaluationSummary:
    """Aggregate per-example results into a summary with pass/fail.

    The *threshold* is compared against the average exact-span recall.

    Args:
        results: Per-example evaluation results.
        threshold: Minimum average recall to pass.

    Returns:
        EvaluationSummary: Aggregated evaluation summary.
    """
    if not results:
        return EvaluationSummary(
            count=0,
            avg_exact_span_recall=0.0,
            avg_token_precision=0.0,
            avg_f1=0.0,
            avg_rouge_l=0.0,
            avg_bleu=0.0,
            threshold=threshold,
            passed=False,
            results=[],
        )

    n = len(results)
    avg_recall = sum(r.exact_span_recall for r in results) / n
    avg_prec = sum(r.token_precision for r in results) / n
    avg_f1 = sum(r.f1 for r in results) / n
    avg_rl = sum(r.rouge_l for r in results) / n
    avg_bleu = sum(r.bleu for r in results) / n

    return EvaluationSummary(
        count=n,
        avg_exact_span_recall=avg_recall,
        avg_token_precision=avg_prec,
        avg_f1=avg_f1,
        avg_rouge_l=avg_rl,
        avg_bleu=avg_bleu,
        threshold=threshold,
        passed=avg_recall >= threshold,
        results=results,
    )
