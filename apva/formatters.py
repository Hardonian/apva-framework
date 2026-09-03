"""Output formatting for APVA CLI and reports.

Provides multiple serialisation formats (JSON, table, markdown, CSV)
so that every CLI subcommand and API export can share the same logic.
"""

from __future__ import annotations

import csv
import io
import json
import sys
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from apva.evaluation import EvaluationSummary
    from apva.models import APVAReport


def _is_tty() -> bool:
    """Return ``True`` when stdout is connected to an interactive terminal."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


# ---------------------------------------------------------------------------
# ANSI helpers (auto-disabled when piped)
# ---------------------------------------------------------------------------

class _Colours:
    """Terminal colour codes — all resolve to empty strings when not a TTY."""

    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"

    @classmethod
    def strip(cls) -> None:
        """Replace all colour codes with empty strings."""
        for attr in ("BOLD", "DIM", "GREEN", "RED", "YELLOW", "CYAN", "RESET"):
            setattr(cls, attr, "")


if not _is_tty():
    _Colours.strip()

C = _Colours


# ---------------------------------------------------------------------------
# Generic formatters
# ---------------------------------------------------------------------------

def format_json(data: Any, indent: int = 2) -> str:
    """Serialise *data* to indented JSON.

    Args:
        data: Any JSON-serialisable Python object.
        indent: JSON indentation level.

    Returns:
        str: Pretty-printed JSON string.
    """
    return json.dumps(data, indent=indent, sort_keys=True, default=str)


def format_table(headers: list[str], rows: list[list[Any]]) -> str:
    """Render *rows* as an ASCII table with aligned columns.

    Args:
        headers: Column header strings.
        rows: Row data (each row is a list matching *headers* length).

    Returns:
        str: ASCII-formatted table.
    """
    str_rows = [[str(cell) for cell in row] for row in rows]
    widths = [max([len(h)] + [len(r[i]) for r in str_rows]) for i, h in enumerate(headers)]

    line = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    header_row = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |"

    body = []
    for row in str_rows:
        body.append("| " + " | ".join(cell.ljust(w) for cell, w in zip(row, widths)) + " |")

    parts = [line, header_row, line, *body, line]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# APVAReport formatters
# ---------------------------------------------------------------------------

def format_report_json(report: APVAReport) -> str:
    """Serialise an APVAReport to JSON."""
    return format_json(report.model_dump(mode="json"))


def format_report_markdown(report: APVAReport) -> str:
    """Render an APVAReport as a Markdown summary.

    Args:
        report: APVA evaluation report.

    Returns:
        str: Markdown-formatted report string.
    """
    net = "✅ Net Positive" if report.is_net_positive else "❌ Net Negative"
    lines = [
        f"# APVA Report: {report.benchmark_name}",
        "",
        f"**Status**: {net}",
        f"**True Value Yield**: {report.true_value_yield_min:.2f} min",
        "",
        "| Metric | Value |",
        "|:---|---:|",
        f"| Gross Time Saved | {report.gross_time_saved_min:.2f} min |",
        f"| RAG Reliability Coefficient | {report.rag_reliability_coefficient:.4f} |",
        f"| Guardrail Friction Tax | {report.guardrail_friction_tax_min:.2f} min |",
        f"| TVY | {report.true_value_yield_min:.2f} min |",
    ]
    if report.true_value_yield_usd is not None:
        lines.append(f"| TVY (USD) | ${report.true_value_yield_usd:.2f} |")
    return "\n".join(lines)


def format_report_csv_row(report: APVAReport) -> str:
    """Return a single CSV row for an APVAReport (no header).

    Args:
        report: APVA evaluation report.

    Returns:
        str: Comma-separated values string.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        report.benchmark_name,
        f"{report.gross_time_saved_min:.4f}",
        f"{report.rag_reliability_coefficient:.4f}",
        f"{report.guardrail_friction_tax_min:.4f}",
        f"{report.true_value_yield_min:.4f}",
        f"{report.true_value_yield_usd:.2f}" if report.true_value_yield_usd is not None else "",
        report.is_net_positive,
    ])
    return buf.getvalue().strip()


def format_reports_csv(reports: list[APVAReport]) -> str:
    """Render multiple APVAReports as a complete CSV file with header.

    Args:
        reports: List of APVA reports to serialise.

    Returns:
        str: Complete CSV string.
    """
    header = "benchmark_name,gross_time_saved_min,rag_reliability,guardrail_tax_min,tvy_min,tvy_usd,is_net_positive"
    rows = [format_report_csv_row(r) for r in reports]
    return "\n".join([header, *rows])


# ---------------------------------------------------------------------------
# Audit scorecard (extracted from apva/cli.py)
# ---------------------------------------------------------------------------

def format_audit_scorecard(
    *,
    benchmark_name: str,
    eval_pass: bool,
    avg_recall: float,
    threshold: float,
    tvy_min: float,
    tvy_usd: float | None,
    gross_saved: float,
    rag_coeff: float,
    guardrail_tax: float,
    hourly_rate: float | None,
    is_net_positive: bool,
    avg_precision: float = 0.0,
    avg_f1: float = 0.0,
    avg_rouge_l: float = 0.0,
    avg_bleu: float = 0.0,
    eval_count: int = 0,
) -> str:
    """Render a rich ASCII audit scorecard.

    Args:
        benchmark_name: Name of the evaluated benchmark.
        eval_pass: Whether the evaluation gate passed.
        avg_recall: Average exact-span recall.
        threshold: Pass/fail recall threshold.
        tvy_min: True Value Yield in minutes.
        tvy_usd: True Value Yield in USD (or None).
        gross_saved: Gross time saved in minutes.
        rag_coeff: RAG reliability coefficient.
        guardrail_tax: Guardrail friction tax in minutes.
        hourly_rate: Practitioner hourly rate (or None).
        is_net_positive: Whether TVY is above zero.
        avg_precision: Average token precision.
        avg_f1: Average F1 score.
        avg_rouge_l: Average ROUGE-L score.
        avg_bleu: Average BLEU score.
        eval_count: Number of golden examples evaluated.

    Returns:
        str: Multi-line formatted scorecard string.
    """
    width = 66
    border = "═" * width
    divider = "─" * width

    status_icon = f"{C.GREEN}✅ PASS{C.RESET}" if eval_pass else f"{C.RED}❌ FAIL{C.RESET}"
    net_icon = f"{C.GREEN}✅ NET POSITIVE{C.RESET}" if is_net_positive else f"{C.RED}❌ NET NEGATIVE{C.RESET}"

    lines = [
        f"{C.BOLD}╔{border}╗{C.RESET}",
        f"{C.BOLD}║{'APVA Enterprise AI ROI Audit Scorecard':^{width}}║{C.RESET}",
        f"{C.BOLD}╠{border}╣{C.RESET}",
        f"  Benchmark   : {C.CYAN}{benchmark_name}{C.RESET}",
        f"  Eval Gate   : {status_icon}  (recall {avg_recall:.2%} vs threshold {threshold:.0%})",
        f"  Examples    : {eval_count}",
        f"{C.DIM}  {divider}{C.RESET}",
        f"  {C.BOLD}Scoring Metrics{C.RESET}",
        f"    Exact Span Recall   : {avg_recall:.4f}",
        f"    Token Precision     : {avg_precision:.4f}",
        f"    F1 Score            : {avg_f1:.4f}",
        f"    ROUGE-L             : {avg_rouge_l:.4f}",
        f"    BLEU                : {avg_bleu:.4f}",
        f"{C.DIM}  {divider}{C.RESET}",
        f"  {C.BOLD}TVY Engine{C.RESET}",
        f"    Gross Time Saved    : {gross_saved:+.2f} min",
        f"    RAG Reliability ρ   : {rag_coeff:.4f}",
        f"    Guardrail Tax       : {guardrail_tax:.2f} min",
        f"    True Value Yield    : {C.BOLD}{tvy_min:+.2f} min{C.RESET}",
    ]
    if tvy_usd is not None:
        lines.append(f"    TVY (USD)           : {C.BOLD}${tvy_usd:+.2f}{C.RESET}")
    if hourly_rate is not None:
        lines.append(f"    Hourly Rate         : ${hourly_rate:.2f}/hr")
    lines += [
        f"    Net Assessment      : {net_icon}",
        f"{C.BOLD}╚{border}╝{C.RESET}",
    ]
    return "\n".join(lines)
