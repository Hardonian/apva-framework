"""Test suite for Enterprise Security and Authentication logic."""

import pytest
from httpx import AsyncClient
from apps.backend.main import app

@pytest.mark.asyncio
async def test_sso_login_success():
    """Verify that a valid enterprise domain can successfully authenticate via SSO."""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/auth/sso/login",
            json={"email": "ceo@acmecorp.com", "connection": "saml-okta"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
@pytest.mark.asyncio
async def test_sso_login_rejects_invalid_domain():
    """Verify that consumer emails are rejected from the Enterprise SSO portal."""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/auth/sso/login",
            json={"email": "hacker@gmail.com", "connection": "saml-okta"}
        )
        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Domain not authorized for Enterprise SSO."

@pytest.mark.asyncio
async def test_rate_limiter_active():
    """Verify that the SlowAPI rate limiter catches abuse."""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        # Send 101 requests to trigger the 100/minute limit
        for _ in range(101):
            response = await client.get("/api/v1/health")
            
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["error"]
