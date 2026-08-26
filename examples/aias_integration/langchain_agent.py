"""Example AIAS LangChain agent instrumented with APVA non-blocking telemetry."""

from __future__ import annotations

import os
from apva_langchain import APVACallbackHandler


def run_instrumented_langchain_agent() -> None:
    # 1. Initialize APVA non-blocking telemetry handler
    apva_handler = APVACallbackHandler(
        api_key=os.getenv("AIAS_APVA_KEY", "apva_dev_key"),
        endpoint=os.getenv("APVA_ENDPOINT", "http://localhost:8000/api/v1/telemetry/ingest"),
        app_name="aias-support-agent",
        session_id="session-user-101",
        human_baseline_time=25.0,  # Human takes ~25 mins to resolve support ticket
        hourly_rate_usd=85.00,     # Standard developer / engineer wage
    )

    print(f"[AIAS] APVA Callback Handler initialized for app '{apva_handler.app_name}'")
    print(f"[AIAS] Baseline: {apva_handler.human_baseline_time}m | Rate: ${apva_handler.hourly_rate_usd}/hr")

    # 2. In production with langchain:
    # chain.invoke({"input": "How do I setup billing?"}, config={"callbacks": [apva_handler]})
    print("[AIAS] Ready to stream live True Value Yield (TVY) to APVA engine.")


if __name__ == "__main__":
    run_instrumented_langchain_agent()
