"""
API endpoint integration tests using FastAPI TestClient.
Verifies health check, error handling, unauthenticated direct access, and response structures.
"""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
import pytest

from backend.main import app
from backend.deps import get_service_supabase

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"


from backend.deps import AuthenticatedUser, get_current_user, get_service_supabase


def test_profile_requires_auth():
    # Calling GET /api/profile without token MUST return 401
    response = client.get("/api/profile")
    assert response.status_code == 401


def test_profile_retrieval_with_mock():
    mock_db = MagicMock()
    # Mock get_by_id returning profile
    mock_db.table().select().eq().single().execute.return_value.data = {
        "id": "00000000-0000-0000-0000-000000000001",
        "full_name": "Test Student",
        "branch": "CSE",
        "semester": 4,
        "cgpa": 8.5,
    }
    # Mock skills and interests queries
    mock_db.table().select().eq().execute.return_value.data = []

    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id="00000000-0000-0000-0000-000000000001",
        email="student@example.com"
    )

    try:
        response = client.get("/api/profile")
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True
        assert json_data["data"]["branch"] == "CSE"
    finally:
        app.dependency_overrides.clear()


def test_careers_endpoint():
    mock_db = MagicMock()
    mock_db.table().select().limit().execute.return_value.data = [
        {"id": "c1", "title": "Software Developer", "branches": ["CSE"], "industry": "IT"}
    ]
    app.dependency_overrides[get_service_supabase] = lambda: mock_db

    try:
        response = client.get("/api/careers")
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True
        assert len(json_data["data"]) == 1
        assert json_data["data"][0]["title"] == "Software Developer"
    finally:
        app.dependency_overrides.clear()


def test_auth_endpoints_removed_404():
    """Confirms removed auth endpoints return 404."""
    res_login = client.post("/api/auth/login", json={"email": "a@b.com", "password": "password"})
    assert res_login.status_code == 404

    res_reg = client.post("/api/auth/register", json={"email": "a@b.com", "password": "password", "full_name": "Name"})
    assert res_reg.status_code == 404
