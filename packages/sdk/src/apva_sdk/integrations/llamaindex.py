"""LlamaIndex integration for APVA telemetry ingestion."""

from __future__ import annotations

import time
from typing import Any

from apva_sdk.client import TelemetryEventPayload, get_default_client

try:
    from llama_index.core.callbacks.base_handler import BaseCallbackHandler
    from llama_index.core.callbacks.schema import CBEventType
except ImportError:
    class BaseCallbackHandler:
        def __init__(self, *args, **kwargs): pass
    CBEventType = Any

class APVALlamaIndexCallback(BaseCallbackHandler):
    """Zero-code LlamaIndex callback for automatic APVA telemetry."""

    def __init__(self, app_name: str, session_id: str, human_baseline_time: float, guardrail_latency_tax: float = 0.0) -> None:
        super().__init__(event_starts_to_ignore=[], event_ends_to_ignore=[])
        self.app_name = app_name
        self.session_id = session_id
        self.human_baseline_time = human_baseline_time
        self.guardrail_latency_tax = guardrail_latency_tax
        self.start_times: dict[str, float] = {}
        self.client = get_default_client()

    def on_event_start(
        self,
        event_type: CBEventType,
        payload: dict[str, Any] | None = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> str:
        """Run when an event starts."""
        if str(event_type) == "CBEventType.QUERY":
            self.start_times[event_id] = time.time()
        return event_id

    def on_event_end(
        self,
        event_type: CBEventType,
        payload: dict[str, Any] | None = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> None:
        """Run when an event ends."""
        if str(event_type) == "CBEventType.QUERY" and event_id in self.start_times:
            start_time = self.start_times.pop(event_id)
            ai_augmented_time = (time.time() - start_time) / 60.0
            
            telemetry = TelemetryEventPayload(
                app_name=self.app_name,
                session_id=self.session_id,
                run_id=event_id,
                human_baseline_time=self.human_baseline_time,
                ai_augmented_time=ai_augmented_time,
                guardrail_latency_tax=self.guardrail_latency_tax,
            )
            self.client.ingest_async(telemetry)

    def start_trace(self, trace_id: str | None = None) -> None:
        """No-op."""
        pass

    def end_trace(self, trace_id: str | None = None, trace_map: dict[str, list[str]] | None = None) -> None:
        """No-op."""
        pass
