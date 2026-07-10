"""Executable verification script for APVA calculator.

Produces real numeric outputs for the four core formulas plus negative-TVY and zero-TVY cases.
"""
from __future__ import annotations
from apva.calculator import APVACalculator
from apva.models import (
    APVAReport,
    BenchmarkInput,
    GuardrailMetrics,
    ProductivityMetrics,
    RAGMetrics,
    SkillLevel,
)


def main():
    # Case 1: basic positive TVY
    productivity = ProductivityMetrics(
        reference_human_baseline_min=60.0,
        skill_level=SkillLevel.SENIOR,
        ai_generation_time_min=10.0,
        epistemic_verification_time_min=5.0,
    )
    rag = RAGMetrics(exact_span_recall=0.9, llm_faithfulness_score=0.8)
    guardrail = GuardrailMetrics(
        base_latency_overhead_min=1.0,
        false_positive_rate=0.0,
        resolution_penalty_time_min=0.0,
        cra_session_drop_penalty_min=0.0,
    )
    benchmark = BenchmarkInput(
        name="basic",
        productivity=productivity,
        rag=rag,
        guardrail=guardrail,
    )
    report = APVACalculator.evaluate(benchmark)
    tv = APVACalculator.true_value_yield(benchmark)
    expected = (60.0 - 15.0) * (0.6 * 0.9 + 0.4 * 0.8) - 1.0
    print("basic_expected", expected)
    print("basic_tv", tv)
    print(
        "basic_pass",
        round(float(tv), 6) == round(float(expected), 6),
        round(float(tv), 6),
        round(float(expected), 6),
    )

    # Case 2: zero baseline savings -> zero TVY with perfect metrics
    productivity = ProductivityMetrics(
        reference_human_baseline_min=30.0,
        skill_level=SkillLevel.JUNIOR,
        ai_generation_time_min=15.0,
        epistemic_verification_time_min=15.0,
    )
    rag = RAGMetrics(exact_span_recall=1.0, llm_faithfulness_score=1.0)
    guardrail = GuardrailMetrics(
        base_latency_overhead_min=0.0,
        false_positive_rate=0.0,
        resolution_penalty_time_min=0.0,
        cra_session_drop_penalty_min=0.0,
    )
    benchmark = BenchmarkInput(
        name="zero_savings",
        productivity=productivity,
        rag=rag,
        guardrail=guardrail,
    )
    tv = APVACalculator.true_value_yield(benchmark)
    print("zero_tv", tv, "pass", tv == 0.0)

    # Case 3: clearly negative TVY
    productivity = ProductivityMetrics(
        reference_human_baseline_min=10.0,
        skill_level=SkillLevel.SENIOR,
        ai_generation_time_min=20.0,
        epistemic_verification_time_min=20.0,
    )
    rag = RAGMetrics(exact_span_recall=0.5, llm_faithfulness_score=0.5)
    guardrail = GuardrailMetrics(
        base_latency_overhead_min=10.0,
        false_positive_rate=1.0,
        resolution_penalty_time_min=10.0,
        cra_session_drop_penalty_min=10.0,
    )
    benchmark = BenchmarkInput(
        name="negative",
        productivity=productivity,
        rag=rag,
        guardrail=guardrail,
    )
    tv = APVACalculator.true_value_yield(benchmark)
    print("neg_tv", tv, "pass", tv < 0.0)


if __name__ == "__main__":
    main()
