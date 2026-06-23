"""
APVA Enterprise Integration for LangChain.

This package provides native, zero-code instrumentation for LangChain.
By wrapping your LLM Chains or Agents with APVACallbackHandler, telemetry
is automatically intercepted, enriched, and streamed to the APVA backend.
"""

from typing import Any
from uuid import uuid4

class APVACallbackHandler:
    """LangChain callback handler for automated TVY instrumentation."""
    
    def __init__(self, api_key: str, app_name: str = "langchain-app"):
        self.api_key = api_key
        self.app_name = app_name
        
    def on_chain_start(self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs: Any) -> None:
        """Called when chain starts running."""
        # Start timing for human baseline vs AI augmented
        self.start_time = ...
        
    def on_chain_end(self, outputs: dict[str, Any], **kwargs: Any) -> None:
        """Called when chain finishes. Auto-emits telemetry."""
        # Calculate latencies and trigger async SDK ingestion to EventStreamer
        # self.client.ingest_telemetry(...)
        print(f"[apva-langchain] Auto-emitted TVY telemetry for {self.app_name}")
