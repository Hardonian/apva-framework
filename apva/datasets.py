"""Golden dataset loading, validation, and generation.

This module provides a canonical ``GoldenExample`` dataclass and loading
helpers so that the CLI, backend, and SDK all share a single
parse-and-validate pipeline for golden evaluation datasets.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GoldenExample:
    """A single golden evaluation example.

    Attributes:
        query: The user's question / prompt.
        context: Retrieved context provided to the RAG system.
        answer: The RAG system's generated answer (may be empty when
            fetching live from a target URL).
        expected_answer: The ground-truth reference answer.
        metadata: Optional structured metadata (difficulty, category, …).
    """

    query: str
    context: str = ""
    answer: str = ""
    expected_answer: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def load_golden_set(path: Path | str) -> list[GoldenExample]:
    """Load and validate a golden dataset JSON file.

    The file may be either:

    * A bare JSON array of example objects, or
    * A JSON object with an ``"examples"`` key containing the array.

    Each example object must have at least ``query`` and
    ``expected_answer`` string fields.

    Args:
        path: Filesystem path to the JSON dataset.

    Returns:
        list[GoldenExample]: Parsed and validated examples.

    Raises:
        ValueError: If the file structure is invalid.
        FileNotFoundError: If *path* does not exist.
    """
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    examples = data.get("examples") if isinstance(data, dict) else data
    if not isinstance(examples, list):
        raise ValueError(
            "Golden dataset must be a JSON array or an object with an 'examples' array."
        )

    parsed: list[GoldenExample] = []
    for index, item in enumerate(examples):
        if not isinstance(item, dict):
            raise ValueError(f"Example {index} is not a JSON object.")
        parsed.append(
            GoldenExample(
                query=str(item.get("query", "")),
                context=str(item.get("context", "")),
                answer=str(item.get("answer", "")),
                expected_answer=str(item.get("expected_answer", "")),
                metadata=item.get("metadata", {}),
            )
        )
    return parsed


def validate_golden_set(examples: list[GoldenExample]) -> list[str]:
    """Return a list of human-readable validation warnings.

    Checks that every example has non-empty ``query`` and
    ``expected_answer`` fields, and flags any duplicates.

    Args:
        examples: Previously loaded golden examples.

    Returns:
        list[str]: Validation warning messages (empty if all OK).
    """
    warnings: list[str] = []
    seen_queries: set[str] = set()
    for i, ex in enumerate(examples):
        if not ex.query.strip():
            warnings.append(f"Example {i}: empty 'query'.")
        if not ex.expected_answer.strip():
            warnings.append(f"Example {i}: empty 'expected_answer'.")
        if ex.query in seen_queries:
            warnings.append(f"Example {i}: duplicate query '{ex.query[:60]}…'.")
        seen_queries.add(ex.query)
    return warnings


def save_golden_set(
    examples: list[GoldenExample],
    path: Path | str,
    *,
    indent: int = 2,
) -> None:
    """Persist a golden dataset to a JSON file.

    Args:
        examples: Golden examples to serialise.
        path: Destination file path.
        indent: JSON indentation level.
    """
    path = Path(path)
    payload = {
        "examples": [
            {
                "query": ex.query,
                "context": ex.context,
                "answer": ex.answer,
                "expected_answer": ex.expected_answer,
                **({"metadata": ex.metadata} if ex.metadata else {}),
            }
            for ex in examples
        ]
    }
    path.write_text(json.dumps(payload, indent=indent, ensure_ascii=False) + "\n", encoding="utf-8")
