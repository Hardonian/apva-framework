# APVA LangChain Integration

Zero-code LangChain callback handler for automated True Value Yield (TVY) telemetry tracking in the APVA ecosystem.

## Installation

```bash
pip install apva-langchain
```

## Usage

```python
from apva_langchain import APVACallbackHandler

handler = APVACallbackHandler(
    app_name="customer-support-agent",
    session_id="session-123",
    human_baseline_time=45.0,
)
```
