from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "sdk" / "src"))

from apva_sdk.integrations import APVAAnthropic


def main() -> None:
    # In production, pass your real anthropic.Anthropic() client
    class MockMessage:
        id = "msg-anthropic-demo-456"
        class usage:
            input_tokens = 30
            output_tokens = 60

    class MockAnthropic:
        class messages:
            @staticmethod
            def create(*args, **kwargs):
                return MockMessage()

    # Wrap the Anthropic client seamlessly
    client = APVAAnthropic(
        client=MockAnthropic(),
        app_name="legal-document-analyzer",
        human_baseline_time=45.0,  # Legal review takes 45 min unaided
        guardrail_latency_tax=0.6,
        hourly_rate_usd=150.0,
    )

    print("[APVA Quickstart] Calling Anthropic Claude message creation...")
    response = client.messages.create(
        model="claude-3-5-sonnet",
        messages=[{"role": "user", "content": "Analyze clause 4.2 in the MSA."}],
    )

    print(f"Received message ID: {response.id}")
    print("Telemetry event automatically captured with token accounting!")


if __name__ == "__main__":
    main()
