"""Tests for SDK telemetry client simplicity."""

from __future__ import annotations

import threading

import pytest

from apva_sdk.client import APVATelemetryClient, TelemetryEventPayload


def test_ingest_sync(monkeypatch: pytest.MonkeyPatch):
    posted: list = []

    class FakeResponse:
        def raise_for_status(self):
            return None

    class FakeClient:
        def post(self, url, headers=None, json=None):
            posted.append(json)
            return FakeResponse()

    monkeypatch.setattr(
        "apva_sdk.client.httpx.Client", lambda **kwargs: FakeClient()
    )
    client = APVATelemetryClient(
        endpoint="http://backend/ingest",
        app_name="app",
        session_id="s",
    )
    payload = TelemetryEventPayload(
        app_name="app",
        session_id="s",
        run_id="r",
        human_baseline_time=0.0,
        ai_augmented_time=1.0,
        guardrail_latency_tax=0.0,
        metadata={},
    )
    client.ingest_async(payload)
    client._thread.join(timeout=1.0)
    assert len(posted) == 1
    assert posted[0]["run_id"] == payload.run_id
    client.close(timeout=1.0)
