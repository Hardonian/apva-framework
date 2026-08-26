"""Universal Local AI Workstation Proxy."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import httpx

from apva_sdk.client import TelemetryEventPayload, get_default_client

logger = logging.getLogger(__name__)

app = FastAPI(title="APVA Local Proxy", version="2.0.0")
TARGET_URL = "http://localhost:11434/v1"


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check for local proxy."""
    return {"status": "ok", "target": TARGET_URL}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_request(request: Request, path: str) -> Any:
    """Transparently proxy the request and capture telemetry."""
    if path == "health" and request.method == "GET":
        return await health()

    start_time = time.perf_counter()
    url = f"{TARGET_URL.rstrip('/')}/{path}"
    body = await request.body()

    # Extract model name if JSON body
    model_name = "unknown"
    try:
        if body:
            parsed = json.loads(body.decode("utf-8"))
            if isinstance(parsed, dict) and "model" in parsed:
                model_name = str(parsed["model"])
    except Exception:
        pass

    # Filter headers (e.g. host) that could break the target server
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            req = client.build_request(
                request.method, url, content=body, headers=headers
            )
            response = await client.send(req, stream=True)

            async def streaming_generator():
                try:
                    async for chunk in response.aiter_raw():
                        yield chunk
                finally:
                    duration_min = (time.perf_counter() - start_time) / 60.0
                    payload = TelemetryEventPayload(
                        app_name="local-proxy",
                        session_id="local-dev-session",
                        run_id=f"proxy-{uuid.uuid4().hex[:12]}",
                        human_baseline_time=5.0,
                        ai_augmented_time=duration_min,
                        guardrail_latency_tax=0.0,
                        metadata={"path": path, "model": model_name},
                    )
                    apva_client = get_default_client()
                    apva_client.ingest_async(payload)
                    logger.debug("Proxied %s and captured %.4fm telemetry.", path, duration_min)

            return StreamingResponse(
                streaming_generator(),
                status_code=response.status_code,
                headers={k: v for k, v in response.headers.items() if k.lower() not in ("content-encoding", "content-length")},
            )
    except httpx.HTTPError as exc:
        duration_min = (time.perf_counter() - start_time) / 60.0
        return JSONResponse(
            status_code=502,
            content={"detail": f"Target proxy connection error: {str(exc)}", "target_url": url},
        )


def run_proxy(port: int, target: str) -> None:
    """Run the proxy server."""
    import uvicorn
    global TARGET_URL
    TARGET_URL = target
    logger.info("Starting APVA proxy on port %d targeting %s", port, target)
    uvicorn.run(app, host="127.0.0.1", port=port)
