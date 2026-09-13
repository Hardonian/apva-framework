"""Enterprise multivariate business-case and portfolio analysis for APVA."""

from __future__ import annotations

import hashlib
import itertools
import json
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apva.calculator import APVACalculator, APVACalculatorConfig
from apva.constants import FRAMEWORK_VERSION
from apva.models import APVAReport, BenchmarkInput, Probability, SensitivityVector

NonNegative = Annotated[float, Field(ge=0.0)]
Positive = Annotated[float, Field(gt=0.0)]
Multiplier = Annotated[float, Field(gt=0.0, le=5.0)]


class DecisionStatus(str, Enum):
    """Recommended enterprise rollout posture."""

    SCALE = "scale"
    CONTROLLED_PILOT = "controlled_pilot"
    OPTIMIZE = "optimize"
    DO_NOT_SCALE = "do_not_scale"


class BusinessCaseAssumptions(BaseModel):
    """Organizational, cost, adoption, and planning-horizon assumptions."""

    model_config = ConfigDict(extra="forbid")

    organization: str = Field(default="Enterprise", min_length=1, max_length=255)
    use_case_owner: str = Field(default="AI Transformation Office", min_length=1, max_length=255)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    practitioners: int = Field(ge=1, le=10_000_000)
    tasks_per_practitioner_per_day: Positive = Field(...)
    working_days_per_year: int = Field(default=230, ge=1, le=366)
    adoption_rate: Probability = Field(default=0.65)
    realization_rate: Probability = Field(default=0.8)
    evidence_confidence: Probability = Field(default=0.75)
    implementation_cost_usd: NonNegative = Field(default=0.0)
    annual_platform_cost_usd: NonNegative = Field(default=0.0)
    variable_ai_cost_per_task_usd: NonNegative = Field(default=0.0)
    annual_risk_avoidance_usd: NonNegative = Field(default=0.0)
    annual_task_growth_rate: float = Field(default=0.0, ge=-0.9, le=5.0)
    analysis_years: int = Field(default=3, ge=1, le=10)
    discount_rate: Probability = Field(default=0.1)


class XFactorInputs(BaseModel):
    """Often-missed causal, knowledge, coordination, tail-risk, and ESG signals.

    These factors are kept separate from canonical TVY to make double counting
    visible during finance and model-risk review.
    """

    model_config = ConfigDict(extra="forbid")

    causal_attribution_confidence: Probability = Field(default=0.7)
    coordination_minutes_saved_per_task: NonNegative = Field(default=0.0)
    reusable_output_rate: Probability = Field(default=0.0)
    expected_reuses_per_output: NonNegative = Field(default=0.0)
    minutes_saved_per_reuse: NonNegative = Field(default=0.0)
    escaped_error_probability: Probability = Field(default=0.0)
    loss_per_escaped_error_usd: NonNegative = Field(default=0.0)
    downstream_blast_radius_multiplier: float = Field(default=1.0, ge=1.0, le=1000.0)
    autonomous_completion_rate: Probability = Field(default=0.0)
    human_override_rate: Probability = Field(default=0.0)
    carbon_grams_co2e_per_task: NonNegative = Field(default=0.0)
    internal_carbon_price_usd_per_tonne: NonNegative = Field(default=0.0)


class DecisionPolicy(BaseModel):
    """Policy-as-code thresholds used to gate pilots and production rollouts."""

    model_config = ConfigDict(extra="forbid")

    minimum_tvy_min: float = Field(default=0.0)
    minimum_rag_reliability: Probability = Field(default=0.8)
    minimum_first_year_roi_pct: float = Field(default=25.0)
    maximum_payback_months: Positive = Field(default=18.0)
    minimum_downside_tvy_min: float = Field(default=0.0)
    minimum_evidence_confidence: Probability = Field(default=0.7)
    maximum_guardrail_tax_min: NonNegative = Field(default=1.0)
    minimum_causal_attribution_confidence: Probability = Field(default=0.6)


class ScenarioMatrix(BaseModel):
    """Bounded multivariate grid for adoption, quality, cost, and volume stress tests."""

    model_config = ConfigDict(extra="forbid")

    adoption_rates: list[Probability] = Field(default_factory=lambda: [0.35, 0.65, 0.9])
    reliability_multipliers: list[Multiplier] = Field(default_factory=lambda: [0.9, 1.0, 1.05])
    cost_multipliers: list[Multiplier] = Field(default_factory=lambda: [0.8, 1.0, 1.2])
    volume_multipliers: list[Multiplier] = Field(default_factory=lambda: [0.75, 1.0, 1.25])

    @model_validator(mode="after")
    def _bounded_matrix(self) -> ScenarioMatrix:
        dimensions = (
            self.adoption_rates,
            self.reliability_multipliers,
            self.cost_multipliers,
            self.volume_multipliers,
        )
        if any(not values for values in dimensions):
            raise ValueError("Every scenario dimension must contain at least one value")
        combinations = 1
        for values in dimensions:
            combinations *= len(values)
        if combinations > 500:
            raise ValueError("Scenario matrix is limited to 500 combinations")
        return self


class EnterpriseAnalysisRequest(BaseModel):
    """Complete request for an auditable enterprise investment analysis."""

    model_config = ConfigDict(extra="forbid")

    benchmark: BenchmarkInput
    business_case: BusinessCaseAssumptions
    x_factors: XFactorInputs = Field(default_factory=XFactorInputs)
    policy: DecisionPolicy = Field(default_factory=DecisionPolicy)
    scenario_matrix: ScenarioMatrix = Field(default_factory=ScenarioMatrix)
    include_scenario_matrix: bool = True
    monte_carlo_simulations: int = Field(default=1000, ge=100, le=10_000)
    uncertainty_fraction: float = Field(default=0.1, gt=0.0, le=0.5)
    confidence_level: float = Field(default=0.95, ge=0.5, lt=1.0)
    random_seed: int | None = None

    @model_validator(mode="after")
    def _financial_input_required(self) -> EnterpriseAnalysisRequest:
        hourly_rate = self.benchmark.productivity.hourly_rate_usd
        if hourly_rate is None or hourly_rate <= 0:
            raise ValueError("Enterprise analysis requires a positive hourly_rate_usd")
        return self


class GateCheck(BaseModel):
    """One explainable policy decision with observed and target values."""

    model_config = ConfigDict(extra="forbid")

    check: str
    label: str
    passed: bool
    actual: float | None
    operator: str
    threshold: float
    unit: str


class AnnualProjection(BaseModel):
    """One discounted annual cash-flow projection."""

    model_config = ConfigDict(extra="forbid")

    year: int
    task_volume: int
    productivity_value_usd: float
    risk_avoidance_usd: float
    operating_cost_usd: float
    net_cash_flow_usd: float
    discounted_cash_flow_usd: float


class OptimizationLever(BaseModel):
    """Ranked model parameter with a quantified recommended direction."""

    model_config = ConfigDict(extra="forbid")

    parameter: str
    direction: str
    current_value: float
    recommended_target: float
    estimated_tvy_gain_min: float
    sensitivity_span_min: float


class ScenarioCell(BaseModel):
    """One point in the multivariate enterprise scenario grid."""

    model_config = ConfigDict(extra="forbid")

    adoption_rate: float
    reliability_multiplier: float
    cost_multiplier: float
    volume_multiplier: float
    task_volume: int
    tvy_min: float
    annual_net_value_usd: float
    first_year_roi_pct: float | None
    decision: DecisionStatus


class EnterpriseBusinessCaseReport(BaseModel):
    """Board-ready, auditable APVA investment decision report."""

    model_config = ConfigDict(extra="forbid")

    report_id: str
    framework_version: str
    organization: str
    use_case: str
    decision: DecisionStatus
    priority_score: float
    benchmark_report: APVAReport
    annual_task_volume: int
    per_task_value_usd: float
    causal_value_yield_per_task_usd: float
    coordination_dividend_per_task_usd: float
    knowledge_dividend_per_task_usd: float
    expected_downstream_loss_per_task_usd: float
    carbon_cost_per_task_usd: float
    x_factor_annual_value_usd: float
    annual_productivity_value_usd: float
    annual_risk_adjusted_value_usd: float
    annual_operating_cost_usd: float
    first_year_net_value_usd: float
    recurring_annual_net_value_usd: float
    first_year_roi_pct: float | None
    payback_months: float | None
    break_even_annual_tasks: int | None
    net_present_value_usd: float
    benefit_cost_ratio: float | None
    monthly_cost_of_delay_usd: float
    downside_tvy_min: float
    upside_tvy_min: float
    probability_negative_tvy: float
    tvy_value_at_risk_5_min: float
    conditional_value_at_risk_5_min: float
    tvy_standard_deviation_min: float
    evidence_confidence: float
    causal_attribution_confidence: float
    enterprise_value_capture_rate: float
    autonomous_completion_rate: float
    human_override_rate: float
    trust_adjusted_autonomy_rate: float
    gate_checks: list[GateCheck]
    top_levers: list[OptimizationLever]
    recommendations: list[str]
    projections: list[AnnualProjection]
    scenario_matrix: list[ScenarioCell]
    positive_scenario_rate: float | None
    audit_trail: dict[str, Any]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PortfolioAnalysisRequest(BaseModel):
    """Multiple business cases competing for an optional investment budget."""

    model_config = ConfigDict(extra="forbid")

    cases: list[EnterpriseAnalysisRequest] = Field(min_length=1, max_length=50)
    investment_budget_usd: float | None = Field(default=None, ge=0.0)

    @model_validator(mode="after")
    def _bounded_work(self) -> PortfolioAnalysisRequest:
        simulations = sum(case.monte_carlo_simulations for case in self.cases)
        if simulations > 50_000:
            raise ValueError("Portfolio analysis is limited to 50,000 Monte Carlo simulations")
        names = [case.benchmark.name for case in self.cases]
        if len(names) != len(set(names)):
            raise ValueError("Portfolio use-case names must be unique")
        return self


class PortfolioRanking(BaseModel):
    """Prioritized portfolio item with funding guidance."""

    model_config = ConfigDict(extra="forbid")

    rank: int
    use_case: str
    decision: DecisionStatus
    priority_score: float
    first_year_net_value_usd: float
    net_present_value_usd: float
    implementation_cost_usd: float
    funded: bool


class PortfolioAnalysisReport(BaseModel):
    """Executive portfolio optimization across multiple AI use cases."""

    model_config = ConfigDict(extra="forbid")

    report_id: str
    framework_version: str
    rankings: list[PortfolioRanking]
    cases: list[EnterpriseBusinessCaseReport]
    total_opportunity_npv_usd: float
    funded_npv_usd: float
    recommended_capital_usd: float
    remaining_budget_usd: float | None
    scale_ready_count: int
    positive_downside_case_rate: float
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class _Economics:
    annual_task_volume: int
    per_task_value_usd: float
    causal_value_yield_per_task_usd: float
    coordination_dividend_per_task_usd: float
    knowledge_dividend_per_task_usd: float
    expected_downstream_loss_per_task_usd: float
    carbon_cost_per_task_usd: float
    annual_productivity_value_usd: float
    annual_operating_cost_usd: float
    first_year_net_value_usd: float
    recurring_annual_net_value_usd: float
    first_year_roi_pct: float | None
    payback_months: float | None
    break_even_annual_tasks: int | None


class EnterpriseValueEngine:
    """Pure enterprise decision engine layered on the canonical APVA formulas."""

    @staticmethod
    def _input_hash(request: EnterpriseAnalysisRequest) -> str:
        serialized = json.dumps(
            request.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(serialized.encode()).hexdigest()

    @staticmethod
    def _economics(
        tvy_min: float,
        hourly_rate_usd: float,
        assumptions: BusinessCaseAssumptions,
        x_factors: XFactorInputs | None = None,
    ) -> _Economics:
        factors = x_factors or XFactorInputs()
        task_volume = round(
            assumptions.practitioners
            * assumptions.tasks_per_practitioner_per_day
            * assumptions.working_days_per_year
            * assumptions.adoption_rate
        )
        raw_realized_value = (tvy_min / 60.0) * hourly_rate_usd * assumptions.realization_rate
        causal_value = raw_realized_value * factors.causal_attribution_confidence
        coordination_dividend = factors.coordination_minutes_saved_per_task / 60.0 * hourly_rate_usd
        knowledge_dividend = (
            factors.reusable_output_rate
            * factors.expected_reuses_per_output
            * factors.minutes_saved_per_reuse
            / 60.0
            * hourly_rate_usd
        )
        expected_downstream_loss = (
            factors.escaped_error_probability
            * factors.loss_per_escaped_error_usd
            * factors.downstream_blast_radius_multiplier
        )
        carbon_cost = (
            factors.carbon_grams_co2e_per_task
            / 1_000_000.0
            * factors.internal_carbon_price_usd_per_tonne
        )
        per_task_value = (
            causal_value
            + coordination_dividend
            + knowledge_dividend
            - expected_downstream_loss
            - carbon_cost
        )
        productivity_value = per_task_value * task_volume
        variable_cost = assumptions.variable_ai_cost_per_task_usd * task_volume
        operating_cost = assumptions.annual_platform_cost_usd + variable_cost
        recurring_net = productivity_value + assumptions.annual_risk_avoidance_usd - operating_cost
        first_year_net = recurring_net - assumptions.implementation_cost_usd
        first_year_cost = assumptions.implementation_cost_usd + operating_cost
        roi = (first_year_net / first_year_cost * 100.0) if first_year_cost > 0 else None
        if assumptions.implementation_cost_usd == 0 and recurring_net > 0:
            payback = 0.0
        elif recurring_net > 0:
            payback = assumptions.implementation_cost_usd / (recurring_net / 12.0)
        else:
            payback = None
        contribution = per_task_value - assumptions.variable_ai_cost_per_task_usd
        fixed_cost = assumptions.implementation_cost_usd + assumptions.annual_platform_cost_usd
        break_even = max(0, round(fixed_cost / contribution)) if contribution > 0 else None
        return _Economics(
            annual_task_volume=task_volume,
            per_task_value_usd=per_task_value,
            causal_value_yield_per_task_usd=causal_value,
            coordination_dividend_per_task_usd=coordination_dividend,
            knowledge_dividend_per_task_usd=knowledge_dividend,
            expected_downstream_loss_per_task_usd=expected_downstream_loss,
            carbon_cost_per_task_usd=carbon_cost,
            annual_productivity_value_usd=productivity_value,
            annual_operating_cost_usd=operating_cost,
            first_year_net_value_usd=first_year_net,
            recurring_annual_net_value_usd=recurring_net,
            first_year_roi_pct=roi,
            payback_months=payback,
            break_even_annual_tasks=break_even,
        )

    @classmethod
    def _projections(
        cls,
        tvy_min: float,
        hourly_rate_usd: float,
        assumptions: BusinessCaseAssumptions,
        x_factors: XFactorInputs,
    ) -> tuple[list[AnnualProjection], float, float | None]:
        projections: list[AnnualProjection] = []
        pv_benefits = 0.0
        pv_costs = assumptions.implementation_cost_usd
        npv = -assumptions.implementation_cost_usd
        base_tasks = (
            assumptions.practitioners
            * assumptions.tasks_per_practitioner_per_day
            * assumptions.working_days_per_year
            * assumptions.adoption_rate
        )
        per_task_value = cls._economics(
            tvy_min, hourly_rate_usd, assumptions, x_factors
        ).per_task_value_usd
        for year in range(1, assumptions.analysis_years + 1):
            task_volume = round(
                base_tasks * (1.0 + assumptions.annual_task_growth_rate) ** (year - 1)
            )
            productivity_value = per_task_value * task_volume
            variable_cost = assumptions.variable_ai_cost_per_task_usd * task_volume
            operating_cost = assumptions.annual_platform_cost_usd + variable_cost
            benefits = productivity_value + assumptions.annual_risk_avoidance_usd
            net_cash_flow = benefits - operating_cost
            discount_factor = (1.0 + assumptions.discount_rate) ** year
            discounted = net_cash_flow / discount_factor
            npv += discounted
            pv_benefits += benefits / discount_factor
            pv_costs += operating_cost / discount_factor
            projections.append(
                AnnualProjection(
                    year=year,
                    task_volume=task_volume,
                    productivity_value_usd=round(productivity_value, 2),
                    risk_avoidance_usd=round(assumptions.annual_risk_avoidance_usd, 2),
                    operating_cost_usd=round(operating_cost, 2),
                    net_cash_flow_usd=round(net_cash_flow, 2),
                    discounted_cash_flow_usd=round(discounted, 2),
                )
            )
        ratio = pv_benefits / pv_costs if pv_costs > 0 else None
        return projections, npv, ratio

    @staticmethod
    def _gate_checks(
        report: APVAReport,
        economics: _Economics,
        assumptions: BusinessCaseAssumptions,
        x_factors: XFactorInputs,
        policy: DecisionPolicy,
    ) -> list[GateCheck]:
        downside = (
            report.confidence_interval.lower
            if report.confidence_interval
            else report.true_value_yield_min
        )
        roi_passed = (
            economics.first_year_roi_pct >= policy.minimum_first_year_roi_pct
            if economics.first_year_roi_pct is not None
            else economics.first_year_net_value_usd > 0
        )
        payback_passed = (
            economics.payback_months is not None
            and economics.payback_months <= policy.maximum_payback_months
        )
        return [
            GateCheck(
                check="tvy",
                label="True Value Yield",
                passed=report.true_value_yield_min >= policy.minimum_tvy_min,
                actual=report.true_value_yield_min,
                operator=">=",
                threshold=policy.minimum_tvy_min,
                unit="minutes/task",
            ),
            GateCheck(
                check="reliability",
                label="RAG Reliability",
                passed=report.rag_reliability_coefficient >= policy.minimum_rag_reliability,
                actual=report.rag_reliability_coefficient,
                operator=">=",
                threshold=policy.minimum_rag_reliability,
                unit="ratio",
            ),
            GateCheck(
                check="roi",
                label="First-year ROI",
                passed=roi_passed,
                actual=economics.first_year_roi_pct,
                operator=">=",
                threshold=policy.minimum_first_year_roi_pct,
                unit="percent",
            ),
            GateCheck(
                check="payback",
                label="Payback Period",
                passed=payback_passed,
                actual=economics.payback_months,
                operator="<=",
                threshold=policy.maximum_payback_months,
                unit="months",
            ),
            GateCheck(
                check="downside",
                label="Downside TVY",
                passed=downside >= policy.minimum_downside_tvy_min,
                actual=downside,
                operator=">=",
                threshold=policy.minimum_downside_tvy_min,
                unit="minutes/task",
            ),
            GateCheck(
                check="evidence",
                label="Evidence Confidence",
                passed=assumptions.evidence_confidence >= policy.minimum_evidence_confidence,
                actual=assumptions.evidence_confidence,
                operator=">=",
                threshold=policy.minimum_evidence_confidence,
                unit="ratio",
            ),
            GateCheck(
                check="guardrail",
                label="Guardrail Friction",
                passed=report.guardrail_friction_tax_min <= policy.maximum_guardrail_tax_min,
                actual=report.guardrail_friction_tax_min,
                operator="<=",
                threshold=policy.maximum_guardrail_tax_min,
                unit="minutes/task",
            ),
            GateCheck(
                check="causality",
                label="Causal Attribution",
                passed=x_factors.causal_attribution_confidence
                >= policy.minimum_causal_attribution_confidence,
                actual=x_factors.causal_attribution_confidence,
                operator=">=",
                threshold=policy.minimum_causal_attribution_confidence,
                unit="ratio",
            ),
        ]

    @staticmethod
    def _decision(
        report: APVAReport,
        economics: _Economics,
        checks: list[GateCheck],
    ) -> DecisionStatus:
        if all(check.passed for check in checks):
            return DecisionStatus.SCALE
        critical = {check.check: check.passed for check in checks}
        if (
            critical["tvy"]
            and critical["reliability"]
            and economics.recurring_annual_net_value_usd > 0
        ):
            return DecisionStatus.CONTROLLED_PILOT
        if report.true_value_yield_min > 0 or economics.recurring_annual_net_value_usd > 0:
            return DecisionStatus.OPTIMIZE
        return DecisionStatus.DO_NOT_SCALE

    @staticmethod
    def _priority_score(
        report: APVAReport,
        economics: _Economics,
        assumptions: BusinessCaseAssumptions,
        x_factors: XFactorInputs,
        checks: list[GateCheck],
    ) -> float:
        gate_score = sum(check.passed for check in checks) / len(checks)
        roi_score = min(1.0, max(0.0, (economics.first_year_roi_pct or 0.0) / 100.0))
        downside = (
            report.confidence_interval.lower
            if report.confidence_interval
            else report.true_value_yield_min
        )
        downside_score = 1.0 if downside >= 0 else 0.0
        payback_score = (
            max(0.0, 1.0 - economics.payback_months / 36.0)
            if economics.payback_months is not None
            else 0.0
        )
        score = (
            gate_score * 30.0
            + roi_score * 15.0
            + report.rag_reliability_coefficient * 15.0
            + assumptions.evidence_confidence * 15.0
            + x_factors.causal_attribution_confidence * 10.0
            + downside_score * 10.0
            + payback_score * 5.0
        )
        return round(min(100.0, score), 1)

    @staticmethod
    def _top_levers(
        sensitivity: list[SensitivityVector], base_tvy: float, limit: int = 5
    ) -> list[OptimizationLever]:
        levers: list[OptimizationLever] = []
        for vector in sensitivity[:limit]:
            increase_is_better = vector.tvy_at_upper >= vector.tvy_at_lower
            target = (
                vector.base_value + vector.delta
                if increase_is_better
                else max(0.0, vector.base_value - vector.delta)
            )
            best_tvy = max(vector.tvy_at_lower, vector.tvy_at_upper)
            levers.append(
                OptimizationLever(
                    parameter=vector.parameter,
                    direction="increase" if increase_is_better else "decrease",
                    current_value=vector.base_value,
                    recommended_target=round(target, 6),
                    estimated_tvy_gain_min=round(max(0.0, best_tvy - base_tvy), 4),
                    sensitivity_span_min=round(vector.tvy_impact, 4),
                )
            )
        return levers

    @classmethod
    def _matrix(
        cls,
        request: EnterpriseAnalysisRequest,
        hourly_rate: float,
        config: APVACalculatorConfig,
    ) -> list[ScenarioCell]:
        cells: list[ScenarioCell] = []
        dimensions = itertools.product(
            request.scenario_matrix.adoption_rates,
            request.scenario_matrix.reliability_multipliers,
            request.scenario_matrix.cost_multipliers,
            request.scenario_matrix.volume_multipliers,
        )
        for adoption, reliability_multiplier, cost_multiplier, volume_multiplier in dimensions:
            benchmark_data = request.benchmark.model_dump()
            rag = benchmark_data["rag"]
            rag["exact_span_recall"] = min(1.0, rag["exact_span_recall"] * reliability_multiplier)
            rag["llm_faithfulness_score"] = min(
                1.0, rag["llm_faithfulness_score"] * reliability_multiplier
            )
            benchmark = BenchmarkInput.model_validate(benchmark_data)
            assumptions = request.business_case.model_copy(
                update={
                    "adoption_rate": adoption,
                    "tasks_per_practitioner_per_day": (
                        request.business_case.tasks_per_practitioner_per_day * volume_multiplier
                    ),
                    "annual_platform_cost_usd": (
                        request.business_case.annual_platform_cost_usd * cost_multiplier
                    ),
                    "variable_ai_cost_per_task_usd": (
                        request.business_case.variable_ai_cost_per_task_usd * cost_multiplier
                    ),
                }
            )
            tvy = APVACalculator.true_value_yield(benchmark, config)
            reliability = APVACalculator.rag_reliability_coefficient(benchmark.rag, config)
            economics = cls._economics(tvy, hourly_rate, assumptions, request.x_factors)
            if (
                tvy >= request.policy.minimum_tvy_min
                and reliability >= request.policy.minimum_rag_reliability
                and economics.first_year_net_value_usd > 0
            ):
                decision = DecisionStatus.SCALE
            elif economics.recurring_annual_net_value_usd > 0:
                decision = DecisionStatus.CONTROLLED_PILOT
            else:
                decision = DecisionStatus.DO_NOT_SCALE
            cells.append(
                ScenarioCell(
                    adoption_rate=adoption,
                    reliability_multiplier=reliability_multiplier,
                    cost_multiplier=cost_multiplier,
                    volume_multiplier=volume_multiplier,
                    task_volume=economics.annual_task_volume,
                    tvy_min=round(tvy, 4),
                    annual_net_value_usd=round(economics.recurring_annual_net_value_usd, 2),
                    first_year_roi_pct=(
                        round(economics.first_year_roi_pct, 2)
                        if economics.first_year_roi_pct is not None
                        else None
                    ),
                    decision=decision,
                )
            )
        return cells

    @classmethod
    def analyze(
        cls,
        request: EnterpriseAnalysisRequest,
        config: APVACalculatorConfig | None = None,
    ) -> EnterpriseBusinessCaseReport:
        """Generate an explainable financial, risk, and governance business case."""
        cfg = config or APVACalculatorConfig()
        input_hash = cls._input_hash(request)
        seed = request.random_seed if request.random_seed is not None else int(input_hash[:16], 16)
        report = APVACalculator.evaluate(
            request.benchmark,
            cfg,
            include_sensitivity=True,
            include_confidence_interval=False,
            n_simulations=request.monte_carlo_simulations,
            sensitivity_delta=request.uncertainty_fraction,
            confidence_level=request.confidence_level,
        )
        # Recompute with a deterministic seed so identical inputs yield identical risk bounds.
        samples = APVACalculator.simulate_tvy(
            request.benchmark,
            cfg,
            n_simulations=request.monte_carlo_simulations,
            noise_pct=request.uncertainty_fraction,
            seed=seed,
        )
        report.confidence_interval = APVACalculator.confidence_interval_from_samples(
            samples, request.confidence_level
        )
        ordered_samples = sorted(samples)
        tail_count = max(1, int(len(ordered_samples) * 0.05))
        value_at_risk = ordered_samples[tail_count - 1]
        conditional_value_at_risk = statistics.mean(ordered_samples[:tail_count])
        probability_negative = sum(sample < 0 for sample in samples) / len(samples)
        standard_deviation = statistics.pstdev(samples) if len(samples) > 1 else 0.0
        hourly_rate = request.benchmark.productivity.hourly_rate_usd
        assert hourly_rate is not None
        economics = cls._economics(
            report.true_value_yield_min,
            hourly_rate,
            request.business_case,
            request.x_factors,
        )
        downside = report.confidence_interval.lower
        downside_economics = cls._economics(
            downside, hourly_rate, request.business_case, request.x_factors
        )
        projections, npv, benefit_cost_ratio = cls._projections(
            report.true_value_yield_min,
            hourly_rate,
            request.business_case,
            request.x_factors,
        )
        checks = cls._gate_checks(
            report,
            economics,
            request.business_case,
            request.x_factors,
            request.policy,
        )
        decision = cls._decision(report, economics, checks)
        levers = cls._top_levers(report.sensitivity, report.true_value_yield_min)
        matrix = cls._matrix(request, hourly_rate, cfg) if request.include_scenario_matrix else []
        positive_scenario_rate = (
            sum(cell.annual_net_value_usd > 0 for cell in matrix) / len(matrix) if matrix else None
        )

        recommendations = [
            (
                "Approve scaled rollout with quarterly evidence recalibration."
                if decision == DecisionStatus.SCALE
                else "Run a controlled pilot and close failed policy gates before scale."
                if decision == DecisionStatus.CONTROLLED_PILOT
                else "Optimize the highest-impact levers before requesting production approval."
                if decision == DecisionStatus.OPTIMIZE
                else "Do not scale under current economics; redesign or retire the use case."
            )
        ]
        for check in checks:
            if not check.passed:
                recommendations.append(
                    f"Close {check.label}: observed {check.actual} {check.unit}; "
                    f"policy requires {check.operator} {check.threshold}."
                )
        if levers:
            top = levers[0]
            recommendations.append(
                f"Prioritize {top.direction} in {top.parameter}; it has the largest modeled "
                f"sensitivity span ({top.sensitivity_span_min:.2f} TVY minutes)."
            )
        if probability_negative > 0.05:
            recommendations.append(
                f"Reduce tail risk: {probability_negative:.1%} of modeled outcomes have negative TVY; "
                f"the worst 5% average {conditional_value_at_risk:.2f} minutes."
            )
        if economics.expected_downstream_loss_per_task_usd > 0:
            recommendations.append(
                "Track escaped-error severity and blast radius as first-class production signals; "
                f"modeled expected loss is ${economics.expected_downstream_loss_per_task_usd:.2f} per task."
            )

        annual_risk_adjusted = downside_economics.recurring_annual_net_value_usd
        return EnterpriseBusinessCaseReport(
            report_id=f"apva-{input_hash[:16]}",
            framework_version=FRAMEWORK_VERSION,
            organization=request.business_case.organization,
            use_case=request.benchmark.name,
            decision=decision,
            priority_score=cls._priority_score(
                report, economics, request.business_case, request.x_factors, checks
            ),
            benchmark_report=report,
            annual_task_volume=economics.annual_task_volume,
            per_task_value_usd=round(economics.per_task_value_usd, 4),
            causal_value_yield_per_task_usd=round(economics.causal_value_yield_per_task_usd, 4),
            coordination_dividend_per_task_usd=round(
                economics.coordination_dividend_per_task_usd, 4
            ),
            knowledge_dividend_per_task_usd=round(economics.knowledge_dividend_per_task_usd, 4),
            expected_downstream_loss_per_task_usd=round(
                economics.expected_downstream_loss_per_task_usd, 4
            ),
            carbon_cost_per_task_usd=round(economics.carbon_cost_per_task_usd, 6),
            x_factor_annual_value_usd=round(
                (
                    economics.per_task_value_usd
                    - (
                        report.true_value_yield_min
                        / 60.0
                        * hourly_rate
                        * request.business_case.realization_rate
                    )
                )
                * economics.annual_task_volume,
                2,
            ),
            annual_productivity_value_usd=round(economics.annual_productivity_value_usd, 2),
            annual_risk_adjusted_value_usd=round(annual_risk_adjusted, 2),
            annual_operating_cost_usd=round(economics.annual_operating_cost_usd, 2),
            first_year_net_value_usd=round(economics.first_year_net_value_usd, 2),
            recurring_annual_net_value_usd=round(economics.recurring_annual_net_value_usd, 2),
            first_year_roi_pct=(
                round(economics.first_year_roi_pct, 2)
                if economics.first_year_roi_pct is not None
                else None
            ),
            payback_months=(
                round(economics.payback_months, 2) if economics.payback_months is not None else None
            ),
            break_even_annual_tasks=economics.break_even_annual_tasks,
            net_present_value_usd=round(npv, 2),
            benefit_cost_ratio=(
                round(benefit_cost_ratio, 3) if benefit_cost_ratio is not None else None
            ),
            monthly_cost_of_delay_usd=round(
                max(0.0, economics.recurring_annual_net_value_usd / 12.0), 2
            ),
            downside_tvy_min=downside,
            upside_tvy_min=report.confidence_interval.upper,
            probability_negative_tvy=round(probability_negative, 4),
            tvy_value_at_risk_5_min=round(value_at_risk, 4),
            conditional_value_at_risk_5_min=round(conditional_value_at_risk, 4),
            tvy_standard_deviation_min=round(standard_deviation, 4),
            evidence_confidence=request.business_case.evidence_confidence,
            causal_attribution_confidence=request.x_factors.causal_attribution_confidence,
            enterprise_value_capture_rate=round(
                request.business_case.adoption_rate
                * request.business_case.realization_rate
                * request.x_factors.causal_attribution_confidence,
                4,
            ),
            autonomous_completion_rate=request.x_factors.autonomous_completion_rate,
            human_override_rate=request.x_factors.human_override_rate,
            trust_adjusted_autonomy_rate=round(
                request.x_factors.autonomous_completion_rate
                * report.rag_reliability_coefficient
                * (1.0 - request.x_factors.human_override_rate),
                4,
            ),
            gate_checks=checks,
            top_levers=levers,
            recommendations=recommendations,
            projections=projections,
            scenario_matrix=matrix,
            positive_scenario_rate=(
                round(positive_scenario_rate, 4) if positive_scenario_rate is not None else None
            ),
            audit_trail={
                "input_sha256": input_hash,
                "random_seed": seed,
                "monte_carlo_simulations": request.monte_carlo_simulations,
                "confidence_level": request.confidence_level,
                "uncertainty_fraction": request.uncertainty_fraction,
                "reliability_weights": {
                    "span_recall": cfg.span_recall_weight,
                    "faithfulness": cfg.faithfulness_weight,
                },
                "formula": "TVY = (gross_time_saved * rag_reliability) - guardrail_tax",
                "enterprise_value_formula": (
                    "causal_TVY + coordination_dividend + knowledge_dividend "
                    "- downstream_expected_loss - carbon_cost - variable_AI_cost"
                ),
                "tail_risk_definition": "CVaR5 = mean TVY in the worst 5% of simulations",
                "currency": request.business_case.currency,
            },
        )

    @classmethod
    def analyze_portfolio(cls, request: PortfolioAnalysisRequest) -> PortfolioAnalysisReport:
        """Rank business cases and allocate an optional implementation budget."""
        reports = [cls.analyze(case) for case in request.cases]
        ordered = sorted(
            zip(request.cases, reports),
            key=lambda item: (
                item[1].decision == DecisionStatus.SCALE,
                item[1].priority_score,
                item[1].net_present_value_usd,
            ),
            reverse=True,
        )
        remaining = request.investment_budget_usd
        rankings: list[PortfolioRanking] = []
        funded_npv = 0.0
        recommended_capital = 0.0
        for rank, (case, report) in enumerate(ordered, start=1):
            cost = case.business_case.implementation_cost_usd
            eligible = report.decision in {
                DecisionStatus.SCALE,
                DecisionStatus.CONTROLLED_PILOT,
            }
            funded = eligible and (remaining is None or cost <= remaining)
            if funded:
                funded_npv += report.net_present_value_usd
                recommended_capital += cost
                if remaining is not None:
                    remaining -= cost
            rankings.append(
                PortfolioRanking(
                    rank=rank,
                    use_case=report.use_case,
                    decision=report.decision,
                    priority_score=report.priority_score,
                    first_year_net_value_usd=report.first_year_net_value_usd,
                    net_present_value_usd=report.net_present_value_usd,
                    implementation_cost_usd=cost,
                    funded=funded,
                )
            )

        portfolio_hash = hashlib.sha256(
            "|".join(report.report_id for report in reports).encode()
        ).hexdigest()
        return PortfolioAnalysisReport(
            report_id=f"apva-portfolio-{portfolio_hash[:16]}",
            framework_version=FRAMEWORK_VERSION,
            rankings=rankings,
            cases=reports,
            total_opportunity_npv_usd=round(
                sum(report.net_present_value_usd for report in reports), 2
            ),
            funded_npv_usd=round(funded_npv, 2),
            recommended_capital_usd=round(recommended_capital, 2),
            remaining_budget_usd=round(remaining, 2) if remaining is not None else None,
            scale_ready_count=sum(report.decision == DecisionStatus.SCALE for report in reports),
            positive_downside_case_rate=round(
                sum(report.downside_tvy_min >= 0 for report in reports) / len(reports), 4
            ),
        )
