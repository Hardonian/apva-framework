"""Mock target application used by APVA tests and docker-compose."""

from __future__ import annotations

from fastapi import FastAPI

from apps.backend.services.eval import compute_rag_scores

app = FastAPI(title="APVA Mock Target App", version="1.0.0")


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
