"""Non-blocking APVA telemetry client."""

from __future__ import annotations

import os
import queue
import threading
import uuid
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field


class TelemetryEventPayload(BaseModel):
    """Payload sent by the APVA SDK to the backend.

    Attributes:
        app_name: Client application identifier.
        session_id: Client session identifier.
        run_id: Client run identifier.
        human_baseline_time: Human baseline time in minutes.
        ai_augmented_time: AI-augmented time in minutes.
        guardrail_latency_tax: Guardrail latency tax in minutes.
        session_iterations: Session iteration count.
        metadata: Optional structured metadata.
    """

    model_config = ConfigDict(extra="forbid")

    app_name: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    human_baseline_time: float = Field(..., ge=0.0)
    ai_augmented_time: float = Field(..., ge=0.0)
    guardrail_latency_tax: float = Field(..., ge=0.0)
    session_iterations: int = Field(..., ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class APVATelemetryClient:
    """Async-friendly telemetry client with a background sender thread.

    The public ``ingest_async`` method never blocks the caller. It enqueues the
    event and a daemon thread sends payloads to the backend over HTTP.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        app_name: str = "apva-sdk-client",
        session_id: str | None = None,
        queue_size: int = 1000,
    ) -> None:
        """Initialize the telemetry client.

        Args:
            endpoint: Backend ingestion endpoint. Defaults to APVA_INGEST_URL or
                ``http://localhost:8000/api/v1/telemetry/ingest``.
            api_key: Optional API key sent in the ``Authorization`` header.
            app_name: Default application name for payloads.
            session_id: Default session ID for payloads.
            queue_size: Maximum queued telemetry events.
        """
        self.endpoint = endpoint or os.getenv(
            "APVA_INGEST_URL",
            "http://localhost:8000/api/v1/telemetry/ingest",
        )
        self.api_key = api_key
        self.app_name = app_name
        self.session_id = session_id or uuid.uuid4().hex
        self._queue: queue.Queue[TelemetryEventPayload] = queue.Queue(maxsize=queue_size)
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._sender_loop, daemon=True)
        self._thread.start()

    def ingest_async(
        self,
        payload: TelemetryEventPayload,
    ) -> bool:
        """Enqueue a telemetry payload without blocking.

        Args:
            payload: Validated telemetry payload.

        Returns:
            bool: ``True`` if queued, ``False`` if the queue is full.
        """
        try:
            self._queue.put_nowait(payload)
            return True
        except queue.Full:
            return False

    def ingest(self, payload: TelemetryEventPayload) -> None:
        """Send a telemetry payload synchronously.

        Args:
            payload: Validated telemetry payload.
        """
        self._send(payload)

    def close(self, timeout: float = 2.0) -> None:
        """Stop the background sender thread.

        Args:
            timeout: Maximum seconds to wait for queued events to drain.
        """
        self._stop_event.set()
        self._thread.join(timeout=timeout)

    def _sender_loop(self) -> None:
        """Drain the queue and send telemetry events to the backend."""
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                payload = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            self._send(payload)

    def _send(self, payload: TelemetryEventPayload) -> None:
        """Send one payload to the backend.

        Args:
            payload: Validated telemetry payload.
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        with httpx.Client(timeout=5.0) as client:
            response = client.post(self.endpoint, headers=headers, json=payload.model_dump())
            response.raise_for_status()
