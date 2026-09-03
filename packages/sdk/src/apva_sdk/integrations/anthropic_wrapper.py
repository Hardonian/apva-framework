"""Anthropic native client wrapper for APVA telemetry ingestion."""

from __future__ import annotations

import inspect
import time
import uuid
from typing import Any

from apva_sdk.client import APVATelemetryClient, TelemetryEventPayload, get_default_client


class APVAAnthropic:
    """Wrapper around the official Anthropic Python client (sync & async)."""

    def __init__(
        self,
        client: Any,
        app_name: str = "anthropic-app",
        session_id: str | None = None,
        human_baseline_time: float = 0.0,
        guardrail_latency_tax: float = 0.0,
        hourly_rate_usd: float | None = None,
        is_shadow: bool = False,
        apva_client: APVATelemetryClient | None = None,
    ) -> None:
        self._client = client
        self.app_name = app_name
        self.session_id = session_id or uuid.uuid4().hex
        self.human_baseline_time = float(human_baseline_time)
        self.guardrail_latency_tax = float(guardrail_latency_tax)
        self.hourly_rate_usd = hourly_rate_usd
        self.is_shadow = is_shadow
        self._apva_client = apva_client or get_default_client()

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._client, name)
        if name == "messages":
            return _APVAMessagesProxy(
                attr,
                self.app_name,
                self.session_id,
                self.human_baseline_time,
                self.guardrail_latency_tax,
                self.hourly_rate_usd,
                self.is_shadow,
                self._apva_client,
            )
        return attr


class _APVAMessagesProxy:
    def __init__(
        self,
        messages: Any,
        app_name: str,
        session_id: str,
        baseline: float,
        tax: float,
        rate: float | None,
        shadow: bool,
        client: APVATelemetryClient,
    ) -> None:
        self._messages = messages
        self.app_name = app_name
        self.session_id = session_id
        self.human_baseline_time = baseline
        self.guardrail_latency_tax = tax
        self.hourly_rate_usd = rate
        self.is_shadow = shadow
        self._apva_client = client

    def create(self, *args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        result = self._messages.create(*args, **kwargs)

        if inspect.iscoroutine(result):

            async def _async_wrapper() -> Any:
                response = await result
                self._emit_telemetry(start_time, response, kwargs)
                return response

            return _async_wrapper()

        self._emit_telemetry(start_time, result, kwargs)
        return result

    def _emit_telemetry(self, start_time: float, response: Any, kwargs: dict[str, Any]) -> None:
        duration_min = (time.perf_counter() - start_time) / 60.0
        run_id = getattr(response, "id", f"msg-{uuid.uuid4().hex[:12]}")
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "output_tokens", 0) if usage else 0

        meta = {
            "provider": "anthropic",
            "model": kwargs.get("model", "unknown"),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }

        payload = TelemetryEventPayload(
            app_name=self.app_name,
            session_id=self.session_id,
            run_id=str(run_id),
            human_baseline_time=self.human_baseline_time,
            ai_augmented_time=duration_min,
            guardrail_latency_tax=self.guardrail_latency_tax,
            session_iterations=1,
            hourly_rate_usd=self.hourly_rate_usd,
            is_shadow=self.is_shadow,
            metadata=meta,
        )
        self._apva_client.ingest_async(payload)


__all__ = ["APVAAnthropic"]
