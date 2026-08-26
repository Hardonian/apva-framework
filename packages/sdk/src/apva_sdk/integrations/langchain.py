"""LangChain integration for APVA telemetry ingestion."""

from __future__ import annotations

import time
from typing import Any

from apva_sdk.client import TelemetryEventPayload, get_default_client

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:
    BaseCallbackHandler = object


class APVALangChainCallbackHandler(BaseCallbackHandler):
    """Zero-code LangChain callback for automatic APVA telemetry."""

    def __init__(self, app_name: str, session_id: str, human_baseline_time: float, guardrail_latency_tax: float = 0.0) -> None:
        self.app_name = app_name
        self.session_id = session_id
        self.human_baseline_time = human_baseline_time
        self.guardrail_latency_tax = guardrail_latency_tax
        self.start_times: dict[str, float] = {}
        self.client = get_default_client()

    def on_chain_start(self, serialized: dict[str, Any], inputs: dict[str, Any], *, run_id: str, **kwargs: Any) -> None:
        self.start_times[str(run_id)] = time.time()

    def on_chain_end(self, outputs: dict[str, Any], *, run_id: str, **kwargs: Any) -> None:
        start_time = self.start_times.pop(str(run_id), None)
        if start_time is not None:
            ai_augmented_time = (time.time() - start_time) / 60.0  # Convert to minutes
            payload = TelemetryEventPayload(
                app_name=self.app_name,
                session_id=self.session_id,
                run_id=str(run_id),
                human_baseline_time=self.human_baseline_time,
                ai_augmented_time=ai_augmented_time,
                guardrail_latency_tax=self.guardrail_latency_tax,
            )
            self.client.ingest_async(payload)
