"""Tests for APVATelemetryClient batching and flushing."""

from __future__ import annotations

import pytest
from apva_sdk.client import APVATelemetryClient, TelemetryEventPayload


def test_batch_ingest_and_flush(monkeypatch: pytest.MonkeyPatch):
    posted: list = []

    class FakeResponse:
        def raise_for_status(self):
            return None

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, headers=None, json=None):
            posted.append(json)
            return FakeResponse()

    monkeypatch.setattr("apva_sdk.client.httpx.Client", lambda **kwargs: FakeClient())

    client = APVATelemetryClient(
        endpoint="http://backend/ingest",
        app_name="batch-test",
        session_id="batch-s",
    )

    payloads = [
        TelemetryEventPayload(
            app_name="batch-test",
            session_id="batch-s",
            run_id=f"run-{i}",
            human_baseline_time=5.0,
            ai_augmented_time=1.0,
            guardrail_latency_tax=0.0,
        )
        for i in range(5)
    ]

    enqueued = client.ingest_batch(payloads)
    assert enqueued == 5

    client.flush(timeout=1.0)
    client.close(timeout=1.0)
    assert len(posted) == 5
