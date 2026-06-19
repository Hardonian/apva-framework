"""Command-line interface for the APVA framework.

Run a benchmark simulation from explicit flags or a JSON input file and emit a
structured JSON report to stdout (or a file).

Examples:
    Run a built-in demo simulation::

        python -m apva.cli demo

    Run from explicit parameters::

        python -m apva.cli run \\
            --name "support-bot" \\
            --human-baseline 60 --skill junior \\
            --ai-time 5 --verify-time 8 \\
            --span-recall 0.9 --faithfulness 0.85 \\
            --base-latency 0.5 --fp-rate 0.1 --resolution-penalty 12 --cra 2

    Run from a JSON file::

        python -m apva.cli run-file benchmark.json
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from pydantic import ValidationError

from apva.calculator import APVACalculator
from apva.models import (
    BenchmarkInput,
    GuardrailMetrics,
    ProductivityMetrics,
    RAGMetrics,
    SkillLevel,
)


def _demo_benchmark() -> BenchmarkInput:
    """Build a representative demo benchmark.

    Returns:
        BenchmarkInput: A net-positive enterprise support-automation scenario.
    """
    return BenchmarkInput(
        name="demo-enterprise-support",
        productivity=ProductivityMetrics(
            reference_human_baseline_min=60.0,
            skill_level=SkillLevel.JUNIOR,
            ai_generation_time_min=4.0,
            epistemic_verification_time_min=9.0,
        ),
        rag=RAGMetrics(exact_span_recall=0.92, llm_faithfulness_score=0.88),
        guardrail=GuardrailMetrics(
            base_latency_overhead_min=0.5,
            false_positive_rate=0.08,
            resolution_penalty_time_min=15.0,
            cra_session_drop_penalty_min=2.0,
        ),
    )


def _emit(report_json: str, output: str | None) -> None:
    """Write the report JSON to a file or stdout.

    Args:
        report_json: Serialized JSON report.
        output: Destination path, or ``None`` for stdout.
    """
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(report_json + "\n")
        print(f"Report written to {output}", file=sys.stderr)
    else:
        print(report_json)


def _build_from_args(args: argparse.Namespace) -> BenchmarkInput:
    """Construct a :class:`BenchmarkInput` from parsed CLI flags.

    Args:
        args: Parsed argparse namespace for the ``run`` subcommand.

    Returns:
        BenchmarkInput: A validated benchmark input.
    """
    return BenchmarkInput(
        name=args.name,
        productivity=ProductivityMetrics(
            reference_human_baseline_min=args.human_baseline,
            skill_level=SkillLevel(args.skill),
            ai_generation_time_min=args.ai_time,
            epistemic_verification_time_min=args.verify_time,
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
    """Construct the argparse CLI parser.

    Returns:
        argparse.ArgumentParser: The configured top-level parser.
    """
    parser = argparse.ArgumentParser(
        prog="apva",
        description="APVA: AI Productivity & Value Architecture benchmark engine.",
    )
    parser.add_argument(
        "-o", "--output", default=None, help="Write JSON report to this path."
    )
    parser.add_argument(
        "--indent", type=int, default=2, help="JSON indent (default: 2)."
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="Run a built-in demo benchmark simulation.")

    run = sub.add_parser("run", help="Run a benchmark from explicit parameters.")
    run.add_argument("--name", required=True, help="Benchmark name.")
    run.add_argument(
        "--human-baseline",
        type=float,
        required=True,
        help="Reference (mid-level) human baseline in minutes.",
    )
    run.add_argument(
        "--skill",
        choices=[s.value for s in SkillLevel],
        default=SkillLevel.MID.value,
        help="Human skill tier (default: mid).",
    )
    run.add_argument(
        "--ai-time", type=float, required=True, help="AI generation time (min)."
    )
    run.add_argument(
        "--verify-time",
        type=float,
        required=True,
        help="Epistemic verification time (min).",
    )
    run.add_argument(
        "--span-recall", type=float, required=True, help="Exact span recall [0,1]."
    )
    run.add_argument(
        "--faithfulness",
        type=float,
        required=True,
        help="LLM faithfulness score [0,1].",
    )
    run.add_argument(
        "--base-latency",
        type=float,
        required=True,
        help="Base latency overhead (min).",
    )
    run.add_argument(
        "--fp-rate", type=float, required=True, help="False positive rate [0,1]."
    )
    run.add_argument(
        "--resolution-penalty",
        type=float,
        required=True,
        help="Resolution penalty time per false positive (min).",
    )
    run.add_argument(
        "--cra",
        type=float,
        required=True,
        help="CRA session drop penalty (min).",
    )

    run_file = sub.add_parser(
        "run-file", help="Run a benchmark from a JSON input file."
    )
    run_file.add_argument("path", help="Path to a BenchmarkInput JSON file.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Optional argument vector (defaults to ``sys.argv[1:]``).

    Returns:
        int: Process exit code (0 success, 2 on validation/IO error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "demo":
            benchmark = _demo_benchmark()
        elif args.command == "run":
            benchmark = _build_from_args(args)
        elif args.command == "run-file":
            with open(args.path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            benchmark = BenchmarkInput.model_validate(payload)
        else:  # pragma: no cover - argparse enforces a valid subcommand.
            parser.error(f"Unknown command: {args.command}")
            return 2
    except (ValidationError, ValueError) as exc:
        print(f"Input validation error: {exc}", file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read input file: {exc}", file=sys.stderr)
        return 2

    report = APVACalculator.evaluate(benchmark)
    report_json = json.dumps(report.model_dump(), indent=args.indent)
    _emit(report_json, args.output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
