"""
Unit and integration tests for SlowAPI rate limiting (unauthenticated IP-based).
Verifies rate limit enforcement, 429 responses, and standard error payload formatting.
"""
from unittest.mock import AsyncMock, MagicMock
from fastapi import Request
from fastapi.testclient import TestClient
import pytest

from backend.main import app
from backend.limiter import get_rate_limit_key, limiter
import backend.api.analysis as analysis_api

client = TestClient(app)


def test_rate_limit_key_uses_client_ip():
    """All requests use client IP address directly."""
    scope = {
        "type": "http",
        "client": ("192.168.1.100", 12345),
        "headers": [],
    }
    request = Request(scope)
    key = get_rate_limit_key(request)
    assert key == "192.168.1.100"

    # Even with an arbitrary authorization header, it uses client IP
    scope_with_header = {
        "type": "http",
        "client": ("10.0.0.1", 54321),
        "headers": [(b"authorization", b"Bearer sample")],
    }
    req_header = Request(scope_with_header)
    assert get_rate_limit_key(req_header) == "10.0.0.1"


def test_career_analysis_rate_limiting_triggers_429():
    """Rapid repeated requests exceed limit and return clean 429 JSON."""
    limiter.reset()
    mock_service = MagicMock()
    mock_service.get_or_create_analysis = AsyncMock(return_value={"is_cached": True})

    from backend.deps import AuthenticatedUser, get_current_user
    app.dependency_overrides[analysis_api._get_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id="00000000-0000-0000-0000-000000000001",
        email="student@example.com"
    )

    responses = []
    try:
        # Default limit is 3/hour. 5 requests will trigger 429
        for _ in range(5):
            res = client.post("/api/analysis/career", json={})
            responses.append(res)

        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes

        # Verify standard APIResponse JSON format on 429
        r_429 = next(r for r in responses if r.status_code == 429)
        data = r_429.json()
        assert data["success"] is False
        assert "Rate limit exceeded" in data["message"]
    finally:
        app.dependency_overrides.clear()
        limiter.reset()