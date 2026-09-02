# Changelog

All notable changes to the APVA framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-09-02

### Added

- **Core Engine Expansion**:
  - `apva.scoring`: Canonical multi-metric scoring pipeline providing `exact_span_recall`, `token_precision`, `f1_score`, `rouge_l_score`, and `bleu_score`.
  - `apva.datasets`: Structured `GoldenExample` loader, validator, and persistent storage.
  - `apva.evaluation`: Unified `EvaluationResult` and `EvaluationSummary` orchestration.
  - `apva.formatters`: Multi-format serialisation (`json`, `markdown`, `table`, `csv`) and rich ANSI scorecard.
  - Sensitivity analysis (`APVACalculator.sensitivity_analysis`) evaluating parameter delta impacts.
  - Monte Carlo confidence interval estimation (`APVACalculator.confidence_interval`).
  - Batch benchmark evaluation (`evaluate_batch`) and comparative ranking (`compare`).
  - Qualitative TVY grading (`TVYGrade`: `EXCEPTIONAL`, `STRONG`, `MODERATE`, `MARGINAL`, `NEGATIVE`).
  - Expanded skill level stratification with `INTERN` (2.0x) and `EXPERT` (0.5x) tiers.
- **Enterprise Backend**:
  - Centralized macro TVY computation service (`services/metrics.py`).
  - Batch telemetry ingestion endpoint (`POST /api/v1/telemetry/ingest/batch`) supporting up to 100 events per call.
  - Paginated evaluation job listings (`GET /api/v1/eval`) with status filtering.
  - Concurrent evaluation job submission (`POST /api/v1/eval/batch-trigger`).
  - Metered billing and invoice estimation endpoints (`GET /api/v1/billing/usage`, `GET /api/v1/billing/estimate`).
  - Standardized `X-APVA-Version` response header and process timing headers.
- **SDKs & Integrations**:
  - Native Anthropic client wrapper (`APVAAnthropic`) instrumenting messages and usage.
  - Exponential backoff retries and context manager support (`__enter__`, `__exit__`).
  - Per-invocation dynamic `run_id` generation in telemetry decorators.
  - TypeScript SDK upgraded with native `fetch` and batch ingestion.
- **CLI Upgrades**:
  - Added `--format` flag supporting `json`, `table`, `markdown`, and `csv`.
  - Added `version`, `validate`, `sensitivity`, and `compare` subcommands.
- **DevOps & Tooling**:
  - Full task runner implementation in `justfile`.
  - Modernized `docker-compose.yml` (removed deprecated version key, added networks and health checks).
  - GitHub Actions CI matrix testing across Python 3.10, 3.11, and 3.12.
- **Evaluation Dataset**:
  - Expanded `data/golden_dataset.json` from 3 to 25 production-grade test cases.

### Fixed

- **Memory Leak**: Evicted stale window buckets in `limiter.py` fixed-window rate limiter.
- **Non-deterministic Evaluation**: Proprietary SLM evaluator now derives deterministic perturbations via SHA-256 content hashing.
- **Serialization Failure**: Pydantic v2 `computed_at` datetime now serializes cleanly across all CLI outputs.
- **Code Duplication**: Removed triple-duplicated tokenization and scoring logic across CLI, packages, and services.
- **Isolated Streaming**: Guarded secondary sinks (ClickHouse and Stripe) with error isolation to ensure primary event persistence is never blocked.
