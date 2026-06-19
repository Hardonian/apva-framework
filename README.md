# APVA — AI Productivity & Value Architecture

> A benchmarking framework that measures the **true enterprise ROI of Generative AI** by synthesizing three pillars into a single time-denominated metric: **True Value Yield (TVY)**.

APVA moves beyond "raw output" benchmarks. Instead of asking *"how fast did the model produce text?"*, it asks *"how much net, reliability-discounted, friction-adjusted human time did this AI workflow actually save?"*

---

## The Three Pillars

| Pillar | What it captures | Key inputs |
|--------|------------------|------------|
| **Productivity** | Skill-stratified human baselines + epistemic verification (cognitive load) | reference baseline, skill tier, AI generation time, verification time |
| **RAG Reliability** | Deterministic *exact span recall* blended with theoretical *LLM-as-judge faithfulness* | exact span recall, faithfulness score |
| **Guardrail Tax** | Operational friction: false positives, latency, and Conversational Risk Accumulation (CRA) | base latency, false-positive rate, resolution penalty, CRA drop penalty |

---

## The Core Mathematics

All times are in **minutes**; all rates/scores are fractions in `[0, 1]`.

**True Value Yield (TVY)**
```
TVY = (Gross_Time_Saved * RAG_Reliability_Coefficient) - Guardrail_Friction_Tax
```

**Gross Time Saved (skill stratified)**
```
Gross_Time_Saved = Skill_Adjusted_Human_Baseline - (AI_Generation_Time + Epistemic_Verification_Time)
```
Junior baselines are scaled **up** (×1.5), seniors **down** (×0.7), so junior workflows yield higher gross time saved.

**RAG Reliability Coefficient**
```
RAG_Reliability = (0.60 * Exact_Span_Recall) + (0.40 * LLM_Faithfulness_Score)
```

**Guardrail Friction Tax**
```
Guardrail_Tax = Base_Latency_Overhead + (False_Positive_Rate * Resolution_Penalty_Time) + CRA_Session_Drop_Penalty
```

> **Negative productivity is a first-class result.** When verification overhead and guardrail tax exceed the human baseline, TVY is negative — the AI workflow is a net loss. APVA reports this faithfully rather than clamping to zero.

---

## Installation

```bash
git clone https://github.com/<your-username>/apva-framework.git
cd apva-framework

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Python **3.10+** is required.

---

## Usage

### 1. Run the built-in demo

```bash
python -m apva.cli demo
```

### 2. Run from explicit parameters

```bash
python -m apva.cli run \
  --name "support-bot" \
  --human-baseline 60 --skill junior \
  --ai-time 5 --verify-time 8 \
  --span-recall 0.9 --faithfulness 0.85 \
  --base-latency 0.5 --fp-rate 0.1 --resolution-penalty 12 --cra 2
```

Skill tiers: `junior`, `mid`, `senior`.

### 3. Run from a JSON file

```json
{
  "name": "doc-summarizer",
  "productivity": {
    "reference_human_baseline_min": 45,
    "skill_level": "mid",
    "ai_generation_time_min": 3,
    "epistemic_verification_time_min": 6
  },
  "rag": { "exact_span_recall": 0.88, "llm_faithfulness_score": 0.82 },
  "guardrail": {
    "base_latency_overhead_min": 0.4,
    "false_positive_rate": 0.05,
    "resolution_penalty_time_min": 10,
    "cra_session_drop_penalty_min": 1.5
  }
}
```

```bash
python -m apva.cli run-file benchmark.json
```

### Example output

```json
{
  "name": "demo-enterprise-support",
  "skill_adjusted_human_baseline_min": 90.0,
  "gross_time_saved_min": 77.0,
  "rag_reliability_coefficient": 0.904,
  "guardrail_friction_tax_min": 3.7,
  "true_value_yield_min": 65.908,
  "is_net_positive": true
}
```

Write to a file with `-o report.json`.

---

## Using APVA as a Library

```python
from apva import (
    APVACalculator, BenchmarkInput, ProductivityMetrics,
    RAGMetrics, GuardrailMetrics, SkillLevel,
)

bench = BenchmarkInput(
    name="my-eval",
    productivity=ProductivityMetrics(
        reference_human_baseline_min=60,
        skill_level=SkillLevel.JUNIOR,
        ai_generation_time_min=5,
        epistemic_verification_time_min=8,
    ),
    rag=RAGMetrics(exact_span_recall=0.9, llm_faithfulness_score=0.85),
    guardrail=GuardrailMetrics(
        base_latency_overhead_min=0.5,
        false_positive_rate=0.1,
        resolution_penalty_time_min=12,
        cra_session_drop_penalty_min=2,
    ),
)

report = APVACalculator.evaluate(bench)
print(report.true_value_yield_min)
```

---

## Testing

```bash
pip install -r requirements.txt
pytest -v
```

The suite verifies every formula to floating-point precision, the skill-stratification monotonicity property (`junior > mid > senior`), Pydantic validation bounds, and the critical **negative-productivity** edge case.

---

## Project Structure

```
apva-framework/
├── apva/
│   ├── __init__.py        # Public API exports
│   ├── models.py          # Pydantic models (validated, type-safe inputs/outputs)
│   ├── calculator.py      # The mathematical engine (pure, deterministic)
│   └── cli.py             # argparse CLI -> JSON report
├── tests/
│   └── test_calculator.py # Exhaustive unit tests
├── requirements.txt
├── README.md
├── .gitignore
└── publish.sh             # Automated git + gh push
```

---

## License

MIT. See repository for details.
