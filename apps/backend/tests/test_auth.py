"""Test suite for Enterprise Security and Authentication logic."""

import pytest
from httpx import ASGITransport, AsyncClient

from apps.backend.apps.backend.main import app


@pytest.mark.asyncio
async def test_sso_login_success():
    """Verify that a valid enterprise domain can successfully authenticate via SSO."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/auth/sso/login", json={"email": "ceo@acmecorp.com", "connection": "saml-okta"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_sso_login_rejects_invalid_domain():
    """Verify that consumer emails are rejected from the Enterprise SSO portal."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/auth/sso/login", json={"email": "hacker@gmail.com", "connection": "saml-okta"}
        )
        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Domain not authorized for Enterprise SSO."


@pytest.mark.asyncio
async def test_rate_limiter_active():
    """Verify the global rate limiter enforces the limit and returns 429.

    Regression test for the previously-silent gap: SlowAPI's middleware did
    not limit routes mounted via ``include_router`` and ``get_remote_address``
    returned an empty key behind some proxies, so 0/105 requests were ever
    throttled. Enforcement is now performed by the ``rate_limit`` dependency.
    """
    import apps.backend.apps.backend.limiter as limiter_mod

    limiter_mod.reset_limits()
    original = limiter_mod.LIMIT
    limiter_mod.LIMIT = 3  # tighten so the test is fast and deterministic
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            codes = []
            for _ in range(8):
                resp = await client.get("/api/v1/auth/sso/callback?code=c&state=s")
                codes.append(resp.status_code)
        assert codes[:3] == [200, 200, 200], f"first 3 should pass: {codes}"
        assert all(c == 429 for c in codes[3:]), f"remaining should be 429: {codes}"
    finally:
        limiter_mod.LIMIT = original
        limiter_mod.reset_limits()
