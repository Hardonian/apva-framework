"""Tests for APVA SDK Integrations: LangChain, LlamaIndex, and OpenAI native wrappers."""

from __future__ import annotations

import time
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

from apva_langchain import APVACallbackHandler as LangChainCallbackHandler
from apva_llamaindex import APVACallbackHandler as LlamaIndexCallbackHandler
from apva_sdk.integrations.openai_wrapper import APVAOpenAI


class MockTelemetryClient:
    """Mock telemetry client capturing ingested payloads in-memory."""

    def __init__(self) -> None:
        self.payloads: list[Any] = []
        self.app_name = "mock-app"
        self.session_id = "mock-session"

    def ingest_async(self, payload: Any) -> bool:
        self.payloads.append(payload)
        return True

    def ingest_batch(self, payloads: list[Any]) -> int:
        self.payloads.extend(payloads)
        return len(payloads)

    def close(self, timeout: float = 2.0) -> None:
        pass


def test_langchain_callback_handler():
    mock_client = MockTelemetryClient()
    handler = LangChainCallbackHandler(
        app_name="langchain-test",
        human_baseline_time=10.0,
        guardrail_latency_tax=0.5,
        client=mock_client,
    )

    run_id = uuid.uuid4()
    handler.on_chain_start(
        serialized={},
        inputs={"input": "hello world"},
        run_id=run_id,
        tags=["production"],
        metadata={"user_id": 42},
    )

    time.sleep(0.01)

    handler.on_chain_end(
        outputs={"output": "hello back"},
        run_id=run_id,
    )

    assert len(mock_client.payloads) == 1
    p = mock_client.payloads[0]
    assert p.app_name == "langchain-test"
    assert p.human_baseline_time == 10.0
    assert p.guardrail_latency_tax == 0.5
    assert p.ai_augmented_time > 0.0
    assert p.metadata.get("tags") == ["production"]


def test_llamaindex_callback_handler():
    mock_client = MockTelemetryClient()
    handler = LlamaIndexCallbackHandler(
        app_name="llamaindex-test",
        human_baseline_time=8.0,
        client=mock_client,
    )

    query_id = "query-1"
    handler.on_event_start(
        event_type="query",
        payload={"query_str": "What is TVY?"},
        event_id=query_id,
    )

    # Simulate retrieval event nested inside query
    retrieve_id = "retrieve-1"
    handler.on_event_start(event_type="retrieve", event_id=retrieve_id, parent_id=query_id)
    node_mock = MagicMock()
    node_mock.text = "TVY stands for True Value Yield."
    handler.on_event_end(
        event_type="retrieve",
        payload={"nodes": [node_mock]},
        event_id=retrieve_id,
        parent_id=query_id,
    )

    time.sleep(0.01)

    handler.on_event_end(
        event_type="query",
        payload={"response": "TVY stands for True Value Yield."},
        event_id=query_id,
    )

    assert len(mock_client.payloads) == 1
    p = mock_client.payloads[0]
    assert p.app_name == "llamaindex-test"
    assert p.human_baseline_time == 8.0
    assert p.metadata.get("has_retrieved_context") is True
    assert p.metadata.get("context_chunks_count") == 1


def test_openai_wrapper_sync():
    mock_client = MockTelemetryClient()

    class MockRawResponse:
        id = "chatcmpl-test-123"
        class usage:
            prompt_tokens = 15
            completion_tokens = 25
            total_tokens = 40

    class MockOpenAIClient:
        class chat:
            class completions:
                @staticmethod
                def create(*args, **kwargs):
                    return MockRawResponse()

    wrapped = APVAOpenAI(
        client=MockOpenAIClient(),
        app_name="openai-test",
        human_baseline_time=12.0,
        apva_client=mock_client,
    )

    res = wrapped.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Explain APVA"}],
    )
    assert res.id == "chatcmpl-test-123"
    assert len(mock_client.payloads) == 1
    p = mock_client.payloads[0]
    assert p.app_name == "openai-test"
    assert p.human_baseline_time == 12.0
    assert p.metadata.get("model") == "gpt-4o"
    assert p.metadata.get("total_tokens") == 40


@pytest.mark.anyio
async def test_openai_wrapper_async():
    mock_client = MockTelemetryClient()

    class MockRawResponse:
        id = "chatcmpl-async-456"
        class usage:
            prompt_tokens = 10
            completion_tokens = 20
            total_tokens = 30

    class MockAsyncOpenAIClient:
        class chat:
            class completions:
                @staticmethod
                async def create(*args, **kwargs):
                    return MockRawResponse()

    wrapped = APVAOpenAI(
        client=MockAsyncOpenAIClient(),
        app_name="openai-async-test",
        human_baseline_time=15.0,
        apva_client=mock_client,
    )

    res = await wrapped.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Async APVA"}],
    )
    assert res.id == "chatcmpl-async-456"
    assert len(mock_client.payloads) == 1
    p = mock_client.payloads[0]
    assert p.app_name == "openai-async-test"
    assert p.human_baseline_time == 15.0
    assert p.metadata.get("total_tokens") == 30
