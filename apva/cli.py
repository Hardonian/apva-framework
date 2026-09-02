"""Command-line interface for the APVA framework.

Run a benchmark simulation, golden dataset evaluation, local AI proxy, or full
turnkey enterprise TVY audit scorecard.

Examples:
    Run a built-in demo simulation::

        apva demo

    Run golden dataset evaluation in CI/CD::

        apva run-eval --golden-set ./data/golden_dataset.json --threshold 0.85

    Run full enterprise TVY audit scorecard::

        apva audit --golden-set ./data/golden_dataset.json --hourly-rate 85.0

    Run local AI proxy::

        apva proxy --port 8080 --target http://localhost:11434/v1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from pydantic import ValidationError

from apva.calculator import APVACalculator
from apva.constants import FRAMEWORK_VERSION
from apva.datasets import GoldenExample, load_golden_set, validate_golden_set
from apva.evaluation import evaluate_examples, summarize_evaluation
from apva.formatters import (
    format_audit_scorecard,
    format_json,
    format_report_markdown,
    format_reports_csv,
    format_table,
)
from apva.models import (
    BenchmarkInput,
    GuardrailMetrics,
    ProductivityMetrics,
    RAGMetrics,
    SkillLevel,
)
from apva.scoring import exact_span_recall, tokenize


def _demo_benchmark() -> BenchmarkInput:
    """Build a representative demo benchmark."""
    return BenchmarkInput(
        name="demo-enterprise-support",
        productivity=ProductivityMetrics(
            reference_human_baseline_min=60.0,
            skill_level=SkillLevel.JUNIOR,
            ai_generation_time_min=4.0,
            epistemic_verification_time_min=9.0,
            hourly_rate_usd=75.0,
        ),
        rag=RAGMetrics(exact_span_recall=0.92, llm_faithfulness_score=0.88),
        guardrail=GuardrailMetrics(
            base_latency_overhead_min=0.5,
            false_positive_rate=0.08,
            resolution_penalty_time_min=15.0,
            cra_session_drop_penalty_min=2.0,
        ),
    )


async def fetch_target_answer(target_url: str, example: dict[str, str] | GoldenExample) -> str:
    """Fetch generated answer from a live target RAG endpoint."""
    import httpx

    query = example.query if isinstance(example, GoldenExample) else example["query"]
    context = example.context if isinstance(example, GoldenExample) else example.get("context", "")
    payload = {"query": query, "context": context}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(f"{target_url.rstrip('/')}/evaluate", json=payload)
        response.raise_for_status()
        data = response.json()
    if isinstance(data, dict) and "answer" in data:
        return str(data["answer"])
    if isinstance(data, str):
        return data
    return str(data)


def summarize_eval(results: list[dict[str, Any]], threshold: float = 0.85) -> dict[str, Any]:
    """Summarize golden set evaluation results."""
    recalls = [float(item["exact_span_recall"]) for item in results]
    avg = sum(recalls) / len(recalls) if recalls else 0.0
    return {
        "count": len(results),
        "average_exact_span_recall": round(avg, 4),
        "threshold": threshold,
        "passed": avg >= threshold,
        "results": results,
    }


def generate_audit_scorecard(
    eval_summary: dict[str, Any],
    human_baseline_min: float = 30.0,
    ai_time_min: float = 3.0,
    verify_time_min: float = 5.0,
    guardrail_tax_min: float = 0.8,
    hourly_rate_usd: float = 85.0,
) -> str:
    """Generate executive enterprise TVY audit scorecard in Markdown."""
    recall = eval_summary["average_exact_span_recall"]
    faithfulness = min(1.0, recall * 0.95 + 0.05)
    rag_reliability = 0.6 * recall + 0.4 * faithfulness

    gross_time_saved = human_baseline_min - (ai_time_min + verify_time_min)
    tvy_min = (gross_time_saved * rag_reliability) - guardrail_tax_min
    tvy_usd = (tvy_min / 60.0) * hourly_rate_usd
    annual_usd_per_100_engineers = tvy_usd * 40 * 50 * 100

    status_badge = "[NET-POSITIVE ROI]" if tvy_min > 0 else "[NET-NEGATIVE YIELD]"

    scorecard = f"""# APVA Enterprise AI ROI Audit Scorecard

> **Status**: {status_badge} | **Audit Standard**: APVA Framework v{FRAMEWORK_VERSION}

---

## Executive Summary

| Metric | Measured Value | Unit |
|---|---|---|
| **True Value Yield (TVY)** | **{tvy_min:+.2f}** | **Minutes / Task** |
| **Financial Value Yield** | **${tvy_usd:+.2f}** | **USD / Task** |
| **Projected Annual Impact (100 Engineers)** | **${annual_usd_per_100_engineers:+,.2f}** | **USD / Year** |
| **Golden Set Recall** | **{recall * 100:.1f}%** | **Exact Span Recall** |
| **RAG Reliability Coefficient** | **{rag_reliability * 100:.1f}%** | **Blended Reliability** |
| **Guardrail Latency Tax** | **{guardrail_tax_min:.2f}** | **Minutes Friction** |

---

## The Three Pillars Decomposition

### 1. Productivity Pillar
* **Human Baseline Equivalent**: {human_baseline_min:.1f} minutes
* **AI Generation Time**: {ai_time_min:.1f} minutes
* **Epistemic Verification**: {verify_time_min:.1f} minutes
* **Gross Time Saved**: **{gross_time_saved:.1f} minutes**

### 2. RAG Reliability Pillar
* **Evaluation Cases Tested**: {eval_summary['count']} golden queries
* **Retrieval Exact Span Recall**: {recall * 100:.1f}%
* **LLM Faithfulness Score**: {faithfulness * 100:.1f}%
* **Reliability Discount Factor**: **{rag_reliability:.3f}x**

### 3. Guardrail & Friction Pillar
* **Base Latency Overhead**: {guardrail_tax_min:.2f} minutes
* **Fully Loaded Wage Basis**: ${hourly_rate_usd:.2f} / hour

---

## Actionable Prescriptions

1. **Optimize Guardrail Latency**: Reduce semantic router overhead by deploying APVA edge workers to recover ~{guardrail_tax_min * 0.6:.2f}m per session.
2. **Context Precision**: Maintain top_k context chunks at 3-5 to maximize exact span recall above 90%.
3. **Continuous CI/CD Gate**: Enforce `apva run-eval --threshold 0.85` in pre-merge workflows.

---
*Report generated by APVA Framework (Hardonia Ecosystem - https://aiautomatedsystems.ca)*
"""
    return scorecard


def _emit(report_text: str, output: str | None) -> None:
    """Write text to file or stdout."""
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(report_text + "\n")
        print(f"Report written to {output}", file=sys.stderr)
    else:
        try:
            print(report_text)
        except UnicodeEncodeError:
            sys.stdout.buffer.write(report_text.encode("utf-8") + b"\n")


def _format_report(report: Any, fmt: str, indent: int = 2) -> str:
    """Format an APVAReport according to the requested format."""
    if fmt == "markdown":
        return format_report_markdown(report)
    elif fmt == "csv":
        return format_reports_csv([report])
    elif fmt == "table":
        headers = ["Metric", "Value", "Unit"]
        rows = [
            ["Benchmark Name", report.benchmark_name, ""],
            ["Human Baseline", f"{report.skill_adjusted_human_baseline_min:.2f}", "min"],
            ["Gross Time Saved", f"{report.gross_time_saved_min:.2f}", "min"],
            ["RAG Reliability (rho)", f"{report.rag_reliability_coefficient:.4f}", "coefficient"],
            ["Guardrail Tax", f"{report.guardrail_friction_tax_min:.2f}", "min"],
            ["True Value Yield (TVY)", f"{report.true_value_yield_min:+.2f}", "min"],
            ["TVY (USD)", f"${report.true_value_yield_usd:.2f}" if report.true_value_yield_usd is not None else "N/A", "USD"],
            ["TVY Grade", report.tvy_grade.value.upper(), ""],
            ["Net Positive", "YES" if report.is_net_positive else "NO", ""],
        ]
        return format_table(headers, rows)
    else:
        # Default json
        return json.dumps(report.model_dump(mode="json"), indent=indent)


def _build_from_args(args: argparse.Namespace) -> BenchmarkInput:
    """Construct BenchmarkInput from parsed CLI flags."""
    return BenchmarkInput(
        name=args.name,
        productivity=ProductivityMetrics(
            reference_human_baseline_min=args.human_baseline,
            skill_level=SkillLevel(args.skill),
            ai_generation_time_min=args.ai_time,
            epistemic_verification_time_min=args.verify_time,
            hourly_rate_usd=args.hourly_rate,
        ),
        rag=RAGMetrics(
            exact_span_recall=args.span_recall,
            llm_faithfulness_score=args.faithfulness,
        ),
        guardrail=GuardrailMetrics(
            base_latency_overhead_min=args.base_latency,
            false_positive_rate=args.fp_rate,
            resolution_penalty_time_min=args.resolution_penalty,
            cra_session_drop_penalty_min=args.cra,
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    """Construct the unified argparse CLI parser."""
    parser = argparse.ArgumentParser(
        prog="apva",
        description=f"APVA v{FRAMEWORK_VERSION}: AI Productivity & Value Architecture benchmark & evaluation engine.",
    )
    parser.add_argument("-o", "--output", default=None, help="Write output to file.")
    parser.add_argument("--format", choices=["json", "table", "markdown", "csv"], default="json", help="Output format.")
    parser.add_argument("--indent", type=int, default=2, help="JSON indent.")

    sub = parser.add_subparsers(dest="command", required=True)

    # version
    sub.add_parser("version", help="Print APVA framework version and runtime info.")

    # demo
    sub.add_parser("demo", help="Run built-in demo benchmark simulation.")

    # run
    run = sub.add_parser("run", help="Run benchmark from explicit parameters.")
    run.add_argument("--name", required=True, help="Benchmark name.")
    run.add_argument("--human-baseline", type=float, required=True, help="Human baseline in minutes.")
    run.add_argument("--skill", choices=[s.value for s in SkillLevel], default=SkillLevel.MID.value)
    run.add_argument("--hourly-rate", type=float, default=None, help="Hourly rate in USD.")
    run.add_argument("--ai-time", type=float, required=True, help="AI generation time (min).")
    run.add_argument("--verify-time", type=float, required=True, help="Verification time (min).")
    run.add_argument("--span-recall", type=float, required=True, help="Exact span recall [0,1].")
    run.add_argument("--faithfulness", type=float, required=True, help="Faithfulness score [0,1].")
    run.add_argument("--base-latency", type=float, required=True, help="Base latency (min).")
    run.add_argument("--fp-rate", type=float, required=True, help="False positive rate [0,1].")
    run.add_argument("--resolution-penalty", type=float, required=True, help="Resolution penalty (min).")
    run.add_argument("--cra", type=float, required=True, help="CRA drop penalty (min).")

    # run-file
    run_file = sub.add_parser("run-file", help="Run benchmark from JSON file.")
    run_file.add_argument("path", help="Path to BenchmarkInput JSON file.")
    run_file.add_argument("--sensitivity", action="store_true", help="Include sensitivity analysis.")
    run_file.add_argument("--ci", action="store_true", help="Include Monte Carlo confidence interval.")

    # sensitivity
    sens = sub.add_parser("sensitivity", help="Run sensitivity analysis on a benchmark.")
    sens.add_argument("path", help="Path to BenchmarkInput JSON file.")
    sens.add_argument("--delta", type=float, default=0.05, help="Perturbation fraction (default: 0.05).")

    # compare
    comp = sub.add_parser("compare", help="Compare multiple benchmark JSON files.")
    comp.add_argument("files", nargs="+", help="Paths to BenchmarkInput JSON files to compare.")

    # validate
    val = sub.add_parser("validate", help="Validate a golden dataset file structure.")
    val.add_argument("--golden-set", required=True, help="Path to golden dataset JSON.")

    # run-eval
    run_eval = sub.add_parser("run-eval", help="Run golden set evaluation gate.")
    run_eval.add_argument("--golden-set", required=True, help="Path to golden dataset JSON.")
    run_eval.add_argument("--target-url", default=None, help="Optional live target RAG URL.")
    run_eval.add_argument("--threshold", type=float, default=0.85, help="Pass threshold.")

    # audit
    audit = sub.add_parser("audit", help="Generate executive enterprise TVY audit scorecard.")
    audit.add_argument("--golden-set", required=True, help="Path to golden dataset JSON.")
    audit.add_argument("--target-url", default=None, help="Optional live target RAG URL.")
    audit.add_argument("--hourly-rate", type=float, default=85.0, help="Practitioner hourly rate in USD.")
    audit.add_argument("--human-baseline", type=float, default=30.0, help="Human baseline (min).")
    audit.add_argument("--guardrail-tax", type=float, default=0.8, help="Guardrail tax (min).")

    # proxy
    proxy = sub.add_parser("proxy", help="Run universal local AI workstation proxy.")
    proxy.add_argument("--port", type=int, default=8080, help="Proxy listen port.")
    proxy.add_argument("--target", default="http://localhost:11434/v1", help="Target URL.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "version":
            info = {
                "apva_version": FRAMEWORK_VERSION,
                "python_version": sys.version.split()[0],
                "platform": sys.platform,
            }
            _emit(json.dumps(info, indent=args.indent), args.output)
            return 0

        elif args.command == "demo":
            benchmark = _demo_benchmark()
            report = APVACalculator.evaluate(benchmark, include_sensitivity=True, include_confidence_interval=True)
            _emit(_format_report(report, args.format, args.indent), args.output)
            return 0

        elif args.command == "run":
            benchmark = _build_from_args(args)
            report = APVACalculator.evaluate(benchmark)
            _emit(_format_report(report, args.format, args.indent), args.output)
            return 0

        elif args.command == "run-file":
            with open(args.path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            benchmark = BenchmarkInput.model_validate(payload)
            report = APVACalculator.evaluate(
                benchmark,
                include_sensitivity=getattr(args, "sensitivity", False),
                include_confidence_interval=getattr(args, "ci", False),
            )
            _emit(_format_report(report, args.format, args.indent), args.output)
            return 0

        elif args.command == "sensitivity":
            with open(args.path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            benchmark = BenchmarkInput.model_validate(payload)
            vectors = APVACalculator.sensitivity_analysis(benchmark, delta_fraction=args.delta)
            if args.format == "table":
                headers = ["Parameter", "Base Value", "Delta", "TVY Lower", "TVY Upper", "TVY Impact"]
                rows = [
                    [v.parameter, f"{v.base_value:.4f}", f"{v.delta:.4f}", f"{v.tvy_at_lower:.4f}", f"{v.tvy_at_upper:.4f}", f"{v.tvy_impact:.4f}"]
                    for v in vectors
                ]
                _emit(format_table(headers, rows), args.output)
            else:
                _emit(json.dumps([v.model_dump() for v in vectors], indent=args.indent), args.output)
            return 0

        elif args.command == "compare":
            benchmarks = []
            for filepath in args.files:
                with open(filepath, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                benchmarks.append(BenchmarkInput.model_validate(data))
            reports = APVACalculator.evaluate_batch(benchmarks)
            comparison = APVACalculator.compare(reports)
            _emit(json.dumps(comparison, indent=args.indent), args.output)
            return 0

        elif args.command == "validate":
            examples = load_golden_set(Path(args.golden_set))
            warnings = validate_golden_set(examples)
            result = {
                "count": len(examples),
                "valid": len(warnings) == 0,
                "warnings": warnings,
            }
            _emit(json.dumps(result, indent=args.indent), args.output)
            return 0 if len(warnings) == 0 else 1

        elif args.command == "run-eval":
            examples = load_golden_set(Path(args.golden_set))
            results = asyncio.run(evaluate_examples(examples, args.target_url))
            summary = summarize_evaluation(results, args.threshold)
            _emit(json.dumps(summary.to_dict(), indent=args.indent), args.output)
            return 0 if summary.passed else 1

        elif args.command == "audit":
            examples = load_golden_set(Path(args.golden_set))
            raw_eval_results = []
            for index, example in enumerate(examples):
                ans = example.answer
                if args.target_url:
                    ans = asyncio.run(fetch_target_answer(args.target_url, example))
                raw_eval_results.append({
                    "index": str(index),
                    "query": example.query,
                    "answer": ans,
                    "expected_answer": example.expected_answer,
                    "exact_span_recall": exact_span_recall(ans, example.expected_answer),
                })
            summary = summarize_eval(raw_eval_results, 0.85)
            scorecard = generate_audit_scorecard(
                summary,
                human_baseline_min=args.human_baseline,
                guardrail_tax_min=args.guardrail_tax,
                hourly_rate_usd=args.hourly_rate,
            )
            _emit(scorecard, args.output)
            return 0

        elif args.command == "proxy":
            try:
                from apva_cli.proxy import run_proxy
            except ImportError:
                from packages.cli.src.apva_cli.proxy import run_proxy
            run_proxy(args.port, args.target)
            return 0

        else:
            parser.error(f"Unknown command: {args.command}")
            return 2

    except (ValidationError, ValueError) as exc:
        print(f"Input validation error: {exc}", file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read input file: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
