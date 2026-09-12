"""Deterministic Grounding and Faithfulness Evaluator."""

from __future__ import annotations

import logging

from apva.scoring import exact_span_recall, token_precision

logger = logging.getLogger(__name__)


class ProprietarySLM:
    """Deterministic RAG Faithfulness and Grounding Scoring Engine.

    Evaluates retrieval grounding, context containment, and factual alignment
    using token-level precision and recall metrics.
    """

    @classmethod
    async def evaluate_rag(
        cls,
        query: str,
        context: str,
        answer: str,
        expected_answer: str | None = None,
        *,
        deterministic: bool = True,
    ) -> float:
        """Evaluate RAG faithfulness score.

        Args:
            query: The user's prompt.
            context: The retrieved context chunks.
            answer: The AI's generated response.
            expected_answer: Optional ground truth.
            deterministic: Parameter preserved for interface compatibility.

        Returns:
            float: Faithfulness score between 0.0 and 1.0.
        """
        logger.debug("[SLM] Evaluating RAG grounding and alignment...")

        if not answer.strip():
            return 0.0

        # 1. Context grounding: What fraction of answer content is supported by context?
        if context.strip():
            grounding_precision = token_precision(answer, context)
        else:
            grounding_precision = 0.50

        # 2. Answer correctness against expected answer (if available)
        if expected_answer and expected_answer.strip():
            correctness_recall = exact_span_recall(answer, expected_answer)
            correctness_precision = token_precision(answer, expected_answer)
            correctness = 0.60 * correctness_recall + 0.40 * correctness_precision
            # Blended score: 50% grounding in context, 50% alignment with ground truth
            score = 0.50 * grounding_precision + 0.50 * correctness
        else:
            score = grounding_precision

        # 3. Penalize responses that exceed context window by more than 2x without grounding
        if context and len(answer) > 2 * len(context) and grounding_precision < 0.70:
            score = max(0.0, score - 0.20)

        return max(0.0, min(1.0, round(score, 4)))

