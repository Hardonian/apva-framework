"""Canonical text-matching scoring functions for the APVA framework.

This module is the **single source of truth** for all token-level retrieval
metrics used by the CLI, backend evaluation service, and SDK.  Every other
module that needs these functions MUST import from here rather than defining
local copies.

All scores return a ``float`` in the inclusive range ``[0.0, 1.0]``.
"""

from __future__ import annotations

import re


def tokenize(text: str) -> list[str]:
    """Tokenize text into lower-case alphanumeric word spans.

    Hyphenated and apostrophised compounds (e.g. ``state-of-the-art``,
    ``don't``) are kept as single tokens.

    Args:
        text: Raw input text.

    Returns:
        list[str]: Normalized word tokens.
    """
    return re.findall(r"[a-zA-Z0-9]+(?:[-'][a-zA-Z0-9]+)*", text.lower())


def exact_span_recall(answer: str, expected_answer: str) -> float:
    """Fraction of expected-answer tokens found exactly in the answer.

    This is a **recall-oriented** metric: it measures how many of the
    required evidence tokens appear anywhere in the generated answer.

    Args:
        answer: Generated / candidate answer text.
        expected_answer: Golden reference answer text.

    Returns:
        float: Recall score in ``[0.0, 1.0]``.
    """
    expected_tokens = tokenize(expected_answer)
    answer_tokens = tokenize(answer)
    if not expected_tokens:
        return 1.0 if not answer_tokens else 0.0
    answer_token_set = set(answer_tokens)
    found = sum(1 for token in expected_tokens if token in answer_token_set)
    return found / len(expected_tokens)


def token_precision(answer: str, expected_answer: str) -> float:
    """Fraction of answer tokens that appear in the expected answer.

    This is a **precision-oriented** metric: it penalises hallucinated
    tokens that are not grounded in the reference.

    Args:
        answer: Generated / candidate answer text.
        expected_answer: Golden reference answer text.

    Returns:
        float: Precision score in ``[0.0, 1.0]``.
    """
    expected_tokens = set(tokenize(expected_answer))
    answer_tokens = set(tokenize(answer))
    if not answer_tokens:
        return 1.0 if not expected_tokens else 0.0
    return len(expected_tokens & answer_tokens) / len(answer_tokens)


def f1_score(answer: str, expected_answer: str) -> float:
    """Harmonic mean of :func:`exact_span_recall` and :func:`token_precision`.

    F1 balances recall (did we find the evidence?) and precision (did we
    hallucinate beyond the evidence?).

    Args:
        answer: Generated / candidate answer text.
        expected_answer: Golden reference answer text.

    Returns:
        float: F1 score in ``[0.0, 1.0]``.
    """
    recall = exact_span_recall(answer, expected_answer)
    precision = token_precision(answer, expected_answer)
    if recall + precision == 0.0:
        return 0.0
    return 2.0 * (precision * recall) / (precision + recall)


def _lcs_length(seq_a: list[str], seq_b: list[str]) -> int:
    """Compute the length of the Longest Common Subsequence (LCS).

    Uses the standard dynamic-programming algorithm in ``O(m*n)`` time
    and ``O(min(m, n))`` space (rolling two rows).

    Args:
        seq_a: First token sequence.
        seq_b: Second token sequence.

    Returns:
        int: Length of the LCS.
    """
    if len(seq_a) < len(seq_b):
        seq_a, seq_b = seq_b, seq_a
    prev = [0] * (len(seq_b) + 1)
    curr = [0] * (len(seq_b) + 1)
    for token_a in seq_a:
        for j, token_b in enumerate(seq_b, start=1):
            if token_a == token_b:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev, curr = curr, [0] * (len(seq_b) + 1)
    return max(prev)


def rouge_l_score(answer: str, expected_answer: str) -> float:
    """ROUGE-L F-measure based on the Longest Common Subsequence.

    ROUGE-L captures sentence-level structural similarity by rewarding
    contiguous ordering of matching tokens without requiring exact
    positional alignment.

    Args:
        answer: Generated / candidate answer text.
        expected_answer: Golden reference answer text.

    Returns:
        float: ROUGE-L F1 score in ``[0.0, 1.0]``.
    """
    answer_tokens = tokenize(answer)
    expected_tokens = tokenize(expected_answer)
    if not expected_tokens and not answer_tokens:
        return 1.0
    if not expected_tokens or not answer_tokens:
        return 0.0
    lcs = _lcs_length(answer_tokens, expected_tokens)
    recall = lcs / len(expected_tokens)
    precision = lcs / len(answer_tokens)
    if recall + precision == 0.0:
        return 0.0
    return 2.0 * (precision * recall) / (precision + recall)


def _count_ngrams(tokens: list[str], n: int) -> dict[tuple[str, ...], int]:
    """Count n-gram occurrences in a token list.

    Args:
        tokens: Token sequence.
        n: N-gram order (1 for unigrams, 2 for bigrams, etc.).

    Returns:
        dict: Mapping from n-gram tuple to occurrence count.
    """
    counts: dict[tuple[str, ...], int] = {}
    for i in range(len(tokens) - n + 1):
        gram = tuple(tokens[i : i + n])
        counts[gram] = counts.get(gram, 0) + 1
    return counts


def bleu_score(
    answer: str,
    expected_answer: str,
    max_n: int = 4,
) -> float:
    """Simplified corpus-free BLEU score up to ``max_n``-grams.

    Uses uniform weights across n-gram orders and applies a brevity
    penalty when the candidate is shorter than the reference.

    .. note::
        This is a lightweight single-sentence BLEU intended for fast
        CI/CD gating — not a replacement for ``sacrebleu``.

    Args:
        answer: Generated / candidate answer text.
        expected_answer: Golden reference answer text.
        max_n: Maximum n-gram order (default 4).

    Returns:
        float: BLEU score in ``[0.0, 1.0]``.
    """
    import math

    answer_tokens = tokenize(answer)
    expected_tokens = tokenize(expected_answer)
    if not answer_tokens or not expected_tokens:
        return 0.0

    # Brevity penalty
    bp = min(1.0, math.exp(1.0 - len(expected_tokens) / len(answer_tokens)))

    log_avg = 0.0
    effective_n = 0
    for n in range(1, max_n + 1):
        candidate_ngrams = _count_ngrams(answer_tokens, n)
        reference_ngrams = _count_ngrams(expected_tokens, n)
        if not candidate_ngrams:
            break
        clipped = 0
        total = 0
        for gram, count in candidate_ngrams.items():
            clipped += min(count, reference_ngrams.get(gram, 0))
            total += count
        if total == 0 or clipped == 0:
            return 0.0
        log_avg += math.log(clipped / total)
        effective_n += 1

    if effective_n == 0:
        return 0.0
    return bp * math.exp(log_avg / effective_n)
