"""APVA CLI."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+(?:[-'][a-zA-Z0-9]+)?", text.lower())


def exact_span_recall(answer: str, expected_answer: str) -> float:
    expected_tokens = tokenize(expected_answer)
    answer_tokens = tokenize(answer)
    if not expected_tokens:
        return 1.0 if not answer_tokens else 0.0
    found = 0
    for token in expected_tokens:
        if token in answer_tokens:
            found += 1
    return found / len(expected_tokens)


def load_golden_set(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text())
    examples = data.get("examples") if isinstance(data, dict) else data
    if not isinstance(examples, list):
        raise ValueError("Golden dataset must be a list or contain an 'examples' list")
    parsed: list[dict[str, str]] = []
    for index, item in enumerate(examples):
        if not isinstance(item, dict):
            raise ValueError(f"Example {index} is not an object")
        parsed.append({
            "query": str(item["query"]),
            "context": str(item.get("context", "")),
            "answer": str(item["answer"]),
            "expected_answer": str(item["expected_answer"]),
        })
    return parsed


async def fetch_answer(target_url: str, example: dict[str, str]) -> str:
    import httpx
    payload = {"query": example["query"], "context": example["context"]}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(f"{target_url.rstrip('/')}/evaluate", json=payload)
        response.raise_for_status()
        data = response.json()
    if isinstance(data, dict) and "answer" in data:
        return str(data["answer"])
    if isinstance(data, str):
        return data
    raise ValueError("Target response must be a string or object with an 'answer' field")


async def evaluate_examples(examples: list[dict[str, str]], target_url: str | None = None) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, example in enumerate(examples):
        answer = example["answer"]
        if target_url:
            answer = await fetch_answer(target_url, example)
        recall = exact_span_recall(answer, example["expected_answer"])
        results.append({
            "index": str(index),
            "query": example["query"],
            "answer": answer,
            "expected_answer": example["expected_answer"],
            "exact_span_recall": recall,
        })
    return results


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    recalls = [float(item["exact_span_recall"]) for item in results]
    avg = sum(recalls) / len(recalls) if recalls else 0.0
    return {
        "count": len(results),
        "average_exact_span_recall": avg,
        "passed": avg >= 0.85,
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="apva", description="APVA CI/CD evaluation runner")
    sub = parser.add_subparsers(dest="command", required=True)
    run_eval = sub.add_parser("run-eval", help="Run exact span recall evaluation")
    run_eval.add_argument("--golden-set", required=True, help="Path to golden dataset JSON")
    run_eval.add_argument("--target-url", default=None, help="Optional target RAG system base URL")
    run_eval.add_argument("--threshold", type=float, default=0.85, help="Pass threshold")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "run-eval":
        parser.error("Unsupported command")
    examples = load_golden_set(Path(args.golden_set))
    results = asyncio.run(evaluate_examples(examples, args.target_url))
    summary = summarize(results)
    summary["threshold"] = args.threshold
    summary["passed"] = float(summary["average_exact_span_recall"]) >= args.threshold
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
