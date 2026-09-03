"""Example AIAS direct OpenAI client wrapper instrumented with APVA telemetry."""

from __future__ import annotations

import os

from apva_sdk.integrations.openai_wrapper import APVAOpenAI


def run_instrumented_openai_client() -> None:
    # 1. Initialize APVAOpenAI wrapper
    client = APVAOpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "sk-mock-key"),
        apva_endpoint=os.getenv("APVA_ENDPOINT", "http://localhost:8000/api/v1/telemetry/ingest"),
        app_name="aias-openai-agent",
        human_baseline_time=15.0,  # 15 mins human baseline
        hourly_rate_usd=80.00,
    )

    print(f"[AIAS] APVA OpenAI proxy initialized for '{client.app_name}'")
    print("[AIAS] Sync & Async ChatCompletions, Embeddings, and token usage tracked automatically.")


if __name__ == "__main__":
    run_instrumented_openai_client()
