"""
Comprehensive Unit Tests for Supabase Authentication, RLS Boundaries,
User Isolation, Role-Based Access Control (Admin), Resume Deletion,
Cross-App Builder Resume Fetch, Multilingual Assessment, and AI Counselor Intent Routing.
"""
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
import pytest

from backend.config import Settings
from backend.deps import (
    AuthenticatedUser,
    get_current_user,
    require_admin,
    get_service_supabase,
)
from backend.main import app
from backend.services.chat_service import classify_intent

client = TestClient(app)

USER_A_ID = "11111111-1111-1111-1111-111111111111"
USER_B_ID = "22222222-2222-2222-2222-222222222222"
ADMIN_USER_ID = "99999999-9999-9999-9999-999999999999"


# ===========================================================================
# 1. CORS Configuration Tests
# ===========================================================================

def test_cors_origins_property():
    settings = Settings(cors_origins="http://localhost:3000, http://127.0.0.1:5500 , https://app.example.com")
    origins = settings.cors_origins_list
    assert origins == ["http://localhost:3000", "http://127.0.0.1:5500", "https://app.example.com"]


def test_default_cors_origins_includes_production_frontend():
    settings = Settings()
    assert "https://gpt-career.netlify.app" in settings.cors_origins_list
    assert "http://127.0.0.1:8001" in settings.cors_origins_list


def test_cors_options_preflight_for_production_frontend():
    res = client.options(
        "/api/health",
        headers={
            "Origin": "https://gpt-career.netlify.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "https://gpt-career.netlify.app"
    assert res.headers.get("access-control-allow-credentials") == "true"


# ===========================================================================
# 2. Strict 401 Unauthorized for Unauthenticated Protected Routes
# ===========================================================================

@pytest.mark.parametrize("method,endpoint", [
    ("get", "/api/profile"),
    ("post", "/api/profile"),
    ("put", "/api/profile"),
    ("get", "/api/analysis/career"),
    ("post", "/api/analysis/career"),
    ("get", "/api/analysis/roadmap"),
    ("get", "/api/chat/sessions"),
    ("post", "/api/chat/send"),
    ("get", "/api/resume/latest"),
    ("delete", "/api/resume"),
    ("get", "/api/resume/builder-resume"),
    ("post", "/api/admin/careers"),
])
def test_protected_routes_return_401_without_token(method, endpoint):
    """Verify that every protected endpoint rejects requests without an Authorization Bearer token."""
    func = getattr(client, method)
    res = func(endpoint)
    assert res.status_code == 401, f"{endpoint} should return 401 without token, got {res.status_code}"
    data = res.json()
    assert "Authentication token required" in data["detail"] or "Bearer" in data["detail"]


# ===========================================================================
# 3. Role-Based Access Control for Admin Endpoints (401 -> 403 -> 201)
# ===========================================================================

def test_admin_careers_returns_403_for_non_admin():
    """Verify that a standard authenticated user receives 403 Forbidden on admin endpoints."""
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=USER_A_ID, email="student@example.com", is_admin=False
    )
    try:
        res = client.post(
            "/api/admin/careers",
            json={
                "title": "Cloud Engineer",
                "description": "Deploy cloud infrastructure",
                "branches": ["CSE"],
                "min_cgpa": 7.0,
                "avg_salary_lpa": 8.0,
                "job_growth": "High",
                "industry": "IT",
            }
        )
        assert res.status_code == 403
        assert "Admin authorization required" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_admin_careers_succeeds_for_admin_user():
    """Verify that an admin user can successfully create career records."""
    mock_db = MagicMock()
    mock_db.table().insert().execute.return_value.data = [
        {"id": "new-career-id", "title": "Cloud Engineer", "branches": ["CSE"]}
    ]
    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=ADMIN_USER_ID, email="admin@example.com", is_admin=True
    )
    try:
        res = client.post(
            "/api/admin/careers",
            json={
                "title": "Cloud Engineer",
                "description": "Deploy cloud infrastructure",
                "branches": ["CSE"],
                "min_cgpa": 7.0,
                "avg_salary_lpa": 8.0,
                "job_growth": "High",
                "industry": "IT",
            }
        )
        assert res.status_code == 201
        assert res.json()["success"] is True
    finally:
        app.dependency_overrides.clear()


# ===========================================================================
# 4. User Data Isolation (User A vs User B)
# ===========================================================================

def test_user_a_cannot_access_user_b_profile():
    """Verify that profile queries are strictly bound to the authenticated user's ID."""
    mock_db = MagicMock()

    # User A profile
    user_a_profile = {
        "id": USER_A_ID,
        "email": "user_a@example.com",
        "full_name": "Student A",
        "branch": "CSE",
    }

    # Simulate database returning profile matching queried id
    def mock_select(*args, **kwargs):
        sel = MagicMock()
        def mock_eq(field, val):
            eq_mock = MagicMock()
            if val == USER_A_ID:
                eq_mock.single().execute.return_value.data = user_a_profile
            else:
                eq_mock.single().execute.return_value.data = None
            return eq_mock
        sel.eq = mock_eq
        return sel

    mock_db.table().select = mock_select
    mock_db.table().delete().eq().execute.return_value.data = []

    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=USER_A_ID, email="user_a@example.com"
    )

    try:
        res = client.get("/api/profile")
        assert res.status_code == 200
        assert res.json()["data"]["id"] == USER_A_ID
        assert res.json()["data"]["full_name"] == "Student A"
    finally:
        app.dependency_overrides.clear()


# ===========================================================================
# 5. Secure Resume Deletion (Deletes only resume analysis)
# ===========================================================================

def test_secure_resume_deletion():
    """Verify DELETE /api/resume deletes resume analysis without touching profiles or chats."""
    mock_db = MagicMock()
    delete_called_for_table = []

    def mock_table(name):
        tbl = MagicMock()
        def mock_delete():
            del_mock = MagicMock()
            def mock_eq(col, val):
                delete_called_for_table.append((name, col, val))
                ret = MagicMock()
                ret.execute.return_value.data = [{"id": "deleted-res-1"}]
                return ret
            del_mock.eq = mock_eq
            return del_mock
        tbl.delete = mock_delete
        return tbl

    mock_db.table = mock_table
    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=USER_A_ID, email="user_a@example.com"
    )

    try:
        res = client.delete("/api/resume")
        assert res.status_code == 200
        assert res.json()["success"] is True
        # Verify resume_analyses was deleted for USER_A_ID
        assert ("resume_analyses", "profile_id", USER_A_ID) in delete_called_for_table
        # Verify profiles and chat_sessions were NOT deleted
        for table, _, _ in delete_called_for_table:
            assert table not in ("profiles", "chat_sessions", "roadmaps")
    finally:
        app.dependency_overrides.clear()


# ===========================================================================
# 6. Cross-App Builder Resume Retrieval
# ===========================================================================

def test_get_builder_resume_authenticated():
    """Verify GET /api/resume/builder-resume returns user's resume from GPT-Resume builder."""
    mock_db = MagicMock()
    mock_resume = {
        "id": "builder-res-1",
        "user_id": USER_A_ID,
        "title": "Diploma Cloud Resume",
        "template_id": "fresher",
        "content": {"name": "Student A", "skills": ["Linux", "AWS"]},
        "updated_at": "2026-09-17T12:00:00Z"
    }

    mock_db.table().select().eq().order().execute.return_value.data = [mock_resume]

    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=USER_A_ID, email="user_a@example.com"
    )

    try:
        res = client.get("/api/resume/builder-resume")
        assert res.status_code == 200
        assert res.json()["success"] is True
        data = res.json()["data"]
        resume_item = data[0] if isinstance(data, list) else data
        assert resume_item["user_id"] == USER_A_ID
        assert resume_item["title"] == "Diploma Cloud Resume"
    finally:
        app.dependency_overrides.clear()


# ===========================================================================
# 7. Multilingual Assessment Questions (Telugu vs English)
# ===========================================================================

def test_assessment_questions_multilingual():
    """Verify assessment questions endpoint respects lang=te and lang=en."""
    mock_db = MagicMock()
    sample_questions = [
        {
            "id": "q1",
            "question_text": "What type of technical tasks do you enjoy most?",
            "question_text_te": "మీరు ఏ రకమైన సాంకేతిక పనులను ఎక్కువగా ఆస్వాదిస్తారు?",
            "domain": "software",
            "phase": "broad",
            "order_num": 1,
            "assessment_options": [
                {
                    "id": "opt1",
                    "question_id": "q1",
                    "option_text": "Writing code and software scripts",
                    "option_text_te": "కోడింగ్ మరియు సాఫ్ట్‌వేర్ స్క్రిప్ట్‌లు రాయడం",
                    "domain_weights": {"software": 5}
                }
            ]
        }
    ]

    mock_db.table().select().order().execute.return_value.data = sample_questions
    app.dependency_overrides[get_service_supabase] = lambda: mock_db

    try:
        # 1. English
        res_en = client.get("/api/profile/assessment/questions?lang=en")
        assert res_en.status_code == 200
        q_en = res_en.json()["data"][0]
        assert q_en["question_text"] == "What type of technical tasks do you enjoy most?"
        assert q_en["assessment_options"][0]["option_text"] == "Writing code and software scripts"

        # 2. Telugu
        res_te = client.get("/api/profile/assessment/questions?lang=te")
        assert res_te.status_code == 200
        q_te = res_te.json()["data"][0]
        assert "సాంకేతిక పనులను" in q_te["question_text"]
        assert "కోడింగ్ మరియు" in q_te["assessment_options"][0]["option_text"]
        # Question and Option IDs remain identical
        assert q_te["id"] == q_en["id"]
        assert q_te["assessment_options"][0]["id"] == q_en["assessment_options"][0]["id"]
    finally:
        app.dependency_overrides.clear()


# ===========================================================================
# 8. AI Counselor Intent Classification (10 Categories)
# ===========================================================================

@pytest.mark.parametrize("query,expected_intent", [
    ("What is my CGPA?", "personal_profile"),
    ("Tell me about my profile and branch", "personal_profile"),
    ("Who is the prime minister of India?", "general_knowledge"),
    ("What is the capital of France?", "general_knowledge"),
    ("Latest news about technological developments", "current_affairs"),
    ("How can I improve my resume for diploma jobs?", "resume"),
    ("How do I interpret my assessment score?", "assessment"),
    ("Show me step 2 of my roadmap", "roadmap"),
    ("What are my top recommended career matches?", "analysis"),
    ("What are the best polytechnic colleges for lateral entry?", "education"),
    ("What is the average salary of a CNC programmer?", "career"),
    ("Can you tell me a funny joke?", "other"),
])
def test_ai_counselor_intent_classification(query, expected_intent):
    """Verify that classify_intent accurately routes student queries to the proper category."""
    classified = classify_intent(query)
    assert classified == expected_intent, f"Query '{query}' classified as '{classified}', expected '{expected_intent}'"
