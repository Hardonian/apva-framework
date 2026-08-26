"""Example AIAS LlamaIndex RAG query engine instrumented with APVA telemetry."""

from __future__ import annotations

import os
from apva_llamaindex import APVACallbackHandler


def run_instrumented_llamaindex_rag() -> None:
    # 1. Initialize APVA non-blocking LlamaIndex callback handler
    apva_handler = APVACallbackHandler(
        api_key=os.getenv("AIAS_APVA_KEY", "apva_dev_key"),
        endpoint=os.getenv("APVA_ENDPOINT", "http://localhost:8000/api/v1/telemetry/ingest"),
        app_name="aias-doc-retriever",
        session_id="session-rag-202",
        human_baseline_time=45.0,  # Human takes ~45 mins to research documentation
        hourly_rate_usd=95.00,     # Senior analyst wage
    )

    print(f"[AIAS] APVA LlamaIndex Handler initialized for '{apva_handler.app_name}'")
    print(f"[AIAS] Context chunk capturing and TVY discount enabled.")

    # 2. In production with llama-index:
    # callback_manager = CallbackManager([apva_handler])
    # service_context = ServiceContext.from_defaults(callback_manager=callback_manager)
    # query_engine.query("What are our SLA uptime commitments?")
    print("[AIAS] Ready to capture retrieval faithfulness and time yield.")


if __name__ == "__main__":
    run_instrumented_llamaindex_rag()
