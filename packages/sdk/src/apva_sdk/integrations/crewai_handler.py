"""CrewAI multi-agent framework integration for APVA telemetry capture."""

from __future__ import annotations

import inspect
import time
import uuid
from typing import Any

from apva_sdk.client import APVATelemetryClient, TelemetryEventPayload, get_default_client


class APVACrewAI:
    """Wrapper and task hook for CrewAI multi-agent executions.

    Calculates True Value Yield across multi-agent workflows by comparing
    the human baseline for the entire project deliverable against the wall-clock
    orchestration time and human supervisory oversight.
    """

    def __init__(
        self,
        crew: Any,
        app_name: str = "crewai-multi-agent",
        session_id: str | None = None,
        human_baseline_time: float = 60.0,
        guardrail_latency_tax: float = 0.5,
        hourly_rate_usd: float | None = None,
        is_shadow: bool = False,
        client: APVATelemetryClient | None = None,
    ) -> None:
        """Initialize the CrewAI APVA wrapper.

        Args:
            crew: The CrewAI Crew instance.
            app_name: Application name identifier.
            session_id: Optional session identifier.
            human_baseline_time: Human time in minutes to complete all tasks manually.
            guardrail_latency_tax: Guardrail / verification latency tax in minutes.
            hourly_rate_usd: Fully loaded hourly compensation of practitioner.
            is_shadow: Shadow mode evaluation flag.
            client: Optional APVATelemetryClient instance.
        """
        self._crew = crew
        self.app_name = app_name
        self.session_id = session_id or uuid.uuid4().hex
        self.human_baseline_time = float(human_baseline_time)
        self.guardrail_latency_tax = float(guardrail_latency_tax)
        self.hourly_rate_usd = hourly_rate_usd
        self.is_shadow = is_shadow
        self._client = client or get_default_client()

    def kickoff(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the crew synchronously and record multi-agent TVY telemetry."""
        start_time = time.perf_counter()
        result = self._crew.kickoff(*args, **kwargs)
        duration_min = (time.perf_counter() - start_time) / 60.0
        self._emit_telemetry(duration_min, result)
        return result

    async def kickoff_async(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the crew asynchronously and record multi-agent TVY telemetry."""
        start_time = time.perf_counter()
        if hasattr(self._crew, "kickoff_async"):
            result = await self._crew.kickoff_async(*args, **kwargs)
        else:
            result = self._crew.kickoff(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result
        duration_min = (time.perf_counter() - start_time) / 60.0
        self._emit_telemetry(duration_min, result)
        return result

    def _emit_telemetry(self, duration_min: float, result: Any) -> None:
        """Construct and enqueue the telemetry event."""
        run_id = f"crew-{uuid.uuid4().hex[:12]}"

        # Attempt to inspect crew agents and task counts if accessible
        agents_count = len(getattr(self._crew, "agents", []))
        tasks_count = len(getattr(self._crew, "tasks", []))

        # Attempt to inspect usage if present
        usage_data = getattr(result, "token_usage", None) or getattr(self._crew, "usage_metrics", None)
        total_tokens = getattr(usage_data, "total_tokens", 0) if usage_data else 0

        metadata: dict[str, Any] = {
            "framework": "crewai",
            "agents_count": agents_count,
            "tasks_count": tasks_count,
            "total_tokens": total_tokens,
        }

        payload = TelemetryEventPayload(
            app_name=self.app_name,
            session_id=self.session_id,
            run_id=run_id,
            human_baseline_time=self.human_baseline_time,
            ai_augmented_time=duration_min,
            guardrail_latency_tax=self.guardrail_latency_tax,
            session_iterations=max(1, tasks_count),
            hourly_rate_usd=self.hourly_rate_usd,
            is_shadow=self.is_shadow,
            metadata=metadata,
        )
        self._client.ingest_async(payload)


__all__ = ["APVACrewAI"]
