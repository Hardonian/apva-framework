"""OpenTelemetry span bridge for the APVA framework.

Translates standard OpenTelemetry GenAI Semantic Convention spans directly
into APVA True Value Yield telemetry events without changing application code.
"""

from __future__ import annotations

import logging
from typing import Any

from apva_sdk.client import APVATelemetryClient, TelemetryEventPayload, get_default_client

logger = logging.getLogger(__name__)


def convert_span_to_apva_payload(
    span: Any,
    default_app_name: str = "otel-genai-app",
    default_human_baseline_min: float = 15.0,
    default_guardrail_tax_min: float = 0.2,
) -> TelemetryEventPayload | None:
    """Extract APVA telemetry from an OpenTelemetry ReadableSpan.

    Args:
        span: OpenTelemetry ReadableSpan instance or duck-typed object.
        default_app_name: Fallback application name.
        default_human_baseline_min: Fallback human baseline time in minutes.
        default_guardrail_tax_min: Fallback guardrail tax in minutes.

    Returns:
        TelemetryEventPayload | None: Constructed payload, or None if invalid.
    """
    attributes = getattr(span, "attributes", {}) or {}

    # Calculate duration in minutes
    start_ns = getattr(span, "start_time", None)
    end_ns = getattr(span, "end_time", None)
    if start_ns is not None and end_ns is not None and end_ns >= start_ns:
        duration_min = (end_ns - start_ns) / (1e9 * 60.0)
    else:
        duration_min = 0.0

    # Extract OpenTelemetry GenAI Semantic Conventions
    model = attributes.get("gen_ai.request.model") or attributes.get("llm.model_name") or "unknown"
    system = attributes.get("gen_ai.system") or attributes.get("llm.system") or "llm"
    prompt_tokens = attributes.get("gen_ai.usage.prompt_tokens") or attributes.get("llm.prompt_tokens") or 0
    completion_tokens = (
        attributes.get("gen_ai.usage.completion_tokens") or attributes.get("llm.completion_tokens") or 0
    )

    # Extract APVA specific annotations if present
    app_name = attributes.get("apva.app_name", default_app_name)
    baseline = float(attributes.get("apva.human_baseline_time", default_human_baseline_min))
    guardrail_tax = float(attributes.get("apva.guardrail_latency_tax", default_guardrail_tax_min))
    hourly_rate = attributes.get("apva.hourly_rate_usd")
    if hourly_rate is not None:
        hourly_rate = float(hourly_rate)
    is_shadow = bool(attributes.get("apva.is_shadow", False))

    # Context & identifiers
    context = getattr(span, "context", None)
    trace_id = format(getattr(context, "trace_id", 0), "032x") if context else "unknown-trace"
    span_id = format(getattr(context, "span_id", 0), "016x") if context else getattr(span, "name", "span")

    metadata: dict[str, Any] = {
        "otel_trace_id": trace_id,
        "otel_span_id": span_id,
        "gen_ai_system": system,
        "model": model,
        "input_tokens": prompt_tokens,
        "output_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }

    return TelemetryEventPayload(
        app_name=str(app_name),
        session_id=str(trace_id),
        run_id=str(span_id),
        human_baseline_time=baseline,
        ai_augmented_time=duration_min,
        guardrail_latency_tax=guardrail_tax,
        session_iterations=1,
        hourly_rate_usd=hourly_rate,
        is_shadow=is_shadow,
        metadata=metadata,
    )


class APVASpanExporter:
    """Custom OpenTelemetry SpanExporter that exports to APVA.

    Can be registered with an OpenTelemetry `BatchSpanProcessor` or
    `SimpleSpanProcessor` to automatically convert GenAI spans to APVA events.
    """

    def __init__(
        self,
        client: APVATelemetryClient | None = None,
        default_app_name: str = "otel-genai-service",
        default_human_baseline_min: float = 20.0,
    ) -> None:
        self.client = client or get_default_client()
        self.default_app_name = default_app_name
        self.default_human_baseline_min = default_human_baseline_min

    def export(self, spans: Any) -> Any:
        """Process and ingest batch of OpenTelemetry spans."""
        for span in spans:
            try:
                # Only process spans tagged with gen_ai or llm
                attrs = getattr(span, "attributes", {}) or {}
                if any(k.startswith("gen_ai.") or k.startswith("llm.") or k.startswith("apva.") for k in attrs):
                    payload = convert_span_to_apva_payload(
                        span,
                        default_app_name=self.default_app_name,
                        default_human_baseline_min=self.default_human_baseline_min,
                    )
                    if payload:
                        self.client.ingest_async(payload)
            except Exception as exc:
                logger.debug("[APVASpanExporter] Error processing span: %s", exc)

        # Return success code matching OpenTelemetry SpanExportResult.SUCCESS (0)
        return 0

    def shutdown(self) -> None:
        """Flush the APVA client."""
        self.client.flush()


__all__ = ["APVASpanExporter", "convert_span_to_apva_payload"]
