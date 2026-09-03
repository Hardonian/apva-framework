"""APVA Enterprise Integration for LangChain.

This package provides native, zero-code instrumentation for LangChain.
By wrapping your LLM Chains, Agents, or Retrievers with APVACallbackHandler,
telemetry is automatically intercepted, enriched, and streamed to the APVA backend.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from apva_sdk.client import APVATelemetryClient, TelemetryEventPayload, get_default_client

try:
    from langchain_core.callbacks.base import BaseCallbackHandler
except ImportError:

    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Fallback callback handler base when langchain_core is not installed."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass


logger = logging.getLogger(__name__)


class APVACallbackHandler(BaseCallbackHandler):
    """LangChain callback handler for automated TVY instrumentation."""

    def __init__(
        self,
        api_key: str | None = None,
        app_name: str = "langchain-app",
        session_id: str | None = None,
        human_baseline_time: float = 0.0,
        guardrail_latency_tax: float = 0.0,
        hourly_rate_usd: float | None = None,
        is_shadow: bool = False,
        client: APVATelemetryClient | None = None,
        endpoint: str | None = None,
    ) -> None:
        super().__init__()
        self.api_key = api_key
        self.app_name = app_name
        self.session_id = session_id or uuid.uuid4().hex
        self.human_baseline_time = float(human_baseline_time)
        self.guardrail_latency_tax = float(guardrail_latency_tax)
        self.hourly_rate_usd = hourly_rate_usd
        self.is_shadow = is_shadow
        self.client = client or (
            APVATelemetryClient(
                api_key=api_key, app_name=app_name, session_id=self.session_id, endpoint=endpoint
            )
            if (api_key or endpoint)
            else get_default_client()
        )
        self._run_start_times: dict[str, float] = {}
        self._run_metadata: dict[str, dict[str, Any]] = {}

    def on_chain_start(
        self,
        serialized: dict[str, Any] | None,
        inputs: dict[str, Any] | None,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Called when a chain starts running."""
        key = str(run_id or uuid.uuid4())
        self._run_start_times[key] = time.perf_counter()
        self._run_metadata[key] = {
            "type": "chain",
            "tags": tags or [],
            "custom": metadata or {},
        }

    def on_chain_end(
        self,
        outputs: dict[str, Any] | None,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        """Called when a chain finishes. Auto-emits telemetry."""
        key = str(run_id or "")
        start_time = self._run_start_times.pop(key, None)
        meta = self._run_metadata.pop(key, {})
        if start_time is not None:
            elapsed_min = (time.perf_counter() - start_time) / 60.0
            payload = TelemetryEventPayload(
                app_name=self.app_name,
                session_id=self.session_id,
                run_id=key or uuid.uuid4().hex,
                human_baseline_time=self.human_baseline_time,
                ai_augmented_time=elapsed_min,
                guardrail_latency_tax=self.guardrail_latency_tax,
                session_iterations=1,
                hourly_rate_usd=self.hourly_rate_usd,
                is_shadow=self.is_shadow,
                metadata=meta,
            )
            self.client.ingest_async(payload)
            logger.debug(
                "[apva-langchain] Auto-emitted TVY telemetry for %s (%.4fm)",
                self.app_name,
                elapsed_min,
            )

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        """Called when a chain errors out."""
        key = str(run_id or "")
        start_time = self._run_start_times.pop(key, None)
        meta = self._run_metadata.pop(key, {})
        if start_time is not None:
            elapsed_min = (time.perf_counter() - start_time) / 60.0
            meta["error"] = str(error)
            payload = TelemetryEventPayload(
                app_name=self.app_name,
                session_id=self.session_id,
                run_id=key or uuid.uuid4().hex,
                human_baseline_time=self.human_baseline_time,
                ai_augmented_time=elapsed_min,
                guardrail_latency_tax=self.guardrail_latency_tax,
                session_iterations=1,
                hourly_rate_usd=self.hourly_rate_usd,
                is_shadow=self.is_shadow,
                metadata=meta,
            )
            self.client.ingest_async(payload)

    def on_llm_start(
        self,
        serialized: dict[str, Any] | None,
        prompts: list[str] | None,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM starts running."""
        key = str(run_id or uuid.uuid4())
        self._run_start_times[key] = time.perf_counter()
        self._run_metadata[key] = {
            "type": "llm",
            "tags": tags or [],
            "custom": metadata or {},
        }

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM ends."""
        key = str(run_id or "")
        start_time = self._run_start_times.pop(key, None)
        meta = self._run_metadata.pop(key, {})
        if start_time is not None:
            elapsed_min = (time.perf_counter() - start_time) / 60.0
            payload = TelemetryEventPayload(
                app_name=self.app_name,
                session_id=self.session_id,
                run_id=key or uuid.uuid4().hex,
                human_baseline_time=self.human_baseline_time,
                ai_augmented_time=elapsed_min,
                guardrail_latency_tax=self.guardrail_latency_tax,
                session_iterations=1,
                hourly_rate_usd=self.hourly_rate_usd,
                is_shadow=self.is_shadow,
                metadata=meta,
            )
            self.client.ingest_async(payload)

    def flush(self, timeout: float = 2.0) -> None:
        """Flush the underlying client queue."""
        if hasattr(self.client, "close"):
            self.client.close(timeout=timeout)


__all__ = ["APVACallbackHandler"]
