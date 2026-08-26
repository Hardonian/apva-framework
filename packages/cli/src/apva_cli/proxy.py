"""Universal Local AI Workstation Proxy."""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import httpx

from apva_sdk.client import TelemetryEventPayload, get_default_client

logger = logging.getLogger(__name__)

app = FastAPI(title="APVA Local Proxy")
TARGET_URL = "http://localhost:11434/v1"

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_request(request: Request, path: str):
    """Transparently proxy the request and capture telemetry."""
    start_time = time.time()
    
    url = f"{TARGET_URL.rstrip('/')}/{path}"
    body = await request.body()
    
    # Filter headers (e.g. host) that could break the target server
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    
    async with httpx.AsyncClient() as client:
        req = client.build_request(
            request.method, url, content=body, headers=headers
        )
        response = await client.send(req, stream=True)
        
        async def streaming_generator():
            async for chunk in response.aiter_raw():
                yield chunk
            
            duration_min = (time.time() - start_time) / 60.0
            payload = TelemetryEventPayload(
                app_name="local-proxy",
                session_id="local-dev-session",
                run_id="local-" + str(int(start_time)),
                human_baseline_time=5.0,
                ai_augmented_time=duration_min,
                guardrail_latency_tax=0.0
            )
            apva_client = get_default_client()
            apva_client.ingest_async(payload)
            logger.info("Proxied %s and captured %.4fm telemetry.", path, duration_min)
            
        return StreamingResponse(
            streaming_generator(),
            status_code=response.status_code,
            headers={k: v for k, v in response.headers.items() if k.lower() not in ("content-encoding", "content-length")}
        )

def run_proxy(port: int, target: str) -> None:
    """Run the proxy server."""
    import uvicorn
    global TARGET_URL
    TARGET_URL = target
    logger.info("Starting APVA proxy on port %d targeting %s", port, target)
    uvicorn.run(app, host="127.0.0.1", port=port)
