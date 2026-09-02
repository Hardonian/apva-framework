"""Tests for APVA SDK Integrations: LangChain, LlamaIndex, OpenAI, Anthropic, CrewAI, and OpenTelemetry."""

from __future__ import annotations

import time
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

from apva_langchain import APVACallbackHandler as LangChainCallbackHandler
from apva_llamaindex import APVACallbackHandler as LlamaIndexCallbackHandler
from apva_sdk.integrations import APVAAnthropic, APVAOpenAI
from apva_sdk.integrations.crewai_handler import APVACrewAI
from apva_sdk.opentelemetry import APVASpanExporter, convert_span_to_apva_payload


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

    def flush(self) -> None:
        pass

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


def test_anthropic_wrapper_sync():
    mock_client = MockTelemetryClient()

    class MockAnthropicResponse:
        id = "msg-anthropic-789"
        class usage:
            input_tokens = 45
            output_tokens = 60

    class MockAnthropicClient:
        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return MockAnthropicResponse()

    wrapped = APVAAnthropic(
        client=MockAnthropicClient(),
        app_name="claude-test",
        human_baseline_time=20.0,
        guardrail_latency_tax=0.2,
        apva_client=mock_client,
    )

    res = wrapped.messages.create(
        model="claude-3-5-sonnet",
        messages=[{"role": "user", "content": "Benchmark APVA"}],
    )
    assert res.id == "msg-anthropic-789"
    assert len(mock_client.payloads) == 1
    p = mock_client.payloads[0]
    assert p.app_name == "claude-test"
    assert p.human_baseline_time == 20.0
    assert p.guardrail_latency_tax == 0.2
    assert p.metadata.get("provider") == "anthropic"
    assert p.metadata.get("total_tokens") == 105


@pytest.mark.anyio
async def test_anthropic_wrapper_async():
    mock_client = MockTelemetryClient()

    class MockAnthropicResponse:
        id = "msg-async-999"
        class usage:
            input_tokens = 25
            output_tokens = 35

    class MockAsyncAnthropicClient:
        class messages:
            @staticmethod
            async def create(*args, **kwargs):
                return MockAnthropicResponse()

    wrapped = APVAAnthropic(
        client=MockAsyncAnthropicClient(),
        app_name="claude-async",
        human_baseline_time=18.0,
        apva_client=mock_client,
    )

    res = await wrapped.messages.create(
        model="claude-3-5-haiku",
        messages=[{"role": "user", "content": "Async Claude"}],
    )
    assert res.id == "msg-async-999"
    assert len(mock_client.payloads) == 1
    p = mock_client.payloads[0]
    assert p.app_name == "claude-async"
    assert p.metadata.get("total_tokens") == 60


def test_crewai_wrapper():
    mock_client = MockTelemetryClient()

    class MockCrew:
        agents = ["researcher", "writer"]
        tasks = ["gather", "summarize"]

        def kickoff(self):
            class Result:
                class token_usage:
                    total_tokens = 350
            return Result()

    crew_wrapper = APVACrewAI(
        crew=MockCrew(),
        app_name="market-research-crew",
        human_baseline_time=90.0,
        guardrail_latency_tax=1.5,
        hourly_rate_usd=110.0,
        client=mock_client,
    )

    crew_wrapper.kickoff()
    assert len(mock_client.payloads) == 1
    p = mock_client.payloads[0]
    assert p.app_name == "market-research-crew"
    assert p.human_baseline_time == 90.0
    assert p.guardrail_latency_tax == 1.5
    assert p.hourly_rate_usd == 110.0
    assert p.metadata.get("agents_count") == 2
    assert p.metadata.get("tasks_count") == 2
    assert p.metadata.get("total_tokens") == 350


def test_opentelemetry_bridge():
    mock_client = MockTelemetryClient()
    exporter = APVASpanExporter(
        client=mock_client,
        default_app_name="otel-rag-service",
        default_human_baseline_min=25.0,
    )

    class MockContext:
        trace_id = 0x1234567890abcdef1234567890abcdef
        span_id = 0xabcdef1234567890

    class MockSpan:
        context = MockContext()
        name = "chat_generation"
        start_time = 1_000_000_000
        end_time = 1_600_000_000  # 0.6 seconds -> 0.01 min
        attributes = {
            "gen_ai.system": "openai",
            "gen_ai.request.model": "gpt-4o",
            "gen_ai.usage.prompt_tokens": 40,
            "gen_ai.usage.completion_tokens": 80,
            "apva.human_baseline_time": 30.0,
            "apva.hourly_rate_usd": 95.0,
        }

    status = exporter.export([MockSpan()])
    assert status == 0
    assert len(mock_client.payloads) == 1
    p = mock_client.payloads[0]
    assert p.app_name == "otel-rag-service"
    assert p.human_baseline_time == 30.0
    assert p.hourly_rate_usd == 95.0
    assert p.metadata.get("model") == "gpt-4o"
    assert p.metadata.get("total_tokens") == 120
