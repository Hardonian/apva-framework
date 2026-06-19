"""Tests for APVA calculator."""

from __future__ import annotations

import pytest

from apva.calculator import APVACalculator
from apva.models import (
    GuardrailMetrics,
    IncidentLevel,
    ProductivityMetrics,
    RAGMetrics,
    SkillLevel,
)


def test_tvy_basic():
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
    benchmark = APVACalculator.build_benchmark(
        productivity=productivity,
        rag=rag,
        guardrail=guardrail,
    )
    tvy = APVACalculator.true_value_yield(benchmark)
    expected = pytest.approx(((60.0 * 0.7) - 15.0) * (0.6 * 0.9 + 0.4 * 0.8) - 1.0)
    assert tvy == expected


def test_tvy_zero_gross_time_saved():
    productivity = ProductivityMetrics(
        reference_human_baseline_min=20.0,
        skill_level=SkillLevel.MID,
        ai_generation_time_min=10.0,
        epistemic_verification_time_min=10.0,
    )
    rag = RAGMetrics(exact_span_recall=1.0, llm_faithfulness_score=1.0)
    guardrail = GuardrailMetrics(
        base_latency_overhead_min=0.0,
        false_positive_rate=0.0,
        resolution_penalty_time_min=0.0,
        cra_session_drop_penalty_min=0.0,
    )
    benchmark = APVACalculator.build_benchmark(
        productivity, rag=rag, guardrail=guardrail
    )
    assert pytest.approx(APVACalculator.true_value_yield(benchmark)) == 0.0


def test_tvy_negative():
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
    benchmark = APVACalculator.build_benchmark(
        productivity, rag=rag, guardrail=guardrail
    )
    tvy = APVACalculator.true_value_yield(benchmark)
    assert tvy < 0.0


def test_gate_threshold_pass():
    benchmark = type("benchmark", (), {})()
    benchmark.rag_reliability = 0.9
    benchmark.guardrail_risk_level = IncidentLevel.LOW
    benchmark.tvy_minutes = 100.0
    assert APVACalculator.meets_threshold(benchmark) is True


def test_gate_threshold_fail_on_reliability():
    benchmark = type("benchmark", (), {})()
    benchmark.rag_reliability = 0.5
    benchmark.guardrail_risk_level = IncidentLevel.LOW
    benchmark.tvy_minutes = 100.0
    assert APVACalculator.meets_threshold(benchmark) is False


def test_gate_threshold_fail_on_risk():
    benchmark = type("benchmark", (), {})()
    benchmark.rag_reliability = 0.9
    benchmark.guardrail_risk_level = IncidentLevel.HIGH
    benchmark.tvy_minutes = 100.0
    assert APVACalculator.meets_threshold(benchmark) is False


def test_gate_threshold_fail_on_negative_tvy():
    benchmark = type("benchmark", (), {})()
    benchmark.rag_reliability = 0.9
    benchmark.guardrail_risk_level = IncidentLevel.LOW
    benchmark.tvy_minutes = -1.0
    assert APVACalculator.meets_threshold(benchmark) is False


def test_guardrail_risk_levels():
    low = APVACalculator.guardrail_risk_level(GuardrailMetrics(1.0, 0.0, 0.0, 0.0))
    high = APVACalculator.guardrail_risk_level(
        GuardrailMetrics(1.0, 1.0, 10.0, 10.0)
    )
    assert low == IncidentLevel.LOW
    assert high == IncidentLevel.HIGH


def test_report_shape():
    benchmark = APVACalculator.build_benchmark(
        ProductivityMetrics(
            reference_human_baseline_min=60.0,
            skill_level=SkillLevel.SENIOR,
            ai_generation_time_min=10.0,
            epistemic_verification_time_min=5.0,
        ),
        rag=RAGMetrics(exact_span_recall=0.9, llm_faithfulness_score=0.8),
        guardrail=GuardrailMetrics(base_latency_overhead_min=1.0),
    )
    report = APVACalculator.report(benchmark)
    assert report.productivity.gross_time_saved_min == pytest.approx(27.0)
    assert report.rag.rag_reliability_coefficient == pytest.approx(0.86)
    assert isinstance(report.metadata, dict)


def test_skill_validation():
    with pytest.raises(ValueError):
        APVACalculator.build_benchmark(
            ProductivityMetrics(
                reference_human_baseline_min=60.0,
                skill_level="invalid",
                ai_generation_time_min=10.0,
                epistemic_verification_time_min=5.0,
            ),
            rag=RAGMetrics(exact_span_recall=1.0, llm_faithfulness_score=1.0),
            guardrail=GuardrailMetrics(base_latency_overhead_min=0.0),
        )
