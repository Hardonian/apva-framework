from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "sdk" / "src"))

from apva_sdk.integrations import APVAOpenAI


def main() -> None:
    # In production, pass your real openai.OpenAI() client
    # For demonstration, we use a mock client interface
    class MockCompletion:
        id = "chatcmpl-demo-123"
        class usage:
            prompt_tokens = 25
            completion_tokens = 50
            total_tokens = 75

    class MockOpenAI:
        class chat:
            class completions:
                @staticmethod
                def create(*args, **kwargs):
                    return MockCompletion()

    # Wrap the OpenAI client with zero code friction
    client = APVAOpenAI(
        client=MockOpenAI(),
        app_name="customer-support-copilot",
        human_baseline_time=25.0,  # Human takes 25 min unaided
        guardrail_latency_tax=0.4,  # Guardrail takes 0.4 min
        hourly_rate_usd=85.0,
    )

    print("[APVA Quickstart] Calling OpenAI chat completion...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "How do I configure APVA?"}],
    )

    print(f"Received completion ID: {response.id}")
    print("Telemetry event automatically captured and queued for ingestion!")


if __name__ == "__main__":
    main()
