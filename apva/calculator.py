"""The APVA mathematical engine.

Implements the four core APVA formulas exactly as specified:

* True Value Yield (TVY)::

      TVY = (Gross_Time_Saved * RAG_Reliability_Coefficient) - Guardrail_Friction_Tax

* Gross Time Saved (skill stratified)::

      Gross_Time_Saved = Skill_Adjusted_Human_Baseline
                         - (AI_Generation_Time + Epistemic_Verification_Time)

* RAG Reliability Coefficient::

      RAG_Reliability = (0.60 * Exact_Span_Recall) + (0.40 * LLM_Faithfulness_Score)

* Guardrail Friction Tax::

      Guardrail_Tax = Base_Latency_Overhead
                     + (False_Positive_Rate * Resolution_Penalty_Time)
                     + CRA_Session_Drop_Penalty
"""

from __future__ import annotations

from apva.models import (
    APVAReport,
    BenchmarkInput,
    GuardrailMetrics,
    ProductivityMetrics,
    RAGMetrics,
)

# Reliability blend weights (deterministic recall vs. theoretical faithfulness).
SPAN_RECALL_WEIGHT: float = 0.60
FAITHFULNESS_WEIGHT: float = 0.40


class APVACalculator:
    """Stateless engine that evaluates APVA benchmarks.

    The calculator holds no mutable state; every method is pure and
    deterministic given its inputs. This makes results trivially reproducible
    and unit-testable.
    """

    @staticmethod
    def gross_time_saved(productivity: ProductivityMetrics) -> float:
        """Compute Gross Time Saved with skill stratification.

        Formula::

            Gross_Time_Saved = Skill_Adjusted_Human_Baseline
                               - (AI_Generation_Time + Epistemic_Verification_Time)

        Args:
            productivity: Productivity pillar inputs.

        Returns:
            float: Gross time saved in minutes. May be negative when AI
            generation plus epistemic verification exceeds the human baseline.
        """
        ai_total = (
            productivity.ai_generation_time_min
            + productivity.epistemic_verification_time_min
        )
        return productivity.skill_adjusted_human_baseline_min - ai_total

    @staticmethod
    def rag_reliability_coefficient(rag: RAGMetrics) -> float:
        """Compute the blended RAG Reliability Coefficient.

        Formula::

            RAG_Reliability = (0.60 * Exact_Span_Recall)
                             + (0.40 * LLM_Faithfulness_Score)

        Args:
            rag: RAG reliability pillar inputs.

        Returns:
            float: Reliability coefficient in ``[0.0, 1.0]`` (guaranteed by the
            validated input bounds and convex weights summing to 1.0).
        """
        return (
            SPAN_RECALL_WEIGHT * rag.exact_span_recall
            + FAITHFULNESS_WEIGHT * rag.llm_faithfulness_score
        )

    @staticmethod
    def guardrail_friction_tax(guardrail: GuardrailMetrics) -> float:
        """Compute the Guardrail Friction Tax.

        Formula::

            Guardrail_Tax = Base_Latency_Overhead
                           + (False_Positive_Rate * Resolution_Penalty_Time)
                           + CRA_Session_Drop_Penalty

        Args:
            guardrail: Guardrail tax pillar inputs.

        Returns:
            float: Total friction tax in minutes (always >= 0 given validated
            non-negative inputs).
        """
        false_positive_cost = (
            guardrail.false_positive_rate * guardrail.resolution_penalty_time_min
        )
        return (
            guardrail.base_latency_overhead_min
            + false_positive_cost
            + guardrail.cra_session_drop_penalty_min
        )

    @classmethod
    def true_value_yield(cls, benchmark: BenchmarkInput) -> float:
        """Compute the headline True Value Yield (TVY).

        Formula::

            TVY = (Gross_Time_Saved * RAG_Reliability_Coefficient)
                 - Guardrail_Friction_Tax

        Args:
            benchmark: A fully specified benchmark input.

        Returns:
            float: TVY in minutes. Negative values are valid and indicate the
            AI workflow is a net productivity loss for the given parameters.
        """
        gross = cls.gross_time_saved(benchmark.productivity)
        reliability = cls.rag_reliability_coefficient(benchmark.rag)
        tax = cls.guardrail_friction_tax(benchmark.guardrail)
        return (gross * reliability) - tax

    @classmethod
    def evaluate(cls, benchmark: BenchmarkInput) -> APVAReport:
        """Run a full APVA evaluation and produce a structured report.

        Args:
            benchmark: A fully specified benchmark input.

        Returns:
            APVAReport: A validated report capturing every intermediate metric
            and the final TVY.
        """
        gross = cls.gross_time_saved(benchmark.productivity)
        reliability = cls.rag_reliability_coefficient(benchmark.rag)
        tax = cls.guardrail_friction_tax(benchmark.guardrail)
        tvy = (gross * reliability) - tax
        
        tvy_usd = None
        if benchmark.productivity.hourly_rate_usd is not None:
            tvy_usd = (tvy / 60.0) * benchmark.productivity.hourly_rate_usd

        return APVAReport(
            name=benchmark.name,
            skill_adjusted_human_baseline_min=(
                benchmark.productivity.skill_adjusted_human_baseline_min
            ),
            gross_time_saved_min=gross,
            rag_reliability_coefficient=reliability,
            guardrail_friction_tax_min=tax,
            true_value_yield_min=tvy,
            true_value_yield_usd=tvy_usd,
            is_net_positive=tvy > 0.0,
        )


def compute_tvy(benchmark: BenchmarkInput) -> float:
    """Convenience functional wrapper around :meth:`APVACalculator.true_value_yield`.

    Args:
        benchmark: A fully specified benchmark input.

    Returns:
        float: The True Value Yield in minutes.
    """
    return APVACalculator.true_value_yield(benchmark)
