# APVA Enterprise Pricing & Unit Economics

## Pricing Tiers

APVA follows a hybrid open-core / usage-metered model designed for seamless bottom-up adoption with clear enterprise expansion paths.

| Tier | Price | Telemetry Quota | Evaluation Jobs | Deployment Options | Support SLA |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Community / Open Source** | **$0** (Apache 2.0) | Unlimited (Self-Hosted) | Unlimited (Local) | Self-Hosted / Docker / SQLite | Community / GitHub |
| **Team** | **$99 / month** | 250,000 events / mo | 5,000 evals / mo | Managed Cloud / Multi-Tenant | 48-Hour Response |
| **Business** | **$499 / month** | 2,500,000 events / mo | 50,000 evals / mo | Managed Cloud + Edge Ingest | 12-Hour Response |
| **Enterprise** | **Custom** | Custom Scale | Custom Scale | Air-Gapped / VPC / Dedicated ClickHouse | 1-Hour SLA + Dedicated Engineer |

---

## Usage-Based Overage Metering

For usage beyond included tier quotas, charges are calculated via the `StripeBillingService`:

* **Telemetry Events**: `$0.005` per 1,000 events ($5.00 per million events).
* **RAG Evaluation Jobs**: `$0.05` per 1,000 evaluations ($50.00 per million evaluations).

---

## ROI Justification for Enterprise Customers

Consider an engineering organization with **100 software engineers** using copilot/RAG systems:

* Average practitioner cost: **$85.00 / hour** ($170,000 fully loaded annual compensation).
* Daily tasks aided: **5 tasks / day** per engineer.
* Measured APVA TVY: **+15.0 minutes net saved per task**.
* Daily time saved per engineer: **75 minutes (1.25 hours)**.
* Daily value per engineer: `1.25 hours * $85.00 = $106.25`.
* Annual organizational value (250 working days, 100 engineers):
  $$\text{Value} = 100 \times 250 \times \$106.25 = \mathbf{\$2,656,250 / \text{year}}$$

An APVA Enterprise contract priced at **$50,000/year** represents a **53x ROI**, defending the investment within the first **7 days of operation**.
