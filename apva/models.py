"""Pydantic data models for the APVA framework.

These models enforce data soundness for every benchmark simulation. All time
values are expressed in **minutes** unless otherwise noted; all rate / score
values are dimensionless fractions in the inclusive range ``[0.0, 1.0]``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apva.constants import FRAMEWORK_VERSION, TVY_GRADE_THRESHOLDS

# ---------------------------------------------------------------------------
# Reusable Annotated types — DRY field definitions
# ---------------------------------------------------------------------------

Probability = Annotated[float, Field(ge=0.0, le=1.0)]
"""A probability or fraction clamped to ``[0.0, 1.0]``."""

PositiveMinutes = Annotated[float, Field(ge=0.0)]
"""A non-negative time measurement in minutes."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SkillLevel(str, Enum):
    """Skill stratification tier for the human baseline.

    The multiplier expresses how much *longer* a human at this tier takes
    relative to a normalized reference task. Junior practitioners take longer,
    so they produce a higher human baseline and therefore a higher gross time
    saved when the AI performs the same task.

    Attributes:
        INTERN: Intern / entry-level practitioner (slowest baseline).
        JUNIOR: Junior practitioner.
        MID: Mid-level practitioner (reference baseline).
        SENIOR: Senior practitioner.
        EXPERT: Staff / Principal / Expert-level (fastest baseline).
    """

    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    EXPERT = "expert"

    @property
    def baseline_multiplier(self) -> float:
        """Return the time multiplier applied to the reference human baseline.

        Returns:
            float: A multiplier > 1.0 for juniors, 1.0 for mid, < 1.0 for
            seniors, encoding that junior baselines yield higher gross time.
        """
        return {
            SkillLevel.INTERN: 2.0,
            SkillLevel.JUNIOR: 1.5,
            SkillLevel.MID: 1.0,
            SkillLevel.SENIOR: 0.7,
            SkillLevel.EXPERT: 0.5,
        }[self]


class TVYGrade(str, Enum):
    """Qualitative grading tier for a computed TVY value.

    Grades map to the thresholds defined in :data:`apva.constants.TVY_GRADE_THRESHOLDS`.

    Attributes:
        EXCEPTIONAL: TVY >= 30 min — transformational productivity gain.
        STRONG: TVY >= 15 min — significant, defensible ROI.
        MODERATE: TVY >= 5 min — positive but modest gain.
        MARGINAL: TVY >= 0 min — break-even territory.
        NEGATIVE: TVY < 0 min — net productivity loss.
    """

    EXCEPTIONAL = "exceptional"
    STRONG = "strong"
    MODERATE = "moderate"
    MARGINAL = "marginal"
    NEGATIVE = "negative"

    @classmethod
    def from_tvy(cls, tvy_min: float) -> TVYGrade:
        """Classify a TVY value into the appropriate grade.

        Args:
            tvy_min: True Value Yield in minutes.

        Returns:
            TVYGrade: The corresponding qualitative grade.
        """
        if tvy_min >= TVY_GRADE_THRESHOLDS["exceptional"]:
            return cls.EXCEPTIONAL
        if tvy_min >= TVY_GRADE_THRESHOLDS["strong"]:
            return cls.STRONG
        if tvy_min >= TVY_GRADE_THRESHOLDS["moderate"]:
            return cls.MODERATE
        if tvy_min >= TVY_GRADE_THRESHOLDS["marginal"]:
            return cls.MARGINAL
        return cls.NEGATIVE


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class ProductivityMetrics(BaseModel):
    """Inputs governing the productivity pillar.

    Attributes:
        reference_human_baseline_min: Time (minutes) a *mid-level* reference
            human takes to complete the task unaided. Must be >= 0.
        skill_level: Skill tier used to stratify the human baseline.
        ai_generation_time_min: Wall-clock time (minutes) the AI system takes
            to generate the deliverable. Must be >= 0.
        epistemic_verification_time_min: Cognitive-load time (minutes) a human
            spends verifying / correcting the AI output. Must be >= 0.
        hourly_rate_usd: Optional dynamic hourly rate of the practitioner to
            compute financial ROI in USD. Must be >= 0.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    reference_human_baseline_min: PositiveMinutes = Field(...)
    skill_level: SkillLevel = Field(default=SkillLevel.MID)
    ai_generation_time_min: PositiveMinutes = Field(...)
    epistemic_verification_time_min: PositiveMinutes = Field(...)
    hourly_rate_usd: float | None = Field(default=None, ge=0.0)

    @property
    def skill_adjusted_human_baseline_min(self) -> float:
        """Compute the skill-stratified human baseline.

        Returns:
            float: ``reference_human_baseline_min`` scaled by the skill
            multiplier (juniors > mid > seniors).
        """
        return self.reference_human_baseline_min * self.skill_level.baseline_multiplier


class RAGMetrics(BaseModel):
    """Inputs governing the RAG reliability pillar.

    Attributes:
        exact_span_recall: Deterministic fraction ``[0,1]`` of required
            evidence spans exactly recalled by retrieval.
        llm_faithfulness_score: LLM-as-judge faithfulness score ``[0,1]``
            measuring how grounded the generation is in retrieved context.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    exact_span_recall: Probability = Field(...)
    llm_faithfulness_score: Probability = Field(...)


class GuardrailMetrics(BaseModel):
    """Inputs governing the guardrail tax pillar.

    Attributes:
        base_latency_overhead_min: Fixed latency (minutes) added per task by
            the guardrail layer. Must be >= 0.
        false_positive_rate: Fraction ``[0,1]`` of benign requests wrongly
            flagged by guardrails.
        resolution_penalty_time_min: Human time (minutes) spent resolving a
            single false positive. Must be >= 0.
        cra_session_drop_penalty_min: Conversational Risk Accumulation penalty
            (minutes) charged when a session must be dropped / restarted due to
            accumulated risk. Must be >= 0.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    base_latency_overhead_min: PositiveMinutes = Field(...)
    false_positive_rate: Probability = Field(...)
    resolution_penalty_time_min: PositiveMinutes = Field(...)
    cra_session_drop_penalty_min: PositiveMinutes = Field(...)


class BenchmarkInput(BaseModel):
    """A complete APVA benchmark simulation input.

    Attributes:
        name: Human-readable benchmark identifier.
        description: Optional longer description for audit trails.
        tags: Optional classification tags for filtering and grouping.
        productivity: Productivity pillar inputs.
        rag: RAG reliability pillar inputs.
        guardrail: Guardrail tax pillar inputs.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    tags: list[str] = Field(default_factory=list)
    productivity: ProductivityMetrics
    rag: RAGMetrics
    guardrail: GuardrailMetrics

    @model_validator(mode="after")
    def _non_empty_name(self) -> "BenchmarkInput":
        """Validate that the benchmark name is not whitespace-only.

        Returns:
            BenchmarkInput: The validated instance.

        Raises:
            ValueError: If ``name`` is whitespace-only.
        """
        if not self.name.strip():
            raise ValueError("Benchmark name must not be empty or whitespace.")
        return self


# ---------------------------------------------------------------------------
# Output / analysis models
# ---------------------------------------------------------------------------


class SensitivityVector(BaseModel):
    """Impact of perturbing a single input parameter on TVY.

    Attributes:
        parameter: Dotted path of the perturbed parameter.
        base_value: Original parameter value.
        delta: Perturbation amount (absolute).
        tvy_at_lower: TVY when parameter is ``base_value - delta``.
        tvy_at_upper: TVY when parameter is ``base_value + delta``.
        tvy_impact: Absolute change in TVY ``|upper - lower|``.
    """

    model_config = ConfigDict(extra="forbid")

    parameter: str
    base_value: float
    delta: float
    tvy_at_lower: float
    tvy_at_upper: float
    tvy_impact: float


class ConfidenceInterval(BaseModel):
    """Monte Carlo derived confidence interval for TVY.

    Attributes:
        lower: Lower bound of the interval.
        median: Median (50th percentile) TVY.
        upper: Upper bound of the interval.
        confidence_level: Confidence level (e.g. 0.95 for 95%).
        n_simulations: Number of Monte Carlo iterations used.
    """

    model_config = ConfigDict(extra="forbid")

    lower: float
    median: float
    upper: float
    confidence_level: float = Field(ge=0.0, le=1.0)
    n_simulations: int = Field(ge=1)


class APVAReport(BaseModel):
    """Structured output of an APVA benchmark computation.

    All time-derived fields are in minutes. ``true_value_yield_min`` may be
    negative when guardrail tax and verification overhead exceed the human
    baseline (i.e. the AI workflow is a net productivity loss).

    Attributes:
        benchmark_name: Benchmark identifier echoed from the input.
        skill_adjusted_human_baseline_min: Stratified human baseline.
        gross_time_saved_min: Raw time saved before reliability discounting.
        rag_reliability_coefficient: Blended reliability coefficient ``[0,1]``.
        guardrail_friction_tax_min: Total guardrail friction tax in minutes.
        true_value_yield_min: Headline TVY metric (may be negative).
        true_value_yield_usd: Financial ROI metric in USD (if hourly rate provided).
        is_net_positive: Convenience flag, ``True`` iff TVY > 0.
        tvy_grade: Qualitative grade based on TVY value.
        sensitivity: Optional per-parameter sensitivity analysis results.
        confidence_interval: Optional Monte Carlo confidence interval.
        computed_at: UTC timestamp when the report was generated.
        framework_version: APVA framework version that produced the report.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    # --- Legacy fields (preserved for backward compatibility) ---
    # The 'name' alias ensures old consumers that read `report.name` still work.
    benchmark_name: str = Field(..., alias="name")

    skill_adjusted_human_baseline_min: float
    gross_time_saved_min: float
    rag_reliability_coefficient: float
    guardrail_friction_tax_min: float
    true_value_yield_min: float
    true_value_yield_usd: float | None = None
    is_net_positive: bool

    # --- New v3 fields ---
    tvy_grade: TVYGrade = Field(default=TVYGrade.MARGINAL)
    sensitivity: list[SensitivityVector] = Field(default_factory=list)
    confidence_interval: ConfidenceInterval | None = Field(default=None)
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    framework_version: str = Field(default=FRAMEWORK_VERSION)
