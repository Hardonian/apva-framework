"""OpenAI native client wrapper for APVA telemetry ingestion."""

from __future__ import annotations

import inspect
import time
import uuid
from typing import Any

from apva_sdk.client import APVATelemetryClient, TelemetryEventPayload, get_default_client


class APVAOpenAI:
    """Wrapper around the official openai Python client (sync & async)."""

    def __init__(
        self,
        client: Any,
        app_name: str = "openai-app",
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
        if name == "chat":
            return _APVAChatProxy(
                attr,
                self.app_name,
                self.session_id,
                self.human_baseline_time,
                self.guardrail_latency_tax,
                self.hourly_rate_usd,
                self.is_shadow,
                self._apva_client,
            )
        if name == "embeddings":
            return _APVAEmbeddingsProxy(
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


class _APVAChatProxy:
    def __init__(
        self,
        chat: Any,
        app_name: str,
        session_id: str,
        baseline: float,
        tax: float,
        rate: float | None,
        shadow: bool,
        client: APVATelemetryClient,
    ) -> None:
        self._chat = chat
        self.app_name = app_name
        self.session_id = session_id
        self.human_baseline_time = baseline
        self.guardrail_latency_tax = tax
        self.hourly_rate_usd = rate
        self.is_shadow = shadow
        self._apva_client = client

    @property
    def completions(self) -> _APVACompletionsProxy:
        return _APVACompletionsProxy(
            self._chat.completions,
            self.app_name,
            self.session_id,
            self.human_baseline_time,
            self.guardrail_latency_tax,
            self.hourly_rate_usd,
            self.is_shadow,
            self._apva_client,
        )


class _APVACompletionsProxy:
    def __init__(
        self,
        completions: Any,
        app_name: str,
        session_id: str,
        baseline: float,
        tax: float,
        rate: float | None,
        shadow: bool,
        client: APVATelemetryClient,
    ) -> None:
        self._completions = completions
        self.app_name = app_name
        self.session_id = session_id
        self.human_baseline_time = baseline
        self.guardrail_latency_tax = tax
        self.hourly_rate_usd = rate
        self.is_shadow = shadow
        self._apva_client = client

    def create(self, *args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        result = self._completions.create(*args, **kwargs)

        if inspect.iscoroutine(result):
            async def _async_wrapper() -> Any:
                response = await result
                self._emit_telemetry(start_time, response, kwargs)
                return response
            return _async_wrapper()

        self._emit_telemetry(start_time, result, kwargs)
        return result

    async def acreate(self, *args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        create_fn = getattr(self._completions, "acreate", self._completions.create)
        res = create_fn(*args, **kwargs)
        response = await res if inspect.iscoroutine(res) else res
        self._emit_telemetry(start_time, response, kwargs)
        return response

    def _emit_telemetry(self, start_time: float, response: Any, kwargs: dict[str, Any]) -> None:
        duration_min = (time.perf_counter() - start_time) / 60.0
        run_id = getattr(response, "id", f"run-{uuid.uuid4().hex[:12]}")
        usage = getattr(response, "usage", None)
        meta = {
            "model": kwargs.get("model", "unknown"),
            "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
            "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
            "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
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


class _APVAEmbeddingsProxy:
    def __init__(
        self,
        embeddings: Any,
        app_name: str,
        session_id: str,
        baseline: float,
        tax: float,
        rate: float | None,
        shadow: bool,
        client: APVATelemetryClient,
    ) -> None:
        self._embeddings = embeddings
        self.app_name = app_name
        self.session_id = session_id
        self.human_baseline_time = baseline
        self.guardrail_latency_tax = tax
        self.hourly_rate_usd = rate
        self.is_shadow = shadow
        self._apva_client = client

    def create(self, *args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        result = self._embeddings.create(*args, **kwargs)

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
        run_id = f"emb-{uuid.uuid4().hex[:12]}"
        meta = {
            "type": "embeddings",
            "model": kwargs.get("model", "text-embedding-3-small"),
        }
        payload = TelemetryEventPayload(
            app_name=self.app_name,
            session_id=self.session_id,
            run_id=run_id,
            human_baseline_time=self.human_baseline_time,
            ai_augmented_time=duration_min,
            guardrail_latency_tax=self.guardrail_latency_tax,
            session_iterations=1,
            hourly_rate_usd=self.hourly_rate_usd,
            is_shadow=self.is_shadow,
            metadata=meta,
        )
        self._apva_client.ingest_async(payload)


__all__ = ["APVAOpenAI"]
