# APVA Enterprise Adoption Playbook

APVA gives engineering, finance, security, procurement, and executive sponsors
one shared decision record for an AI workflow. It connects technical quality to
realized labor value and then subjects the result to explicit rollout policy.

## What each stakeholder receives

| Stakeholder | Decision evidence |
|---|---|
| Executive sponsor | First-year net value, recurring value, NPV, payback, cost of delay, and rollout posture |
| Finance / FinOps | Adoption-adjusted task volume, fixed and variable costs, realization rate, break-even volume, and benefit-cost ratio |
| Model governance | Reliability, downside TVY, evidence confidence, deterministic simulation seed, policy checks, and audit hash |
| Engineering | Ranked sensitivity levers, guardrail friction, runtime latency, cache behavior, and deployment gate output |
| Security / compliance | Tenant isolation, PII redaction policy, signed access, bounded inputs, exportable evidence, and immutable formula version |
| Procurement | Comparable portfolio ranking and capital allocation across candidate vendors or use cases |

## The APVA value-integrity scorecard

The highest-value signals are commonly omitted because they cross team
boundaries: observability owns runtime data, finance owns value, operations owns
workflow outcomes, and risk owns failures. APVA keeps them in one explainable
calculation without collapsing them into a black-box score.

| KPI | Formula | Minimum source data | Collection pattern |
|---|---|---|---|
| Causal Value Yield | `raw TVY value × realization × causal confidence` | treatment/control outcomes, cohort assignment, sample size | randomized holdout when possible; matched pre/post or difference-in-differences otherwise |
| Enterprise Value Capture | `adoption × realization × causal confidence` | eligible users, active users, observed capacity conversion | identity-aware workflow events joined to operational outcomes |
| Coordination Dividend | `coordination minutes removed × labor rate` | handoff timestamps, queue time, search time, meeting load | process-mining events before and after rollout |
| Knowledge Compounding Dividend | `reusable-output rate × reuses × minutes/reuse × labor rate` | artifact ID, producer, consumers, reuse count, avoided work | stable artifact lineage across tickets, documents, code, and decisions |
| Downstream Expected Loss | `escape probability × loss severity × blast radius` | correction/reversal events, affected records/users, recovery cost | delayed outcome joins; do not stop measurement at model response time |
| Trust-Adjusted Autonomy | `autonomous completion × reliability × (1 − override)` | autonomy mode, approval/override event, grounded quality | emit explicit delegation and human-intervention outcomes |
| Tail-Value Risk | `P(TVY < 0)`, `VaR5`, `CVaR5` | input distributions and reproducible simulation seed | use observed distributions once sample sizes support them |
| Carbon-Adjusted Cost | `grams CO2e/task ÷ 1,000,000 × internal $/tonne` | model/region energy estimate and task count | version the emissions factor alongside model and infrastructure |

Three rules keep these metrics credible:

1. Do not self-assign high causal confidence for a scale decision. Tie it to an
   experiment design, a dated evidence window, and a cohort/sample record.
2. Count coordination or reuse value only when it is incremental to the human
   baseline. A saved minute belongs in one component, never two.
3. Join delayed harm, reversal, and reuse events back to the originating run.
   Immediate response telemetry alone cannot measure downstream value integrity.

The enterprise per-task value envelope is:

```text
causal TVY value
+ coordination dividend
+ knowledge compounding dividend
- downstream expected loss
- carbon-adjusted cost
- variable AI cost
```

APVA also reports the components separately, the probability of negative TVY,
5% value-at-risk, worst-5% conditional value-at-risk, enterprise value capture,
and trust-adjusted autonomy. Policy can therefore reject an attractive average
when causal evidence or the downside is unacceptable.

## Measurement contract

Instrument every candidate workflow with five groups of facts:

1. Human baseline: reference completion time, practitioner skill tier, and fully loaded hourly rate.
2. AI workflow: generation time and human verification/correction time.
3. Quality: exact-span recall and grounded-answer faithfulness.
4. Friction: policy latency, false-positive rate, resolution time, and session-drop cost.
5. Value integrity: causal cohort, workflow outcome, coordination time, reusable
   artifact lineage, escaped-error severity and blast radius, autonomy/override
   outcome, and—where material—task-level emissions.

APVA does not substitute token savings for business value. The canonical result
remains:

```text
TVY = (gross time saved × RAG reliability) - guardrail friction
```

The enterprise layer then applies measured TVY to adoption, workforce scale,
realization, implementation and operating costs, risk avoidance, growth, and
discounted cash flow.

## Four-week rollout pattern

### Week 1 — establish evidence

- Select one repeatable, economically meaningful workflow.
- Capture at least 30 unaided human baselines across relevant skill tiers.
- Define a golden evaluation set and the decision policy before reviewing results.
- Set `hourly_rate_usd`; otherwise financial conclusions are intentionally unavailable.

### Week 2 — run in shadow mode

- Instrument the workflow with `APVATelemetryClient` or a native integration.
- Keep human approval in the loop and record verification time.
- Monitor queue drops, guardrail friction, financial-data coverage, and RAG reliability.
- Use `POST /api/v1/analysis/observed-business-case` to eliminate spreadsheet transcription.

### Week 3 — controlled pilot

- Freeze the input dataset and policy thresholds in version control.
- Generate a deterministic business case and retain its audit ID.
- Stress adoption, reliability, cost, and volume assumptions.
- Close failed gates in descending sensitivity order.

### Week 4 — scale or stop

- Require `scale` or `controlled_pilot` in CI and release governance.
- Compare all qualified workflows through the portfolio endpoint.
- Fund in priority order within the approved implementation budget.
- Re-run the same policy quarterly or whenever model, prompt, corpus, routing, or guardrails change.

## Core Python usage

```python
import json

from apva import EnterpriseAnalysisRequest, EnterpriseValueEngine

with open("examples/enterprise-business-case.json", encoding="utf-8") as source:
    request = EnterpriseAnalysisRequest.model_validate(json.load(source))

report = EnterpriseValueEngine.analyze(request)
print(report.decision, report.net_present_value_usd, report.report_id)
```

The engine is pure and local-first. Identical inputs and seeds produce the same
report ID and uncertainty bounds, making the result suitable for evidence
retention and independent review.

## Workflow gate with the SDK

```python
from apva_sdk import APVAEnterpriseClient

with APVAEnterpriseClient(
    api_url="https://apva.example.com/api/v1",
    api_key="...",
) as client:
    report = client.analyze_business_case(payload)
    client.require_decision(report, allowed=("scale", "controlled_pilot"))
```

`require_decision` raises `APVAWorkflowGateError` with the failed governance
checks. This makes it usable in CI, deployment approval, procurement review, or
an internal model registry.

## CLI and GitHub Actions

```bash
apva business-case case.json \
  --format markdown \
  --output apva-business-case.md \
  --require-decision scale controlled_pilot
```

Copy `.github/workflows/apva-value-gate.yml` into the delivery workflow. It
publishes the Markdown decision to the GitHub job summary, retains it as an
artifact, and exits non-zero when policy rejects the rollout.

## Cost and performance controls

- Telemetry is coalesced into bounded SDK batches and persisted with one usage row per batch.
- Scenario matrices are limited to 500 combinations and portfolio simulation work to 50,000 iterations.
- CPU-heavy Monte Carlo analysis runs outside the API event loop.
- Tenant aggregates use a short, write-invalidated cache; timeseries use one grouped query.
- PostgreSQL pool size and overflow are explicit deployment settings.

## Audit record

Every report includes:

- Framework and formula version.
- Canonical SHA-256 input hash and deterministic random seed.
- Simulation count, uncertainty, confidence level, and reliability weights.
- Every policy check with its actual value, operator, threshold, unit, and result.
- Tenant and observed sample lineage when generated from live telemetry.
- Ranked sensitivity levers and scenario resilience.

Retain the JSON report alongside the model, prompt, retrieval configuration,
golden dataset revision, approval ticket, and deployment artifact.
