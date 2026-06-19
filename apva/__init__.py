"""APVA: AI Productivity & Value Architecture.

A benchmarking framework that measures the true enterprise ROI of Generative AI
by synthesizing three pillars:

1. Productivity  - Skill-stratified human baselines + epistemic verification.
2. RAG Reliability - Deterministic span recall + LLM-as-judge faithfulness.
3. Guardrail Tax - False positives, latency, and Conversational Risk Accumulation.

The headline metric is True Value Yield (TVY), expressed in time units (minutes).
"""

from apva.calculator import APVACalculator, compute_tvy
from apva.models import (
    APVAReport,
    BenchmarkInput,
    GuardrailMetrics,
    ProductivityMetrics,
    RAGMetrics,
    SkillLevel,
)

__all__ = [
    "APVACalculator",
    "compute_tvy",
    "APVAReport",
    "BenchmarkInput",
    "GuardrailMetrics",
    "ProductivityMetrics",
    "RAGMetrics",
    "SkillLevel",
]

__version__ = "0.1.0"
