"""Tests for APVA local AI proxy."""

from __future__ import annotations

import pytest
from apva_cli.proxy import app as proxy_app
from httpx import ASGITransport, AsyncClient


@pytest.mark.anyio
async def test_proxy_health_endpoint():
    transport = ASGITransport(app=proxy_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert "target" in data
