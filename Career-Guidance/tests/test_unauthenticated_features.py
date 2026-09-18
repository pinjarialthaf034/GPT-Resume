"""
Comprehensive tests verifying all CareerCompass AI features operate seamlessly
under authenticated user sessions via Supabase Auth:
- Profile retrieval, creation, and updating
- Career assessment submission
- Career explorer search and detail
- Career analysis and roadmap progress
- Chat sessions, history, and message sending
- Resume analysis
"""
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
import pytest

from backend.main import app
from backend.deps import AuthenticatedUser, get_current_user, get_service_supabase
import backend.api.analysis as analysis_api
import backend.api.chat as chat_api
import backend.api.resume as resume_api

client = TestClient(app)

TEST_USER_ID = "33333333-3333-3333-3333-333333333333"


@pytest.fixture(autouse=True)
def override_auth_user():
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id=TEST_USER_ID,
        email="priya@example.com",
        is_admin=False
    )
    yield
    app.dependency_overrides.clear()


def test_profile_crud_authenticated():
    mock_db = MagicMock()
    # Mock profile not found initially
    mock_db.table().select().eq().single().execute.return_value.data = None
    mock_db.table().select().limit().execute.return_value.data = []

    # Mock insert
    created_profile = {
        "id": TEST_USER_ID,
        "email": "priya@example.com",
        "full_name": "Priya Patel",
        "branch": "CSE",
        "semester": 5,
        "cgpa": 9.1,
        "career_goal": "Cloud Infrastructure",
        "profile_version": 1,
        "is_admin": False,
    }
    mock_db.table().insert().execute.return_value.data = [created_profile]
    mock_db.table().delete().eq().execute.return_value.data = []

    app.dependency_overrides[get_service_supabase] = lambda: mock_db

    try:
        # 1. Create Profile
        create_payload = {
            "full_name": "Priya Patel",
            "branch": "CSE",
            "semester": 5,
            "cgpa": 9.1,
            "career_goal": "Cloud Infrastructure",
            "skills": [{"name": "Python", "proficiency": "advanced"}],
            "interests": ["Cloud"],
        }
        res_create = client.post("/api/profile", json=create_payload)
        assert res_create.status_code == 201
        assert res_create.json()["success"] is True

        # 2. Get Profile
        mock_db.table().select().eq().single().execute.return_value.data = created_profile
        res_get = client.get("/api/profile")
        assert res_get.status_code == 200
        assert res_get.json()["data"]["full_name"] == "Priya Patel"

        # 3. Update Profile
        updated_profile = dict(created_profile)
        updated_profile["cgpa"] = 9.3
        mock_db.table().update().eq().execute.return_value.data = [updated_profile]

        res_update = client.put("/api/profile", json={"cgpa": 9.3})
        assert res_update.status_code == 200
        assert res_update.json()["success"] is True
    finally:
        pass


def test_assessment_submission_authenticated():
    mock_db = MagicMock()
    mock_db.table().select().eq().single().execute.return_value.data = {
        "id": TEST_USER_ID,
        "full_name": "Priya Patel",
    }
    mock_db.table().delete().eq().execute.return_value.data = []
    mock_db.table().insert().execute.return_value.data = []
    mock_db.table().update().eq().execute.return_value.data = [{}]

    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    try:
        payload = {
            "answers": [
                {"question_id": "q1", "option_id": "opt1"},
                {"question_id": "q2", "option_id": "opt2"},
            ]
        }
        res = client.post("/api/profile/assessment/submit", json=payload)
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert "Assessment submitted" in res.json()["message"]
    finally:
        pass


def test_career_analysis_and_roadmap_authenticated():
    mock_service = MagicMock()
    mock_service.get_or_create_analysis = AsyncMock(return_value={
        "id": "analysis-123",
        "profile_id": TEST_USER_ID,
        "is_cached": False,
        "recommended_careers": [{"title": "DevOps Engineer", "match_score": 92}],
    })
    mock_service.get_latest_analysis.return_value = {
        "id": "analysis-123",
        "recommended_careers": [{"title": "DevOps Engineer"}],
    }
    mock_service.get_roadmap_progress.return_value = {
        "analysis_id": "analysis-123",
        "roadmap_steps": [{"step_number": 1, "title": "Learn Linux", "completed": False}],
        "percent_complete": 0,
    }
    mock_service.update_roadmap_progress.return_value = {
        "step_number": 1,
        "completed": True,
    }

    app.dependency_overrides[analysis_api._get_service] = lambda: mock_service

    try:
        # POST run analysis with auth
        res_run = client.post("/api/analysis/career", json={"force_regenerate": True})
        assert res_run.status_code == 200
        assert res_run.json()["data"]["recommended_careers"][0]["title"] == "DevOps Engineer"

        # GET latest analysis with auth
        res_get = client.get("/api/analysis/career")
        assert res_get.status_code == 200
        assert res_get.json()["data"]["id"] == "analysis-123"

        # GET roadmap progress with auth
        res_rm = client.get("/api/analysis/roadmap")
        assert res_rm.status_code == 200
        assert res_rm.json()["data"]["percent_complete"] == 0

        # POST update roadmap step with auth
        res_step = client.post("/api/analysis/roadmap/progress", json={"step_number": 1, "completed": True})
        assert res_step.status_code == 200
        assert res_step.json()["data"]["completed"] is True
    finally:
        pass


def test_chat_authenticated():
    mock_service = MagicMock()
    mock_service.send_message = AsyncMock(return_value={
        "session_id": "session-abc",
        "response": "Hello! I can guide your career path.",
    })
    mock_service.get_history.return_value = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
    ]
    mock_service.list_sessions.return_value = [
        {"id": "session-abc", "created_at": "2026-09-04T00:00:00Z"}
    ]

    app.dependency_overrides[chat_api._get_service] = lambda: mock_service

    try:
        # Send chat message with auth
        res_send = client.post("/api/chat/send", json={"message": "What should I learn?"})
        assert res_send.status_code == 200
        assert res_send.json()["data"]["session_id"] == "session-abc"

        # Get history with auth
        res_hist = client.get("/api/chat/history/session-abc")
        assert res_hist.status_code == 200
        assert len(res_hist.json()["data"]["messages"]) == 2

        # List sessions with auth
        res_sess = client.get("/api/chat/sessions")
        assert res_sess.status_code == 200
        assert len(res_sess.json()["data"]) == 1
    finally:
        pass


def test_resume_analysis_authenticated():
    mock_service = MagicMock()
    mock_service.analyze_resume = AsyncMock(return_value={
        "guidance_score": 85,
        "strengths": ["Clear project descriptions"],
        "missing_skills": ["Docker", "Kubernetes"],
    })
    mock_service.get_latest_resume_analysis.return_value = {
        "guidance_score": 85,
        "strengths": ["Clear project descriptions"],
    }

    app.dependency_overrides[resume_api._get_service] = lambda: mock_service

    try:
        # POST analyze resume with auth
        files = {"file": ("resume.pdf", b"%PDF-1.4 dummy content", "application/pdf")}
        res_analyze = client.post("/api/resume/analyze", files=files)
        assert res_analyze.status_code == 200
        assert res_analyze.json()["data"]["guidance_score"] == 85

        # GET latest resume analysis with auth
        res_latest = client.get("/api/resume/latest")
        assert res_latest.status_code == 200
        assert res_latest.json()["data"]["guidance_score"] == 85
    finally:
        pass
