"""Tests for APVA calculator."""

from __future__ import annotations

import pytest

from apva.calculator import APVACalculator
from apva.models import GuardrailMetrics, ProductivityMetrics, RAGMetrics, SkillLevel


def test_gross_time_saved_positive():
    productivity = ProductivityMetrics(
        reference_human_baseline_min=60.0,
        skill_level=SkillLevel.SENIOR,
        ai_generation_time_min=10.0,
        epistemic_verification_time_min=5.0,
    )
    gross = APVACalculator.gross_time_saved(productivity)
    assert pytest.approx(gross) == 60.0 * 0.7 - 15.0


def test_gross_time_saved_zero():
    productivity = ProductivityMetrics(
        reference_human_baseline_min=30.0,
        skill_level=SkillLevel.MID,
        ai_generation_time_min=15.0,
        epistemic_verification_time_min=15.0,
    )
    gross = APVACalculator.gross_time_saved(productivity)
    assert pytest.approx(gross) == 0.0


def test_gross_time_saved_negative():
    productivity = ProductivityMetrics(
        reference_human_baseline_min=10.0,
        skill_level=SkillLevel.SENIOR,
        ai_generation_time_min=20.0,
        epistemic_verification_time_min=20.0,
    )
    gross = APVACalculator.gross_time_saved(productivity)
    assert gross < 0.0


def test_rag_reliability_coefficient():
    rag = RAGMetrics(exact_span_recall=0.9, llm_faithfulness_score=0.8)
    reliability = APVACalculator.rag_reliability_coefficient(rag)
    assert pytest.approx(reliability) == 0.6 * 0.9 + 0.4 * 0.8


def test_rag_reliability_perfect():
    rag = RAGMetrics(exact_span_recall=1.0, llm_faithfulness_score=1.0)
    reliability = APVACalculator.rag_reliability_coefficient(rag)
    assert pytest.approx(reliability) == 1.0


def test_guardrail_friction_tax():
    guardrail = GuardrailMetrics(
        base_latency_overhead_min=1.0,
        false_positive_rate=0.0,
        resolution_penalty_time_min=0.0,
        cra_session_drop_penalty_min=0.0,
    )
    tax = APVACalculator.guardrail_friction_tax(guardrail)
    assert pytest.approx(tax) == 1.0


def test_guardrail_friction_tax_with_false_positives():
    guardrail = GuardrailMetrics(
        base_latency_overhead_min=1.0,
        false_positive_rate=0.5,
        resolution_penalty_time_min=4.0,
        cra_session_drop_penalty_min=2.0,
    )
    tax = APVACalculator.guardrail_friction_tax(guardrail)
    assert pytest.approx(tax) == 1.0 + 0.5 * 4.0 + 2.0


def test_true_value_yield_basic():
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
    tvy = APVACalculator.true_value_yield(
        type("B", (), {"productivity": productivity, "rag": rag, "guardrail": guardrail, "name": "basic"})()
    )
    expected = ((60.0 * 0.7) - 15.0) * (0.6 * 0.9 + 0.4 * 0.8) - 1.0
    assert pytest.approx(tvy) == expected


def test_true_value_yield_negative():
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
    tvy = APVACalculator.true_value_yield(
        type("B", (), {"productivity": productivity, "rag": rag, "guardrail": guardrail, "name": "neg"})()
    )
    assert tvy < 0.0


def test_evaluate_report_fields():
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
    benchmark = type("B", (), {"productivity": productivity, "rag": rag, "guardrail": guardrail, "name": "rpt"})()
    report = APVACalculator.evaluate(benchmark)
    assert report.gross_time_saved_min == pytest.approx(27.0)
    assert report.rag_reliability_coefficient == pytest.approx(0.86)
    assert report.true_value_yield_min == pytest.approx((27.0 * 0.86) - 1.0)
    assert report.is_net_positive is True


def test_skill_level_multipliers():
    assert SkillLevel.JUNIOR.baseline_multiplier == 1.5
    assert SkillLevel.MID.baseline_multiplier == 1.0
    assert SkillLevel.SENIOR.baseline_multiplier == 0.7


def test_skill_validation_rejects_invalid():
    with pytest.raises(ValueError):
        ProductivityMetrics(
            reference_human_baseline_min=60.0,
            skill_level="invalid",
            ai_generation_time_min=10.0,
            epistemic_verification_time_min=5.0,
        )


def test_guardrail_metrics_bounds():
    with pytest.raises(ValueError):
        GuardrailMetrics(
            base_latency_overhead_min=-1.0,
            false_positive_rate=0.0,
            resolution_penalty_time_min=0.0,
            cra_session_drop_penalty_min=0.0,
        )
