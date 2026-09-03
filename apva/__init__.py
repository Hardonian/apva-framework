"""APVA — AI Productivity & Value Assurance Framework.

The ``apva`` package is the core engine for computing True Value Yield (TVY):
the single metric that captures the real enterprise ROI of Generative AI by
combining Productivity, RAG Reliability, and Guardrail Friction into a
time-denominated value.

Quick start::

    from apva.calculator import APVACalculator
    from apva.models import BenchmarkInput

    benchmark = BenchmarkInput(name="demo", ...)
    report = APVACalculator.evaluate(benchmark)
    print(report.true_value_yield_min)
"""

from __future__ import annotations

from apva.constants import FRAMEWORK_VERSION

__version__: str = FRAMEWORK_VERSION

from apva.calculator import APVACalculator, APVACalculatorConfig, compute_tvy
from apva.exceptions import (
    APVAAuthenticationError,
    APVACalculationError,
    APVAConfigurationError,
    APVAError,
    APVANetworkError,
    APVARateLimitError,
    APVAValidationError,
)
from apva.models import (
    APVAReport,
    BenchmarkInput,
    ConfidenceInterval,
    GuardrailMetrics,
    PositiveMinutes,
    Probability,
    ProductivityMetrics,
    RAGMetrics,
    SensitivityVector,
    SkillLevel,
    TVYGrade,
)

__all__ = [
    # Version
    "__version__",
    # Calculator
    "APVACalculator",
    "APVACalculatorConfig",
    "compute_tvy",
    # Models
    "APVAReport",
    "BenchmarkInput",
    "ConfidenceInterval",
    "GuardrailMetrics",
    "PositiveMinutes",
    "Probability",
    "ProductivityMetrics",
    "RAGMetrics",
    "SensitivityVector",
    "SkillLevel",
    "TVYGrade",
    # Exceptions
    "APVAAuthenticationError",
    "APVACalculationError",
    "APVAConfigurationError",
    "APVAError",
    "APVANetworkError",
    "APVARateLimitError",
    "APVAValidationError",
]
