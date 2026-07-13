# APVA — AI Productivity & Value Architecture

> Measure the **true enterprise ROI of Generative AI** as a single time-denominated metric: **True Value Yield (TVY)**.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status: Active](https://img.shields.io/badge/status-active-orange)]()
[![Bootstrap-ready](https://img.shields.io/badge/bootstrap-ready-2ea043)](BOOTSTRAP.md)

---

## The problem

Most AI benchmarks answer *"how fast did the model produce output?"* and ignore the only number a CFO cares about: **net human time saved**.

APVA answers: *"How much reliability-discounted, friction-adjusted human time did this AI workflow actually save — and what is it worth?"*

## The Three Pillars

| Pillar | Captures | Key inputs |
|--------|----------|------------|
| **Productivity** | Skill-stratified human baselines + epistemic verification | reference baseline, skill tier, AI generation time, verification time |
| **RAG Reliability** | Deterministic exact-span recall + faithfulness | exact span recall, faithfulness score, retrieval coverage |
| **Value / Friction** | Operational friction, rework, and cost normalization | tool-switch cost, rework rate, $/hour normalization |

These fuse into **TVY (True Value Yield)** — a defensible, time-denominated ROI metric you can compare across workflows, teams, and models.

## What it is

APVA is a **local-first** framework (FastAPI + SQLAlchemy + Celery) that:

- Runs TVY benchmarks against real workflows
- Exposes a telemetry + scoring API (`/metrics`, `/health`)
- Ships a CLI + SDK for embedding in your own pipelines
- Persists results to SQLite/Postgres (async)
- Is **bootstrap-ready** — one command stands up the full stack

## Quick bootstrap

```bash
# 0. Prereqs: Python 3.12+, just (pipx install rust-just)
git clone https://github.com/Hardonian/apva-framework.git
cd apva-framework

# 1. One-command setup (venv + .env + deps + smoke test)
just bootstrap
#  or without just:
./scripts/bootstrap.sh

# 2. Configure
cp .env.example .env   # edit with your keys — never commit .env

# 3. Run
just dev               # start locally
just test              # run the suite
just smoke             # assert health endpoint responds

# Optional: Docker
docker compose up --build
```

## Layout

```
apva/            # core TVY engine, models, scoring
apps/            # service apps (API, worker)
packages/        # reusable SDK / client
data/            # fixtures, sample benchmarks
docs/            # methodology + architecture
tests/           # pytest suite
deploy/          # container / deploy config
```

## Why local-first

No telemetry leaves your machine unless you wire it out. Benchmarks, scores, and
raw traces stay in your own store — so the ROI numbers you report are auditable,
not a black box.

## Part of the Hardonia stack

APVA is one of the [Hardonia](https://github.com/Hardonian) local-first AI
infrastructure projects: measurable value, operator-grade control, and zero
theatre.

## License

MIT — see [LICENSE](LICENSE).
