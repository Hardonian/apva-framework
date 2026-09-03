"""APVA Enterprise Integration for LlamaIndex.

This package provides native, zero-code instrumentation for LlamaIndex.
By registering the APVACallbackHandler into the global Settings / CallbackManager,
all RAG retrieval metrics and generation latencies are streamed directly
to the APVA backend.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from apva_sdk.client import APVATelemetryClient, TelemetryEventPayload, get_default_client

try:
    from llama_index.core.callbacks.base_handler import BaseCallbackHandler
    from llama_index.core.callbacks.schema import CBEventType, EventPayload
except ImportError:

    class BaseCallbackHandler:  # type: ignore[no-redef]
        """Fallback base callback handler when llama-index-core is not installed."""

        def __init__(
            self,
            event_starts_to_ignore: list[Any] | None = None,
            event_ends_to_ignore: list[Any] | None = None,
        ) -> None:
            self.event_starts_to_ignore = event_starts_to_ignore or []
            self.event_ends_to_ignore = event_ends_to_ignore or []

    class CBEventType:  # type: ignore[no-redef]
        """Mock CBEventType enum."""

        CHUNKING = "chunking"
        NODE_PARSING = "node_parsing"
        EMBEDDING = "embedding"
        LLM = "llm"
        QUERY = "query"
        RETRIEVE = "retrieve"
        SYNTHESIZE = "synthesize"
        TREE = "tree"
        SUB_QUESTION = "sub_question"

    class EventPayload:  # type: ignore[no-redef]
        """Mock EventPayload keys."""

        DOCUMENTS = "documents"
        CHUNKS = "chunks"
        NODES = "nodes"
        PROMPT = "prompt"
        MESSAGES = "messages"
        RESPONSE = "response"
        QUERY_STR = "query_str"
        SUB_QUESTIONS = "sub_questions"


logger = logging.getLogger(__name__)


class APVACallbackHandler(BaseCallbackHandler):
    """LlamaIndex callback handler for automated RAG evaluation & TVY telemetry."""

    def __init__(
        self,
        api_key: str | None = None,
        app_name: str = "llamaindex-app",
        session_id: str | None = None,
        human_baseline_time: float = 0.0,
        guardrail_latency_tax: float = 0.0,
        hourly_rate_usd: float | None = None,
        is_shadow: bool = False,
        client: APVATelemetryClient | None = None,
        endpoint: str | None = None,
    ) -> None:
        super().__init__(
            event_starts_to_ignore=[],
            event_ends_to_ignore=[],
        )
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
        self._start_times: dict[str, float] = {}
        self._contexts: dict[str, list[str]] = {}

    def on_event_start(
        self,
        event_type: CBEventType | str,
        payload: dict[str, Any] | None = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> str:
        """Track retrieval and generation start times."""
        eid = event_id or uuid.uuid4().hex
        self._start_times[eid] = time.perf_counter()
        return eid

    def on_event_end(
        self,
        event_type: CBEventType | str,
        payload: dict[str, Any] | None = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> None:
        """Capture context and generated answers and stream telemetry."""
        eid = event_id or ""
        start_time = self._start_times.pop(eid, None)
        ev_str = str(event_type).lower()

        # Capture retrieved contexts
        if "retrieve" in ev_str and payload:
            nodes = payload.get("nodes") or []
            contexts = [getattr(n, "text", str(n)) for n in nodes]
            if parent_id:
                self._contexts.setdefault(parent_id, []).extend(contexts)

        # Emit telemetry on top-level query or LLM completion
        if ("query" in ev_str or "llm" in ev_str) and start_time is not None:
            elapsed_min = (time.perf_counter() - start_time) / 60.0
            retrieved = self._contexts.pop(eid, self._contexts.pop(parent_id, []))
            meta = {
                "event_type": str(event_type),
                "has_retrieved_context": len(retrieved) > 0,
                "context_chunks_count": len(retrieved),
            }
            telemetry = TelemetryEventPayload(
                app_name=self.app_name,
                session_id=self.session_id,
                run_id=eid or uuid.uuid4().hex,
                human_baseline_time=self.human_baseline_time,
                ai_augmented_time=elapsed_min,
                guardrail_latency_tax=self.guardrail_latency_tax,
                session_iterations=1,
                hourly_rate_usd=self.hourly_rate_usd,
                is_shadow=self.is_shadow,
                metadata=meta,
            )
            self.client.ingest_async(telemetry)
            logger.debug(
                "[apva-llamaindex] Emitted telemetry for %s event %s (%.4fm)",
                self.app_name,
                ev_str,
                elapsed_min,
            )

    def start_trace(self, trace_id: str | None = None) -> None:
        """Run when an overall trace begins."""
        pass

    def end_trace(
        self,
        trace_id: str | None = None,
        trace_map: dict[str, list[str]] | None = None,
    ) -> None:
        """Run when an overall trace completes."""
        pass

    def flush(self, timeout: float = 2.0) -> None:
        """Flush the underlying client queue."""
        if hasattr(self.client, "close"):
            self.client.close(timeout=timeout)


__all__ = ["APVACallbackHandler"]
