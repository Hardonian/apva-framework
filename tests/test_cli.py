"""Tests for APVA CLI eval runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from apva_cli.main import exact_span_recall, load_golden_set, summarize


def test_exact_span_recall_equal():
    assert exact_span_recall("foo bar", "foo bar") == pytest.approx(1.0)


def test_exact_span_recall_partial():
    assert exact_span_recall("foo", "foo bar") == pytest.approx(0.5)


def test_summarize_pass(tmp_path: Path):
    results = [{"index": "0", "query": "q", "answer": "a b c", "expected_answer": "a b c", "exact_span_recall": 1.0}]
    summary = summarize(results)
    assert summary["passed"] is True
    assert summary["count"] == 1


def test_summarize_low_recall(tmp_path: Path):
    results = [{"index": "0", "query": "q", "answer": "", "expected_answer": "a b c", "exact_span_recall": 0.0}]
    summary = summarize(results)
    assert summary["passed"] is False
    assert summary["average_exact_span_recall"] == pytest.approx(0.0)


def test_load_golden_set(tmp_path: Path):
    path = tmp_path / "golden.json"
    path.write_text('{"examples": [{"query": "q", "answer": "a", "expected_answer": "a"}]}')
    examples = load_golden_set(path)
    assert len(examples) == 1
    assert examples[0].query == "q"
