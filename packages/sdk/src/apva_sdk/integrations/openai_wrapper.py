"""OpenAI native client wrapper for APVA telemetry ingestion."""

from __future__ import annotations

import time
from typing import Any

from apva_sdk.client import TelemetryEventPayload, get_default_client

class APVAOpenAI:
    """Wrapper around the official openai Python client."""
    
    def __init__(self, client: Any, app_name: str, session_id: str, human_baseline_time: float, guardrail_latency_tax: float = 0.0):
        self._client = client
        self.app_name = app_name
        self.session_id = session_id
        self.human_baseline_time = human_baseline_time
        self.guardrail_latency_tax = guardrail_latency_tax
        self._apva_client = get_default_client()
        
    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._client, name)
        if name == "chat":
            return _APVAChatProxy(
                attr, 
                self.app_name, 
                self.session_id, 
                self.human_baseline_time, 
                self.guardrail_latency_tax, 
                self._apva_client
            )
        return attr

class _APVAChatProxy:
    def __init__(self, chat: Any, app_name: str, session_id: str, baseline: float, tax: float, client: Any):
        self._chat = chat
        self.app_name = app_name
        self.session_id = session_id
        self.human_baseline_time = baseline
        self.guardrail_latency_tax = tax
        self._apva_client = client
        
    @property
    def completions(self) -> Any:
        return _APVACompletionsProxy(
            self._chat.completions,
            self.app_name,
            self.session_id,
            self.human_baseline_time,
            self.guardrail_latency_tax,
            self._apva_client
        )
        
class _APVACompletionsProxy:
    def __init__(self, completions: Any, app_name: str, session_id: str, baseline: float, tax: float, client: Any):
        self._completions = completions
        self.app_name = app_name
        self.session_id = session_id
        self.human_baseline_time = baseline
        self.guardrail_latency_tax = tax
        self._apva_client = client

    def create(self, *args, **kwargs) -> Any:
        start_time = time.time()
        response = self._completions.create(*args, **kwargs)
        duration_min = (time.time() - start_time) / 60.0
        
        run_id = getattr(response, "id", f"run-{int(start_time)}")
        
        payload = TelemetryEventPayload(
            app_name=self.app_name,
            session_id=self.session_id,
            run_id=run_id,
            human_baseline_time=self.human_baseline_time,
            ai_augmented_time=duration_min,
            guardrail_latency_tax=self.guardrail_latency_tax,
        )
        self._apva_client.ingest_async(payload)
        return response
