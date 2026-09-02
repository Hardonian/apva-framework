"""Comprehensive unit tests for the APVA calculator engine and data models."""

from __future__ import annotations

import pytest

from apva.calculator import APVACalculator, APVACalculatorConfig
from apva.models import (
    BenchmarkInput,
    GuardrailMetrics,
    ProductivityMetrics,
    RAGMetrics,
    SkillLevel,
    TVYGrade,
)


def _sample_benchmark(
    name: str = "test-benchmark",
    baseline: float = 60.0,
    skill: SkillLevel = SkillLevel.SENIOR,
    ai_time: float = 10.0,
    verify_time: float = 5.0,
    recall: float = 0.9,
    faithfulness: float = 0.8,
    base_latency: float = 1.0,
    fp_rate: float = 0.0,
    resolution_penalty: float = 0.0,
    cra: float = 0.0,
    hourly_rate: float | None = None,
) -> BenchmarkInput:
    """Helper to construct a fully validated BenchmarkInput."""
    return BenchmarkInput(
        name=name,
        productivity=ProductivityMetrics(
            reference_human_baseline_min=baseline,
            skill_level=skill,
            ai_generation_time_min=ai_time,
            epistemic_verification_time_min=verify_time,
            hourly_rate_usd=hourly_rate,
        ),
        rag=RAGMetrics(
            exact_span_recall=recall,
            llm_faithfulness_score=faithfulness,
        ),
        guardrail=GuardrailMetrics(
            base_latency_overhead_min=base_latency,
            false_positive_rate=fp_rate,
            resolution_penalty_time_min=resolution_penalty,
            cra_session_drop_penalty_min=cra,
        ),
    )


# ---------------------------------------------------------------------------
# Gross Time Saved Tests
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# RAG Reliability Tests
# ---------------------------------------------------------------------------

def test_rag_reliability_coefficient():
    rag = RAGMetrics(exact_span_recall=0.9, llm_faithfulness_score=0.8)
    reliability = APVACalculator.rag_reliability_coefficient(rag)
    assert pytest.approx(reliability) == 0.6 * 0.9 + 0.4 * 0.8


def test_rag_reliability_perfect():
    rag = RAGMetrics(exact_span_recall=1.0, llm_faithfulness_score=1.0)
    reliability = APVACalculator.rag_reliability_coefficient(rag)
    assert pytest.approx(reliability) == 1.0


def test_rag_reliability_custom_config():
    rag = RAGMetrics(exact_span_recall=0.8, llm_faithfulness_score=0.6)
    config = APVACalculatorConfig(span_recall_weight=0.7, faithfulness_weight=0.3)
    reliability = APVACalculator.rag_reliability_coefficient(rag, config)
    assert pytest.approx(reliability) == 0.7 * 0.8 + 0.3 * 0.6


def test_invalid_calculator_config():
    with pytest.raises(ValueError):
        APVACalculatorConfig(span_recall_weight=0.5, faithfulness_weight=0.6)


# ---------------------------------------------------------------------------
# Guardrail Tax Tests
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# True Value Yield & Full Evaluation Tests (Using Real BenchmarkInput)
# ---------------------------------------------------------------------------

def test_true_value_yield_basic():
    benchmark = _sample_benchmark(name="basic", baseline=60.0, skill=SkillLevel.SENIOR)
    tvy = APVACalculator.true_value_yield(benchmark)
    expected = ((60.0 * 0.7) - 15.0) * (0.6 * 0.9 + 0.4 * 0.8) - 1.0
    assert pytest.approx(tvy) == expected


def test_true_value_yield_negative():
    benchmark = _sample_benchmark(
        name="neg",
        baseline=10.0,
        skill=SkillLevel.SENIOR,
        ai_time=20.0,
        verify_time=20.0,
        recall=0.5,
        faithfulness=0.5,
        base_latency=10.0,
        fp_rate=1.0,
        resolution_penalty=10.0,
        cra=10.0,
    )
    tvy = APVACalculator.true_value_yield(benchmark)
    assert tvy < 0.0


def test_evaluate_report_fields():
    benchmark = _sample_benchmark(name="rpt")
    report = APVACalculator.evaluate(benchmark)
    assert report.gross_time_saved_min == pytest.approx(27.0)
    assert report.rag_reliability_coefficient == pytest.approx(0.86)
    assert report.true_value_yield_min == pytest.approx((27.0 * 0.86) - 1.0)
    assert report.is_net_positive is True
    assert report.tvy_grade in (TVYGrade.EXCEPTIONAL, TVYGrade.STRONG)
    assert report.benchmark_name == "rpt"


def test_evaluate_with_usd():
    benchmark = _sample_benchmark(name="usd-bench", hourly_rate=120.0)
    report = APVACalculator.evaluate(benchmark)
    assert report.true_value_yield_usd is not None
    assert pytest.approx(report.true_value_yield_usd) == (report.true_value_yield_min / 60.0) * 120.0


# ---------------------------------------------------------------------------
# Skill Level Multipliers (All 5 Tiers)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "skill, expected_mult",
    [
        (SkillLevel.INTERN, 2.0),
        (SkillLevel.JUNIOR, 1.5),
        (SkillLevel.MID, 1.0),
        (SkillLevel.SENIOR, 0.7),
        (SkillLevel.EXPERT, 0.5),
    ],
)
def test_skill_level_multipliers(skill: SkillLevel, expected_mult: float):
    assert skill.baseline_multiplier == expected_mult


def test_skill_validation_rejects_invalid():
    with pytest.raises(ValueError):
        ProductivityMetrics(
            reference_human_baseline_min=60.0,
            skill_level="invalid",  # type: ignore[arg-type]
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


# ---------------------------------------------------------------------------
# TVY Grade Classification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "tvy, expected_grade",
    [
        (35.0, TVYGrade.EXCEPTIONAL),
        (20.0, TVYGrade.STRONG),
        (10.0, TVYGrade.MODERATE),
        (2.0, TVYGrade.MARGINAL),
        (-5.0, TVYGrade.NEGATIVE),
    ],
)
def test_tvy_grade_classification(tvy: float, expected_grade: TVYGrade):
    assert TVYGrade.from_tvy(tvy) == expected_grade


# ---------------------------------------------------------------------------
# Sensitivity Analysis & Monte Carlo
# ---------------------------------------------------------------------------

def test_sensitivity_analysis():
    benchmark = _sample_benchmark(name="sens-bench")
    vectors = APVACalculator.sensitivity_analysis(benchmark, delta_fraction=0.1)
    assert len(vectors) > 0
    # Vectors must be sorted by descending TVY impact
    impacts = [v.tvy_impact for v in vectors]
    assert impacts == sorted(impacts, reverse=True)
    assert all(v.delta > 0 for v in vectors)


def test_confidence_interval():
    benchmark = _sample_benchmark(name="ci-bench")
    ci = APVACalculator.confidence_interval(benchmark, n_simulations=100, seed=42)
    assert ci.lower <= ci.median <= ci.upper
    assert ci.n_simulations == 100
    assert ci.confidence_level == 0.95


# ---------------------------------------------------------------------------
# Batch Evaluation & Comparison
# ---------------------------------------------------------------------------

def test_evaluate_batch():
    b1 = _sample_benchmark(name="b1", baseline=40.0)
    b2 = _sample_benchmark(name="b2", baseline=80.0)
    reports = APVACalculator.evaluate_batch([b1, b2])
    assert len(reports) == 2
    assert reports[0].benchmark_name == "b1"
    assert reports[1].benchmark_name == "b2"


def test_compare_reports():
    b1 = _sample_benchmark(name="low-baseline", baseline=30.0)
    b2 = _sample_benchmark(name="high-baseline", baseline=100.0)
    reports = APVACalculator.evaluate_batch([b1, b2])
    comparison = APVACalculator.compare(reports)
    assert comparison["best"] == "high-baseline"
    assert comparison["worst"] == "low-baseline"
    assert len(comparison["rankings"]) == 2
    assert comparison["tvy_spread_min"] > 0
