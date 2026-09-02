"""Framework-wide constants for the APVA framework.

All magic numbers, version strings, and configuration defaults are
centralised here so that every module references a single source of truth.
"""

from __future__ import annotations

FRAMEWORK_VERSION: str = "3.0.0"
"""Semantic version of the APVA framework — must match ``pyproject.toml``."""

# ---------------------------------------------------------------------------
# RAG Reliability Coefficient weights
# ---------------------------------------------------------------------------
DEFAULT_SPAN_RECALL_WEIGHT: float = 0.60
"""Weight applied to deterministic exact-span recall in the reliability blend."""

DEFAULT_FAITHFULNESS_WEIGHT: float = 0.40
"""Weight applied to LLM-as-judge faithfulness in the reliability blend."""

# ---------------------------------------------------------------------------
# Sensitivity & Monte Carlo defaults
# ---------------------------------------------------------------------------
DEFAULT_CONFIDENCE_LEVEL: float = 0.95
"""Default confidence level for Monte Carlo intervals (95 %)."""

DEFAULT_MONTE_CARLO_SIMULATIONS: int = 1_000
"""Number of Monte Carlo iterations for confidence interval estimation."""

DEFAULT_SENSITIVITY_DELTA: float = 0.05
"""Default perturbation fraction (±5 %) for sensitivity analysis."""

# ---------------------------------------------------------------------------
# TVY Grading thresholds (minutes saved per task)
# ---------------------------------------------------------------------------
TVY_GRADE_THRESHOLDS: dict[str, float] = {
    "exceptional": 30.0,
    "strong": 15.0,
    "moderate": 5.0,
    "marginal": 0.0,
}
"""Mapping from grade label → minimum TVY in minutes.

Grades are evaluated top-down: a TVY of 20.0 min is ``STRONG`` because
it exceeds 15.0 but not 30.0.  Anything below 0.0 is ``NEGATIVE``.
"""

# ---------------------------------------------------------------------------
# CI/CD evaluation defaults
# ---------------------------------------------------------------------------
DEFAULT_EVAL_THRESHOLD: float = 0.85
"""Default exact-span-recall threshold for CI/CD eval gate pass/fail."""

DEFAULT_GOLDEN_SET_PATH: str = "data/golden_dataset.json"
"""Conventional path for the project's golden evaluation dataset."""

# ---------------------------------------------------------------------------
# Rate limiting defaults
# ---------------------------------------------------------------------------
DEFAULT_RATE_LIMIT: int = 100
"""Maximum requests per window per client IP."""

DEFAULT_RATE_WINDOW_SECONDS: int = 60
"""Fixed-window duration in seconds for rate limiting."""

# ---------------------------------------------------------------------------
# SDK defaults
# ---------------------------------------------------------------------------
DEFAULT_SDK_QUEUE_SIZE: int = 2_000
"""Maximum number of telemetry payloads buffered in the SDK queue."""

DEFAULT_SDK_RETRY_ATTEMPTS: int = 3
"""Maximum retry attempts for SDK telemetry HTTP sends."""

DEFAULT_SDK_RETRY_BASE_DELAY: float = 0.1
"""Base delay in seconds for exponential backoff between retries."""

DEFAULT_SDK_BATCH_SIZE: int = 100
"""Maximum events per batch ingestion HTTP call."""
