"""Unit tests for the canonical apva.scoring module."""

from __future__ import annotations

import pytest

from apva.scoring import (
    bleu_score,
    exact_span_recall,
    f1_score,
    rouge_l_score,
    token_precision,
    tokenize,
)


def test_tokenize():
    text = "The state-of-the-art APVA framework doesn't drop tokens!"
    tokens = tokenize(text)
    assert "state-of-the-art" in tokens
    assert "doesn't" in tokens
    assert "apva" in tokens
    assert "tokens" in tokens


def test_tokenize_empty():
    assert tokenize("") == []
    assert tokenize("   \n\t  ") == []


def test_exact_span_recall():
    expected = "APVA measures true enterprise ROI of Generative AI"
    answer = "We know that APVA measures true enterprise ROI of Generative AI accurately."
    assert exact_span_recall(answer, expected) == pytest.approx(1.0)

    partial = "APVA measures enterprise ROI"
    recall = exact_span_recall(partial, expected)
    assert 0.0 < recall < 1.0

    empty = ""
    assert exact_span_recall(empty, expected) == 0.0
    assert exact_span_recall("something", "") == 0.0
    assert exact_span_recall("", "") == 1.0


def test_token_precision():
    expected = "APVA measures enterprise ROI"
    answer = "APVA measures enterprise ROI"
    assert token_precision(answer, expected) == pytest.approx(1.0)

    # Hallucinated extra tokens lower precision
    hallucinated = "APVA measures enterprise ROI with deep neural networks and quantum computing"
    prec = token_precision(hallucinated, expected)
    assert 0.0 < prec < 1.0

    assert token_precision("", expected) == 0.0
    assert token_precision("", "") == 1.0


def test_f1_score():
    expected = "alpha beta gamma delta"
    exact = "alpha beta gamma delta"
    assert f1_score(exact, expected) == pytest.approx(1.0)

    disjoint = "one two three"
    assert f1_score(disjoint, expected) == 0.0

    partial = "alpha beta other"
    f1 = f1_score(partial, expected)
    assert 0.0 < f1 < 1.0


def test_rouge_l_score():
    expected = "the cat sat on the mat"
    answer = "the cat sat on the mat"
    assert rouge_l_score(answer, expected) == pytest.approx(1.0)

    # Permuted tokens reduce LCS
    permuted = "mat the on sat cat the"
    rl = rouge_l_score(permuted, expected)
    assert 0.0 < rl < 1.0

    assert rouge_l_score("", expected) == 0.0
    assert rouge_l_score("", "") == 1.0


def test_bleu_score():
    expected = "the quick brown fox jumps over the lazy dog"
    exact = "the quick brown fox jumps over the lazy dog"
    assert bleu_score(exact, expected) == pytest.approx(1.0)

    disjoint = "completely unrelated sentence with no overlap whatsoever"
    assert bleu_score(disjoint, expected) == 0.0

    assert bleu_score("", expected) == 0.0
    assert bleu_score(exact, "") == 0.0
