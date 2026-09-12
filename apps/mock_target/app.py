"""Mock target application used by APVA tests and docker-compose."""

from __future__ import annotations

from fastapi import FastAPI

try:
    from apps.backend.services.eval import compute_rag_scores
except ImportError:
    try:
        from apva.scoring import exact_span_recall, token_precision

        def compute_rag_scores(answer: str, expected_answer: str):
            recall = exact_span_recall(answer, expected_answer)
            precision = token_precision(answer, expected_answer)
            faithfulness = min(1.0, max(0.0, 0.75 * recall + 0.25 * precision))
            reliability = 0.6 * recall + 0.4 * faithfulness
            from types import SimpleNamespace
            return SimpleNamespace(
                exact_span_recall=recall,
                llm_faithfulness_score=faithfulness,
                precision_score=precision,
                rag_reliability_coefficient=reliability,
            )
    except ImportError:
        def compute_rag_scores(answer: str, expected_answer: str):
            import re

            def tok(s: str) -> list[str]:
                return re.findall(r"[a-zA-Z0-9]+(?:[-'][a-zA-Z0-9]+)*", s.lower())

            exp_tokens = tok(expected_answer)
            ans_tokens = tok(answer)
            ans_set = set(ans_tokens)
            exp_set = set(exp_tokens)
            recall = sum(1 for t in exp_tokens if t in ans_set) / len(exp_tokens) if exp_tokens else 1.0
            precision = len(exp_set & ans_set) / len(ans_tokens) if ans_tokens else 1.0
            faithfulness = min(1.0, max(0.0, 0.75 * recall + 0.25 * precision))
            reliability = 0.6 * recall + 0.4 * faithfulness
            from types import SimpleNamespace
            return SimpleNamespace(
                exact_span_recall=recall,
                llm_faithfulness_score=faithfulness,
                precision_score=precision,
                rag_reliability_coefficient=reliability,
            )

app = FastAPI(title="APVA Target Evaluation App", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Return mock target health.

    Returns:
        dict[str, str]: Health payload.
    """
    return {"status": "ok"}


@app.post("/score-faithfulness")
def score_faithfulness(payload: dict) -> dict:
    """Score a RAG transcript with deterministic local metrics.

    Args:
        payload: Evaluation payload with answer and expected_answer.

    Returns:
        dict: RAG score payload.
    """
    scores = compute_rag_scores(payload["answer"], payload["expected_answer"])
    return {
        "exact_span_recall": scores.exact_span_recall,
        "llm_faithfulness_score": scores.llm_faithfulness_score,
        "precision_score": scores.precision_score,
        "rag_reliability_coefficient": scores.rag_reliability_coefficient,
    }
