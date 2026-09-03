"""The APVA mathematical engine.

Implements the four core APVA formulas exactly as specified:

* True Value Yield (TVY)::

      TVY = (Gross_Time_Saved * RAG_Reliability_Coefficient) - Guardrail_Friction_Tax

* Gross Time Saved (skill stratified)::

      Gross_Time_Saved = Skill_Adjusted_Human_Baseline
                         - (AI_Generation_Time + Epistemic_Verification_Time)

* RAG Reliability Coefficient::

      RAG_Reliability = (w_r * Exact_Span_Recall) + (w_f * LLM_Faithfulness_Score)

* Guardrail Friction Tax::

      Guardrail_Tax = Base_Latency_Overhead
                     + (False_Positive_Rate * Resolution_Penalty_Time)
                     + CRA_Session_Drop_Penalty

**v3.0 additions**: configurable weights, sensitivity analysis,
Monte Carlo confidence intervals, batch evaluation, comparison,
and qualitative grading.
"""

from __future__ import annotations

import copy
import random
import statistics
from dataclasses import dataclass
from typing import Any

from apva.constants import (
    DEFAULT_CONFIDENCE_LEVEL,
    DEFAULT_FAITHFULNESS_WEIGHT,
    DEFAULT_MONTE_CARLO_SIMULATIONS,
    DEFAULT_SENSITIVITY_DELTA,
    DEFAULT_SPAN_RECALL_WEIGHT,
)
from apva.models import (
    APVAReport,
    BenchmarkInput,
    ConfidenceInterval,
    GuardrailMetrics,
    ProductivityMetrics,
    RAGMetrics,
    SensitivityVector,
    TVYGrade,
)

# ---------------------------------------------------------------------------
# Calculator configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class APVACalculatorConfig:
    """Per-evaluation configuration for the APVA calculator.

    Allows A/B testing of reliability blend weights without modifying
    the global constants.

    Attributes:
        span_recall_weight: Weight for exact-span recall in the reliability
            blend. Must sum to 1.0 with ``faithfulness_weight``.
        faithfulness_weight: Weight for LLM-as-judge faithfulness.
    """

    span_recall_weight: float = DEFAULT_SPAN_RECALL_WEIGHT
    faithfulness_weight: float = DEFAULT_FAITHFULNESS_WEIGHT

    def __post_init__(self) -> None:
        total = self.span_recall_weight + self.faithfulness_weight
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Reliability weights must sum to 1.0, got {total:.6f}.")


# Module-level default config
_DEFAULT_CONFIG = APVACalculatorConfig()


# ---------------------------------------------------------------------------
# Core calculator
# ---------------------------------------------------------------------------


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
            productivity.ai_generation_time_min + productivity.epistemic_verification_time_min
        )
        return productivity.skill_adjusted_human_baseline_min - ai_total

    @staticmethod
    def rag_reliability_coefficient(
        rag: RAGMetrics,
        config: APVACalculatorConfig | None = None,
    ) -> float:
        """Compute the blended RAG Reliability Coefficient.

        Formula::

            RAG_Reliability = (w_r * Exact_Span_Recall)
                             + (w_f * LLM_Faithfulness_Score)

        Args:
            rag: RAG reliability pillar inputs.
            config: Optional calculator configuration with custom weights.

        Returns:
            float: Reliability coefficient in ``[0.0, 1.0]``.
        """
        cfg = config or _DEFAULT_CONFIG
        return (
            cfg.span_recall_weight * rag.exact_span_recall
            + cfg.faithfulness_weight * rag.llm_faithfulness_score
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
        false_positive_cost = guardrail.false_positive_rate * guardrail.resolution_penalty_time_min
        return (
            guardrail.base_latency_overhead_min
            + false_positive_cost
            + guardrail.cra_session_drop_penalty_min
        )

    @classmethod
    def true_value_yield(
        cls,
        benchmark: BenchmarkInput,
        config: APVACalculatorConfig | None = None,
    ) -> float:
        """Compute the headline True Value Yield (TVY).

        Formula::

            TVY = (Gross_Time_Saved * RAG_Reliability_Coefficient)
                 - Guardrail_Friction_Tax

        Args:
            benchmark: A fully specified benchmark input.
            config: Optional calculator configuration with custom weights.

        Returns:
            float: TVY in minutes. Negative values are valid and indicate the
            AI workflow is a net productivity loss for the given parameters.
        """
        gross = cls.gross_time_saved(benchmark.productivity)
        reliability = cls.rag_reliability_coefficient(benchmark.rag, config)
        tax = cls.guardrail_friction_tax(benchmark.guardrail)
        return (gross * reliability) - tax

    @classmethod
    def evaluate(
        cls,
        benchmark: BenchmarkInput,
        config: APVACalculatorConfig | None = None,
        *,
        include_sensitivity: bool = False,
        include_confidence_interval: bool = False,
        n_simulations: int = DEFAULT_MONTE_CARLO_SIMULATIONS,
        sensitivity_delta: float = DEFAULT_SENSITIVITY_DELTA,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
    ) -> APVAReport:
        """Run a full APVA evaluation and produce a structured report.

        Args:
            benchmark: A fully specified benchmark input.
            config: Optional calculator configuration with custom weights.
            include_sensitivity: If True, compute per-parameter sensitivity.
            include_confidence_interval: If True, run Monte Carlo simulation.
            n_simulations: Number of Monte Carlo iterations.
            sensitivity_delta: Fractional perturbation for sensitivity analysis.
            confidence_level: Confidence level for the interval (e.g. 0.95).

        Returns:
            APVAReport: A validated report capturing every intermediate metric
            and the final TVY.
        """
        cfg = config or _DEFAULT_CONFIG

        gross = cls.gross_time_saved(benchmark.productivity)
        reliability = cls.rag_reliability_coefficient(benchmark.rag, cfg)
        tax = cls.guardrail_friction_tax(benchmark.guardrail)
        tvy = (gross * reliability) - tax

        tvy_usd = None
        if benchmark.productivity.hourly_rate_usd is not None:
            tvy_usd = (tvy / 60.0) * benchmark.productivity.hourly_rate_usd

        sensitivity: list[SensitivityVector] = []
        if include_sensitivity:
            sensitivity = cls.sensitivity_analysis(
                benchmark, config=cfg, delta_fraction=sensitivity_delta
            )

        ci: ConfidenceInterval | None = None
        if include_confidence_interval:
            ci = cls.confidence_interval(
                benchmark,
                config=cfg,
                n_simulations=n_simulations,
                noise_pct=sensitivity_delta,
                confidence_level=confidence_level,
            )

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
            tvy_grade=TVYGrade.from_tvy(tvy),
            sensitivity=sensitivity,
            confidence_interval=ci,
        )

    @classmethod
    def evaluate_batch(
        cls,
        benchmarks: list[BenchmarkInput],
        config: APVACalculatorConfig | None = None,
        **kwargs: Any,
    ) -> list[APVAReport]:
        """Evaluate multiple benchmarks and return their reports.

        Args:
            benchmarks: List of benchmark inputs.
            config: Optional shared calculator configuration.
            **kwargs: Additional keyword arguments passed to :meth:`evaluate`.

        Returns:
            list[APVAReport]: One report per benchmark, in order.
        """
        return [cls.evaluate(b, config, **kwargs) for b in benchmarks]

    @classmethod
    def compare(cls, reports: list[APVAReport]) -> dict[str, Any]:
        """Compare multiple reports and return rankings and deltas.

        Args:
            reports: Two or more APVA reports to compare.

        Returns:
            dict: Comparison summary with rankings, best/worst, and deltas.
        """
        if len(reports) < 2:
            raise ValueError("compare() requires at least 2 reports.")

        sorted_reports = sorted(reports, key=lambda r: r.true_value_yield_min, reverse=True)
        best = sorted_reports[0]
        worst = sorted_reports[-1]
        tvy_values = [r.true_value_yield_min for r in reports]

        return {
            "rankings": [
                {
                    "rank": i + 1,
                    "benchmark": r.benchmark_name,
                    "tvy_min": round(r.true_value_yield_min, 4),
                    "tvy_grade": r.tvy_grade.value,
                    "is_net_positive": r.is_net_positive,
                }
                for i, r in enumerate(sorted_reports)
            ],
            "best": best.benchmark_name,
            "worst": worst.benchmark_name,
            "tvy_spread_min": round(best.true_value_yield_min - worst.true_value_yield_min, 4),
            "avg_tvy_min": round(statistics.mean(tvy_values), 4),
            "median_tvy_min": round(statistics.median(tvy_values), 4),
            "all_net_positive": all(r.is_net_positive for r in reports),
        }

    # -------------------------------------------------------------------
    # Sensitivity analysis
    # -------------------------------------------------------------------

    @classmethod
    def sensitivity_analysis(
        cls,
        benchmark: BenchmarkInput,
        config: APVACalculatorConfig | None = None,
        delta_fraction: float = DEFAULT_SENSITIVITY_DELTA,
    ) -> list[SensitivityVector]:
        """Perturb each numeric input by ±delta and measure TVY impact.

        Args:
            benchmark: Base benchmark input.
            config: Optional calculator configuration.
            delta_fraction: Fractional perturbation (e.g. 0.05 = ±5%).

        Returns:
            list[SensitivityVector]: One entry per perturbed parameter,
            sorted by descending ``tvy_impact``.
        """
        cfg = config or _DEFAULT_CONFIG
        results: list[SensitivityVector] = []

        perturbable: list[tuple[str, str, str, float]] = [
            (
                "productivity",
                "reference_human_baseline_min",
                "productivity.reference_human_baseline_min",
                benchmark.productivity.reference_human_baseline_min,
            ),
            (
                "productivity",
                "ai_generation_time_min",
                "productivity.ai_generation_time_min",
                benchmark.productivity.ai_generation_time_min,
            ),
            (
                "productivity",
                "epistemic_verification_time_min",
                "productivity.epistemic_verification_time_min",
                benchmark.productivity.epistemic_verification_time_min,
            ),
            ("rag", "exact_span_recall", "rag.exact_span_recall", benchmark.rag.exact_span_recall),
            (
                "rag",
                "llm_faithfulness_score",
                "rag.llm_faithfulness_score",
                benchmark.rag.llm_faithfulness_score,
            ),
            (
                "guardrail",
                "base_latency_overhead_min",
                "guardrail.base_latency_overhead_min",
                benchmark.guardrail.base_latency_overhead_min,
            ),
            (
                "guardrail",
                "false_positive_rate",
                "guardrail.false_positive_rate",
                benchmark.guardrail.false_positive_rate,
            ),
            (
                "guardrail",
                "resolution_penalty_time_min",
                "guardrail.resolution_penalty_time_min",
                benchmark.guardrail.resolution_penalty_time_min,
            ),
            (
                "guardrail",
                "cra_session_drop_penalty_min",
                "guardrail.cra_session_drop_penalty_min",
                benchmark.guardrail.cra_session_drop_penalty_min,
            ),
        ]

        for pillar, attr, dotted_path, base_value in perturbable:
            if base_value == 0.0:
                # Use absolute delta for zero-valued parameters
                delta = delta_fraction
            else:
                delta = abs(base_value * delta_fraction)

            lower_val = max(0.0, base_value - delta)
            upper_val = base_value + delta

            # Clamp probabilities to [0, 1]
            if attr in ("exact_span_recall", "llm_faithfulness_score", "false_positive_rate"):
                upper_val = min(1.0, upper_val)

            tvy_lower = cls._evaluate_with_override(benchmark, pillar, attr, lower_val, cfg)
            tvy_upper = cls._evaluate_with_override(benchmark, pillar, attr, upper_val, cfg)

            results.append(
                SensitivityVector(
                    parameter=dotted_path,
                    base_value=base_value,
                    delta=delta,
                    tvy_at_lower=round(tvy_lower, 6),
                    tvy_at_upper=round(tvy_upper, 6),
                    tvy_impact=round(abs(tvy_upper - tvy_lower), 6),
                )
            )

        results.sort(key=lambda sv: sv.tvy_impact, reverse=True)
        return results

    @classmethod
    def _evaluate_with_override(
        cls,
        benchmark: BenchmarkInput,
        pillar: str,
        attr: str,
        value: float,
        config: APVACalculatorConfig,
    ) -> float:
        """Compute TVY with a single parameter overridden.

        Args:
            benchmark: Base benchmark input.
            pillar: Pillar name ("productivity", "rag", "guardrail").
            attr: Attribute name within the pillar.
            value: Override value.
            config: Calculator configuration.

        Returns:
            float: TVY with the parameter overridden.
        """
        data = benchmark.model_dump()
        data[pillar][attr] = value
        modified = BenchmarkInput.model_validate(data)
        return cls.true_value_yield(modified, config)

    # -------------------------------------------------------------------
    # Monte Carlo confidence interval
    # -------------------------------------------------------------------

    @classmethod
    def confidence_interval(
        cls,
        benchmark: BenchmarkInput,
        config: APVACalculatorConfig | None = None,
        n_simulations: int = DEFAULT_MONTE_CARLO_SIMULATIONS,
        noise_pct: float = DEFAULT_SENSITIVITY_DELTA,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        seed: int | None = None,
    ) -> ConfidenceInterval:
        """Estimate a confidence interval for TVY via Monte Carlo simulation.

        Adds Gaussian noise (stddev = ``noise_pct * base_value``) to every
        numeric input and re-computes TVY ``n_simulations`` times. The
        resulting distribution is used to extract percentile bounds.

        Args:
            benchmark: Base benchmark input.
            config: Optional calculator configuration.
            n_simulations: Number of Monte Carlo iterations.
            noise_pct: Standard deviation as a fraction of each parameter value.
            confidence_level: Confidence level (e.g. 0.95 for 95%).
            seed: Optional random seed for reproducibility.

        Returns:
            ConfidenceInterval: Lower, median, and upper bounds.
        """
        cfg = config or _DEFAULT_CONFIG
        rng = random.Random(seed)
        tvy_samples: list[float] = []

        base_data = benchmark.model_dump()

        numeric_paths: list[tuple[str, str, float, bool]] = [
            (
                "productivity",
                "reference_human_baseline_min",
                benchmark.productivity.reference_human_baseline_min,
                False,
            ),
            (
                "productivity",
                "ai_generation_time_min",
                benchmark.productivity.ai_generation_time_min,
                False,
            ),
            (
                "productivity",
                "epistemic_verification_time_min",
                benchmark.productivity.epistemic_verification_time_min,
                False,
            ),
            ("rag", "exact_span_recall", benchmark.rag.exact_span_recall, True),
            ("rag", "llm_faithfulness_score", benchmark.rag.llm_faithfulness_score, True),
            (
                "guardrail",
                "base_latency_overhead_min",
                benchmark.guardrail.base_latency_overhead_min,
                False,
            ),
            ("guardrail", "false_positive_rate", benchmark.guardrail.false_positive_rate, True),
            (
                "guardrail",
                "resolution_penalty_time_min",
                benchmark.guardrail.resolution_penalty_time_min,
                False,
            ),
            (
                "guardrail",
                "cra_session_drop_penalty_min",
                benchmark.guardrail.cra_session_drop_penalty_min,
                False,
            ),
        ]

        for _ in range(n_simulations):
            sim_data = copy.deepcopy(base_data)
            for pillar, attr, base_val, is_prob in numeric_paths:
                stddev = noise_pct * base_val if base_val != 0 else noise_pct * 0.1
                noisy = rng.gauss(base_val, stddev)
                noisy = max(0.0, noisy)
                if is_prob:
                    noisy = min(1.0, noisy)
                sim_data[pillar][attr] = noisy

            try:
                sim_benchmark = BenchmarkInput.model_validate(sim_data)
                tvy_samples.append(cls.true_value_yield(sim_benchmark, cfg))
            except Exception:
                # Skip invalid samples (rare edge case)
                continue

        if not tvy_samples:
            base_tvy = cls.true_value_yield(benchmark, cfg)
            return ConfidenceInterval(
                lower=base_tvy,
                median=base_tvy,
                upper=base_tvy,
                confidence_level=confidence_level,
                n_simulations=n_simulations,
            )

        tvy_samples.sort()
        alpha = (1.0 - confidence_level) / 2.0
        lower_idx = int(alpha * len(tvy_samples))
        upper_idx = int((1.0 - alpha) * len(tvy_samples)) - 1
        median_idx = len(tvy_samples) // 2

        return ConfidenceInterval(
            lower=round(tvy_samples[max(0, lower_idx)], 4),
            median=round(tvy_samples[median_idx], 4),
            upper=round(tvy_samples[min(upper_idx, len(tvy_samples) - 1)], 4),
            confidence_level=confidence_level,
            n_simulations=len(tvy_samples),
        )


def compute_tvy(benchmark: BenchmarkInput) -> float:
    """Convenience functional wrapper around :meth:`APVACalculator.true_value_yield`.

    Args:
        benchmark: A fully specified benchmark input.

    Returns:
        float: The True Value Yield in minutes.
    """
    return APVACalculator.true_value_yield(benchmark)
