"""Pydantic data models for the APVA framework.

These models enforce data soundness for every benchmark simulation. All time
values are expressed in **minutes** unless otherwise noted; all rate / score
values are dimensionless fractions in the inclusive range ``[0.0, 1.0]``.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SkillLevel(str, Enum):
    """Skill stratification tier for the human baseline.

    The multiplier expresses how much *longer* a human at this tier takes
    relative to a normalized reference task. Junior practitioners take longer,
    so they produce a higher human baseline and therefore a higher gross time
    saved when the AI performs the same task.

    Attributes:
        JUNIOR: Entry-level practitioner (slowest baseline, highest yield).
        MID: Mid-level practitioner.
        SENIOR: Senior practitioner (fastest baseline, lowest yield).
    """

    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"

    @property
    def baseline_multiplier(self) -> float:
        """Return the time multiplier applied to the reference human baseline.

        Returns:
            float: A multiplier > 1.0 for juniors, 1.0 for mid, < 1.0 for
            seniors, encoding that junior baselines yield higher gross time.
        """
        return {
            SkillLevel.JUNIOR: 1.5,
            SkillLevel.MID: 1.0,
            SkillLevel.SENIOR: 0.7,
        }[self]


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

    model_config = ConfigDict(extra="forbid")

    reference_human_baseline_min: float = Field(..., ge=0.0)
    skill_level: SkillLevel = Field(default=SkillLevel.MID)
    ai_generation_time_min: float = Field(..., ge=0.0)
    epistemic_verification_time_min: float = Field(..., ge=0.0)
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

    model_config = ConfigDict(extra="forbid")

    exact_span_recall: float = Field(..., ge=0.0, le=1.0)
    llm_faithfulness_score: float = Field(..., ge=0.0, le=1.0)


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

    model_config = ConfigDict(extra="forbid")

    base_latency_overhead_min: float = Field(..., ge=0.0)
    false_positive_rate: float = Field(..., ge=0.0, le=1.0)
    resolution_penalty_time_min: float = Field(..., ge=0.0)
    cra_session_drop_penalty_min: float = Field(..., ge=0.0)


class BenchmarkInput(BaseModel):
    """A complete APVA benchmark simulation input.

    Attributes:
        name: Human-readable benchmark identifier.
        productivity: Productivity pillar inputs.
        rag: RAG reliability pillar inputs.
        guardrail: Guardrail tax pillar inputs.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
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


class APVAReport(BaseModel):
    """Structured output of an APVA benchmark computation.

    All time-derived fields are in minutes. ``true_value_yield_min`` may be
    negative when guardrail tax and verification overhead exceed the human
    baseline (i.e. the AI workflow is a net productivity loss).

    Attributes:
        name: Benchmark identifier echoed from the input.
        skill_adjusted_human_baseline_min: Stratified human baseline.
        gross_time_saved_min: Raw time saved before reliability discounting.
        rag_reliability_coefficient: Blended reliability coefficient ``[0,1]``.
        guardrail_friction_tax_min: Total guardrail friction tax in minutes.
        true_value_yield_min: Headline TVY metric (may be negative).
        true_value_yield_usd: Financial ROI metric in USD (if hourly rate provided).
        is_net_positive: Convenience flag, ``True`` iff TVY > 0.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    skill_adjusted_human_baseline_min: float
    gross_time_saved_min: float
    rag_reliability_coefficient: float
    guardrail_friction_tax_min: float
    true_value_yield_min: float
    true_value_yield_usd: float | None = None
    is_net_positive: bool
