"""Unit tests for the apva.datasets module."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from apva.datasets import (
    GoldenExample,
    load_golden_set,
    save_golden_set,
    validate_golden_set,
)


def test_golden_example_model():
    ex = GoldenExample(
        query="What is TVY?",
        context="TVY is True Value Yield.",
        answer="True Value Yield.",
        expected_answer="True Value Yield.",
        metadata={"category": "definitions"},
    )
    assert ex.query == "What is TVY?"
    assert ex.metadata["category"] == "definitions"


def test_load_golden_set_valid(tmp_path: Path):
    path = tmp_path / "valid.json"
    data = {
        "examples": [
            {"query": "q1", "expected_answer": "a1", "context": "c1", "answer": "ans1"},
            {"query": "q2", "expected_answer": "a2"},
        ]
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    loaded = load_golden_set(path)
    assert len(loaded) == 2
    assert loaded[0].query == "q1"
    assert loaded[1].expected_answer == "a2"


def test_load_golden_set_array(tmp_path: Path):
    path = tmp_path / "array.json"
    data = [
        {"query": "q1", "expected_answer": "a1"},
    ]
    path.write_text(json.dumps(data), encoding="utf-8")
    loaded = load_golden_set(path)
    assert len(loaded) == 1
    assert loaded[0].query == "q1"


def test_validate_golden_set():
    examples = [
        GoldenExample(query="q1", expected_answer="a1"),
        GoldenExample(query="", expected_answer="a2"),  # empty query
        GoldenExample(query="q3", expected_answer=""),  # empty answer
        GoldenExample(query="q1", expected_answer="a1_dup"),  # duplicate query
    ]
    warnings = validate_golden_set(examples)
    assert len(warnings) == 3


def test_save_and_reload(tmp_path: Path):
    path = tmp_path / "saved.json"
    original = [
        GoldenExample(query="q1", expected_answer="a1", context="ctx1", answer="ans1", metadata={"level": 1}),
    ]
    save_golden_set(original, path)
    reloaded = load_golden_set(path)
    assert len(reloaded) == 1
    assert reloaded[0].query == "q1"
    assert reloaded[0].metadata.get("level") == 1
