"""Unit tests for the APVA mathematical engine.

These tests verify the four core formulas to floating-point precision,
exercise the skill-stratification monotonicity property, and cover the
critical negative-productivity edge case where guardrail tax plus verification
overhead exceed the human baseline.
"""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from apva.calculator import APVACalculator, compute_tvy
from apva.models import (
    BenchmarkInput,
    GuardrailMetrics,
    ProductivityMetrics,
    RAGMetrics,
    SkillLevel,
)

REL_TOL = 1e-9


def _benchmark(
    *,
    name: str = "unit-test",
    baseline: float = 60.0,
    skill: SkillLevel = SkillLevel.MID,
    ai_time: float = 5.0,
    verify_time: float = 5.0,
    span_recall: float = 0.9,
    faithfulness: float = 0.8,
    base_latency: float = 1.0,
    fp_rate: float = 0.1,
    resolution_penalty: float = 10.0,
    cra: float = 0.0,
) -> BenchmarkInput:
    """Build a BenchmarkInput with overridable defaults for concise tests."""
    return BenchmarkInput(
        name=name,
        productivity=ProductivityMetrics(
            reference_human_baseline_min=baseline,
            skill_level=skill,
            ai_generation_time_min=ai_time,
            epistemic_verification_time_min=verify_time,
        ),
        rag=RAGMetrics(
            exact_span_recall=span_recall,
            llm_faithfulness_score=faithfulness,
        ),
        guardrail=GuardrailMetrics(
            base_latency_overhead_min=base_latency,
            false_positive_rate=fp_rate,
            resolution_penalty_time_min=resolution_penalty,
            cra_session_drop_penalty_min=cra,
        ),
    )


def test_rag_reliability_coefficient_blend() -> None:
    """RAG reliability must be the 0.60/0.40 convex blend."""
    rag = RAGMetrics(exact_span_recall=0.9, llm_faithfulness_score=0.8)
    expected = 0.60 * 0.9 + 0.40 * 0.8  # 0.86
    assert math.isclose(
        APVACalculator.rag_reliability_coefficient(rag), expected, rel_tol=REL_TOL
    )


def test_rag_reliability_bounds() -> None:
    """Reliability is 1.0 at perfect inputs and 0.0 at zero inputs."""
    perfect = RAGMetrics(exact_span_recall=1.0, llm_faithfulness_score=1.0)
    zero = RAGMetrics(exact_span_recall=0.0, llm_faithfulness_score=0.0)
    assert math.isclose(
        APVACalculator.rag_reliability_coefficient(perfect), 1.0, rel_tol=REL_TOL
    )
    assert math.isclose(
        APVACalculator.rag_reliability_coefficient(zero), 0.0, rel_tol=REL_TOL
    )


def test_guardrail_friction_tax() -> None:
    """Guardrail tax = base + (fp_rate * resolution) + CRA."""
    guard = GuardrailMetrics(
        base_latency_overhead_min=1.0,
        false_positive_rate=0.1,
        resolution_penalty_time_min=10.0,
        cra_session_drop_penalty_min=2.0,
    )
    expected = 1.0 + (0.1 * 10.0) + 2.0  # 4.0
    assert math.isclose(
        APVACalculator.guardrail_friction_tax(guard), expected, rel_tol=REL_TOL
    )


def test_gross_time_saved_mid_level() -> None:
    """Gross time saved at mid skill = baseline - (ai + verify)."""
    prod = ProductivityMetrics(
        reference_human_baseline_min=60.0,
        skill_level=SkillLevel.MID,
        ai_generation_time_min=5.0,
        epistemic_verification_time_min=5.0,
    )
    assert math.isclose(
        APVACalculator.gross_time_saved(prod), 50.0, rel_tol=REL_TOL
    )


def test_skill_stratification_monotonicity() -> None:
    """Junior baselines must yield strictly more gross time than seniors.

    With identical AI + verification times, the ordering must be
    junior > mid > senior.
    """
    junior = APVACalculator.gross_time_saved(
        _benchmark(skill=SkillLevel.JUNIOR).productivity
    )
    mid = APVACalculator.gross_time_saved(
        _benchmark(skill=SkillLevel.MID).productivity
    )
    senior = APVACalculator.gross_time_saved(
        _benchmark(skill=SkillLevel.SENIOR).productivity
    )
    assert junior > mid > senior


def test_tvy_full_formula() -> None:
    """End-to-end TVY must match a hand-computed value exactly.

    baseline (mid) = 60, ai+verify = 10  -> gross = 50
    reliability = 0.60*0.9 + 0.40*0.8 = 0.86
    tax = 1 + 0.1*10 + 0 = 2.0
    TVY = 50 * 0.86 - 2.0 = 41.0
    """
    bench = _benchmark()
    assert math.isclose(compute_tvy(bench), 41.0, rel_tol=REL_TOL)
    report = APVACalculator.evaluate(bench)
    assert math.isclose(report.true_value_yield_min, 41.0, rel_tol=REL_TOL)
    assert report.is_net_positive is True


def test_negative_productivity_edge_case() -> None:
    """When AI + verification + tax exceed the baseline, TVY must be negative.

    baseline (mid) = 10, ai+verify = 9 -> gross = 1
    reliability = 0.60*0.5 + 0.40*0.5 = 0.5
    tax = 5 + 0.5*10 + 3 = 13.0
    TVY = 1 * 0.5 - 13.0 = -12.5
    """
    bench = _benchmark(
        baseline=10.0,
        skill=SkillLevel.MID,
        ai_time=4.0,
        verify_time=5.0,
        span_recall=0.5,
        faithfulness=0.5,
        base_latency=5.0,
        fp_rate=0.5,
        resolution_penalty=10.0,
        cra=3.0,
    )
    report = APVACalculator.evaluate(bench)
    assert math.isclose(report.true_value_yield_min, -12.5, rel_tol=REL_TOL)
    assert report.is_net_positive is False


def test_negative_gross_time_saved() -> None:
    """Gross time saved itself can be negative (AI slower than human)."""
    prod = ProductivityMetrics(
        reference_human_baseline_min=5.0,
        skill_level=SkillLevel.SENIOR,  # 5 * 0.7 = 3.5 baseline
        ai_generation_time_min=10.0,
        epistemic_verification_time_min=5.0,
    )
    # 3.5 - (10 + 5) = -11.5
    assert math.isclose(
        APVACalculator.gross_time_saved(prod), -11.5, rel_tol=REL_TOL
    )


def test_report_fields_consistency() -> None:
    """The report must echo every intermediate metric consistently."""
    bench = _benchmark()
    report = APVACalculator.evaluate(bench)
    assert report.name == "unit-test"
    assert math.isclose(
        report.skill_adjusted_human_baseline_min, 60.0, rel_tol=REL_TOL
    )
    assert math.isclose(report.gross_time_saved_min, 50.0, rel_tol=REL_TOL)
    assert math.isclose(
        report.rag_reliability_coefficient, 0.86, rel_tol=REL_TOL
    )
    assert math.isclose(report.guardrail_friction_tax_min, 2.0, rel_tol=REL_TOL)


@pytest.mark.parametrize(
    "field,value",
    [
        ("exact_span_recall", 1.5),
        ("exact_span_recall", -0.1),
        ("llm_faithfulness_score", 2.0),
        ("llm_faithfulness_score", -1.0),
    ],
)
def test_rag_validation_rejects_out_of_range(field: str, value: float) -> None:
    """RAG scores outside [0,1] must raise a validation error."""
    kwargs = {"exact_span_recall": 0.5, "llm_faithfulness_score": 0.5}
    kwargs[field] = value
    with pytest.raises(ValidationError):
        RAGMetrics(**kwargs)


def test_negative_time_inputs_rejected() -> None:
    """Negative time inputs must be rejected by validation."""
    with pytest.raises(ValidationError):
        ProductivityMetrics(
            reference_human_baseline_min=-1.0,
            ai_generation_time_min=1.0,
            epistemic_verification_time_min=1.0,
        )


def test_empty_name_rejected() -> None:
    """Whitespace-only benchmark names must be rejected."""
    with pytest.raises(ValidationError):
        _benchmark(name="   ")


def test_skill_level_multipliers() -> None:
    """Skill multipliers must encode junior > mid > senior."""
    assert SkillLevel.JUNIOR.baseline_multiplier > SkillLevel.MID.baseline_multiplier
    assert SkillLevel.MID.baseline_multiplier > SkillLevel.SENIOR.baseline_multiplier
