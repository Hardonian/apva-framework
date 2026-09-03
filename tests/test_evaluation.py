"""Unit tests for the apva.evaluation module."""

from __future__ import annotations

import pytest

from apva.datasets import GoldenExample
from apva.evaluation import (
    EvaluationResult,
    evaluate_examples,
    summarize_evaluation,
)


@pytest.mark.asyncio
async def test_evaluate_examples_offline():
    examples = [
        GoldenExample(
            query="What is TVY?",
            context="TVY is True Value Yield.",
            answer="TVY is True Value Yield.",
            expected_answer="TVY is True Value Yield.",
        ),
        GoldenExample(
            query="What is APVA?",
            context="APVA measures AI ROI.",
            answer="Unrelated text.",
            expected_answer="APVA measures AI ROI.",
        ),
    ]

    results = await evaluate_examples(examples)
    assert len(results) == 2
    assert results[0].exact_span_recall == pytest.approx(1.0)
    assert results[0].f1 == pytest.approx(1.0)
    assert results[1].exact_span_recall < 0.5


def test_summarize_evaluation():
    results = [
        EvaluationResult(
            index=0,
            query="q1",
            answer="a1",
            expected_answer="a1",
            exact_span_recall=1.0,
            token_precision=1.0,
            f1=1.0,
            rouge_l=1.0,
            bleu=1.0,
        ),
        EvaluationResult(
            index=1,
            query="q2",
            answer="partial",
            expected_answer="partial answer",
            exact_span_recall=0.5,
            token_precision=1.0,
            f1=0.6667,
            rouge_l=0.6667,
            bleu=0.0,
        ),
    ]

    summary = summarize_evaluation(results, threshold=0.70)
    assert summary.count == 2
    assert summary.avg_exact_span_recall == pytest.approx(0.75)
    assert summary.passed is True
    d = summary.to_dict()
    assert d["count"] == 2
    assert d["passed"] is True


def test_summarize_empty():
    summary = summarize_evaluation([], threshold=0.85)
    assert summary.count == 0
    assert summary.passed is False
