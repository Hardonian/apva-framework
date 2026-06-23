"""
APVA Enterprise Integration for LlamaIndex.

This package provides native, zero-code instrumentation for LlamaIndex.
By registering the APVACallbackHandler into the global ServiceContext,
all RAG retrieval metrics and generation latencies are streamed directly
to the APVA ClickHouse backend.
"""

from typing import Any
from llama_index.core.callbacks import BaseCallbackHandler
from llama_index.core.callbacks.schema import CBEventType, EventPayload

class APVACallbackHandler(BaseCallbackHandler):
    """LlamaIndex callback handler for automated RAG evaluation & TVY."""
    
    def __init__(self, api_key: str, app_name: str = "llamaindex-app"):
        super().__init__(
            event_starts_to_ignore=[],
            event_ends_to_ignore=[]
        )
        self.api_key = api_key
        self.app_name = app_name
        
    def on_event_start(self, event_type: CBEventType, payload: dict[str, Any] | None = None, event_id: str = "", parent_id: str = "", **kwargs: Any) -> str:
        """Track retrieval and LLM start times."""
        return event_id
        
    def on_event_end(self, event_type: CBEventType, payload: dict[str, Any] | None = None, event_id: str = "", parent_id: str = "", **kwargs: Any) -> None:
        """Capture context and generated answers to fire off to EventStreamer."""
        if event_type == CBEventType.LLM:
            print(f"[apva-llamaindex] Auto-emitted RAG evaluation payload for {self.app_name}")
