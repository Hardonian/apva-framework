# APVA LlamaIndex Integration

Zero-code LlamaIndex callback handler for automated True Value Yield (TVY) telemetry tracking in the APVA ecosystem.

## Installation

```bash
pip install apva-llamaindex
```

## Usage

```python
from apva_llamaindex import APVALlamaIndexCallback

callback = APVALlamaIndexCallback(
    app_name="rag-search-agent",
    session_id="session-789",
    human_baseline_time=30.0,
)
```
