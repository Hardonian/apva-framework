"""Quickstart: Sensitivity analysis and Monte Carlo confidence interval estimation."""

from __future__ import annotations

from apva.calculator import APVACalculator
from apva.formatters import format_table
from apva.models import (
    BenchmarkInput,
    GuardrailMetrics,
    ProductivityMetrics,
    RAGMetrics,
    SkillLevel,
)


def main() -> None:
    benchmark = BenchmarkInput(
        name="finance-rag-copilot",
        productivity=ProductivityMetrics(
            reference_human_baseline_min=45.0,
            skill_level=SkillLevel.SENIOR,
            ai_generation_time_min=3.5,
            epistemic_verification_time_min=6.0,
            hourly_rate_usd=95.0,
        ),
        rag=RAGMetrics(
            exact_span_recall=0.88,
            llm_faithfulness_score=0.91,
        ),
        guardrail=GuardrailMetrics(
            base_latency_overhead_min=0.6,
            false_positive_rate=0.04,
            resolution_penalty_time_min=12.0,
            cra_session_drop_penalty_min=1.5,
        ),
    )

    print("=== 1. Primary Evaluation ===")
    report = APVACalculator.evaluate(benchmark)
    print(f"Benchmark: {report.benchmark_name}")
    print(f"True Value Yield: {report.true_value_yield_min:+.2f} min (${report.true_value_yield_usd:.2f})")
    print(f"Grade: {report.tvy_grade.value.upper()}")

    print("\n=== 2. Sensitivity Analysis (Top 5 Impact Drivers) ===")
    vectors = APVACalculator.sensitivity_analysis(benchmark, delta_fraction=0.05)
    headers = ["Parameter", "Base Value", "Delta", "TVY Impact"]
    rows = [
        [v.parameter, f"{v.base_value:.4f}", f"{v.delta:.4f}", f"{v.tvy_impact:.4f}"]
        for v in vectors[:5]
    ]
    print(format_table(headers, rows))

    print("\n=== 3. Monte Carlo Confidence Interval (95% CI) ===")
    ci = APVACalculator.confidence_interval(benchmark, n_simulations=1000, seed=42)
    print(f"Lower Bound (2.5%):  {ci.lower:+.2f} min")
    print(f"Median (50.0%):      {ci.median:+.2f} min")
    print(f"Upper Bound (97.5%): {ci.upper:+.2f} min")


if __name__ == "__main__":
    main()
