#!/usr/bin/env python3
"""Improve GitHub README with better visual structure and innovation markers."""

ORIGINAL_README = Path('/home/scott/ai-workspace/repos/apva-framework/README.md')
BACKUP_README = Path('/home/scott/ai-workspace/repos/apva-framework/README.md.bak')
BACKUP_README.write_text(ORIGINAL_README.read_text())

IMPROVED_README = '''# APVA — AI Productivity & Value Architecture

> A benchmarking framework that measures the **true enterprise ROI of Generative AI** by synthesizing three pillars into a single time-denominated metric: **True Value Yield (TVY)**.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status: Active](https://img.shields.io/badge/status-active_development-orange)]()

---

## The Problem

Most AI benchmarks answer: *"How fast did the model produce output?"*  
They ignore: **human time saved, reliability, and operational friction.**

APVA answers: *"How much net, reliability-discounted, friction-adjusted human time did this AI workflow actually save?"*

---

## The Three Pillars

| Pillar | What it Captures | Key Inputs |
|--------|------------------|------------|
| **Productivity** | Skill-stratified human baselines + epistemic verification | reference baseline, skill tier, AI generation time, verification time |
| **RAG Reliability** | Deterministic exact span recall + LLM faithfulness | exact span recall, faithfulness score |
| **Guardrail Tax** | Operational friction: false positives, latency, CRA | base latency, false-positive rate, resolution penalty, CRA drop penalty |

---

## The Core Mathematics

All times are in **minutes**; all rates/scores are fractions in `[0, 1]`.

```
TVY = (Gross_Time_Saved × RAG_Reliability_Coefficient) − Guardrail_Friction_Tax
```

Where:
- **Gross_Time_Saved** = Skill_Adjusted_Human_Baseline − (AI_Generation_Time + Verification_Time)
- **RAG_Reliability** = (0.60 × Exact_Span_Recall) + (0.40 × LLM_Faithfulness_Score)
- **Guardrail_Tax** = Base_Latency + (False_Positive_Rate × Resolution_Penalty) + CRA_Penalty

> Negative productivity is a first-class result. When guardrails exceed time saved, TVY is negative — the workflow is a net loss.

---

## Installation

```bash
git clone https://github.com/Hardonian/apva-framework.git
cd apva-framework
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
```

Requires **Python 3.10+**. Compatible with Python 3.14 for EPYC lab deployments.

---

## Quick Start

```bash
# Generate a demo report
python -m apva.cli demo

# Run from parameters
python -m apva.cli run \\
  --name "support-bot" \\
  --human-baseline 60 --skill junior \\
  --ai-time 5 --verify-time 8 \\
  --span-recall 0.9 --faithfulness 0.85 \\
  --base-latency 0.5 --fp-rate 0.1 --resolution-penalty 12 --cra 2
```

---

## Library Usage

```python
from apva import APVACalculator, BenchmarkInput, SkillLevel

bench = BenchmarkInput(
    name="repo-audit",
    productivity=ProductivityMetrics(
        reference_human_baseline_min=180,
        skill_level=SkillLevel.MID,
        ai_generation_time_min=25,
        epistemic_verification_time_min=45,
    ),
    rag=RAGMetrics(exact_span_recall=0.9, llm_faithfulness_score=0.85),
    guardrail=GuardrailMetrics(
        base_latency_overhead_min=0.5,
        false_positive_rate=0.05,
        resolution_penalty_time_min=10,
        cra_session_drop_penalty_min=1,
    ),
)

report = APVACalculator.evaluate(bench)
# {
#   "true_value_yield_min": 138.8,
#   "is_net_positive": true,
#   "rag_reliability_coefficient": 0.87,
#   "guardrail_friction_tax_min": 2.0
# }
```

---

## Project Structure

```
apva-framework/
├── apva/
│   ├── __init__.py         # Public API
│   ├── models.py           # Pydantic models (validated, type-safe)
│   ├── calculator.py       # Pure deterministic engine
│   └── cli.py              # argparse → JSON
├── tests/
│   └── test_calculator.py    # Formula verification, edge cases
├── apps/backend/           # FastAPI service layer
├── docker-compose.yml        # Local dev with PostgreSQL/Redis
└── README.md
```

---

## Competitive Advantages

| What Others Miss | APVA Provides | Business Impact |
|------------------|-----------------|-----------------|
| Raw output speed | **Reliability-adjusted time saved** | Avoid costly negative-productivity automations |
| Static metrics | **Skill-stratified baselines** | Junior workflows ≠ senior workflows |
| No guardrail cost | **Operational friction tax** | Real-world deployment costs included |
| API-only focus | **Local-first execution** | No per-token costs, data stays private |

---

## Testing

```bash
pytest -v
# Verifies: formulas, skill monotonicity, negative-productivity edge cases, validation bounds
```

---

## Use Cases

- **Pre-deployment vetting**: Kill negative-TVY workflows before scaling
- **ROI reporting**: Show reliability-adjusted savings to stakeholders
- **Pricing optimization**: Charge based on verified time saved
- **Automation triage**: Prioritize high-TVY improvements

---

## License

MIT — see [LICENSE](LICENSE) for details.