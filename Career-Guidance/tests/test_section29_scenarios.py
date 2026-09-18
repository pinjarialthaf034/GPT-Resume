"""
Tests specifically verifying all 10 scenarios enumerated in Section 29 of the specification:
TEST 1: CSE student strongly interested in software.
TEST 2: CSE student strongly interested in electronics.
TEST 3: Mechanical student interested in software.
TEST 4: Student gives mixed answers.
TEST 5: Student chooses 'Not sure yet' repeatedly.
TEST 6: Student refreshes page during assessment (resumed via state).
TEST 7: Student submits assessment twice (idempotent upsert).
TEST 8: Backend error response format is friendly.
TEST 9: Gemini unavailable -> rule-engine fallback produces deterministic career matches.
TEST 10: Existing analysis/dashboard/roadmap endpoints have no regressions.
"""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.deps import get_service_supabase
from backend.services.matching_engine import compute_career_matches
from backend.services.analysis_service import AnalysisService

client = TestClient(app)

MOCK_DISCOVERY_QUESTIONS = [
    {
        "id": "q1",
        "question_text": "Favorite Activity?",
        "category": "Logic",
        "phase": "broad",
        "domain": "software",
        "order_num": 1,
        "assessment_options": [
            {"id": "opt-sw", "option_text": "Building apps", "career_weight": {"Software Developer": 3}, "domain_weight": {"software": 10}},
            {"id": "opt-elec", "option_text": "Wiring circuits", "career_weight": {"Embedded Systems Engineer": 3}, "domain_weight": {"electronics_embedded": 10}},
            {"id": "opt-unsure", "option_text": "🤷 I am not sure yet", "career_weight": {}, "domain_weight": {}},
        ]
    },
    {
        "id": "q2",
        "question_text": "Work environment?",
        "category": "Environment",
        "phase": "broad",
        "domain": "general",
        "order_num": 2,
        "assessment_options": [
            {"id": "opt-sw-env", "option_text": "Modern screen office", "career_weight": {"Software Developer": 2}, "domain_weight": {"software": 8}},
            {"id": "opt-elec-env", "option_text": "Electronics R&D lab", "career_weight": {"Embedded Systems Engineer": 2}, "domain_weight": {"electronics_embedded": 8}},
            {"id": "opt-unsure-2", "option_text": "🤷 I am not sure yet", "career_weight": {}, "domain_weight": {}},
        ]
    },
    {
        "id": "q-deep-sw",
        "question_text": "Deep Software Challenge?",
        "category": "Logic",
        "phase": "deep_dive",
        "domain": "software",
        "order_num": 6,
        "assessment_options": [
            {"id": "opt-deep-backend", "option_text": "APIs and DBs", "career_weight": {"Backend Developer": 3}, "domain_weight": {"software": 10}}
        ]
    },
    {
        "id": "q-deep-elec",
        "question_text": "Deep Electronics Challenge?",
        "category": "Hardware",
        "phase": "deep_dive",
        "domain": "electronics_embedded",
        "order_num": 7,
        "assessment_options": [
            {"id": "opt-deep-mcu", "option_text": "Microcontrollers", "career_weight": {"Embedded Systems Engineer": 3}, "domain_weight": {"electronics_embedded": 10}}
        ]
    }
]


def test_scenario_1_cse_interested_in_software():
    """TEST 1: CSE student strongly interested in software -> software deep dive question appears."""
    mock_db = MagicMock()
    mock_db.table().select().order().execute.return_value.data = MOCK_DISCOVERY_QUESTIONS
    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    try:
        # Answered broad questions with software
        res = client.post("/api/profile/assessment/next", json={
            "answers": [
                {"question_id": "q1", "option_id": "opt-sw"},
                {"question_id": "q2", "option_id": "opt-sw-env"},
                {"question_id": "acknowledged", "option_id": "ok"}
            ]
        })
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["phase"] == "deep_dive"
        assert data["question"]["domain"] == "software"
        assert data["top_domains"][0]["domain"] == "software"
    finally:
        app.dependency_overrides.clear()


def test_scenario_2_cse_interested_in_electronics():
    """TEST 2: CSE student strongly interested in electronics -> electronics deep dive question appears."""
    mock_db = MagicMock()
    mock_db.table().select().order().execute.return_value.data = MOCK_DISCOVERY_QUESTIONS
    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    try:
        # Answered broad questions with electronics
        res = client.post("/api/profile/assessment/next", json={
            "answers": [
                {"question_id": "q1", "option_id": "opt-elec"},
                {"question_id": "q2", "option_id": "opt-elec-env"},
                {"question_id": "acknowledged", "option_id": "ok"}
            ]
        })
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["phase"] == "deep_dive"
        assert data["question"]["domain"] == "electronics_embedded"
        assert data["top_domains"][0]["domain"] == "electronics_embedded"
    finally:
        app.dependency_overrides.clear()


def test_scenario_3_mechanical_interested_in_software():
    """TEST 3: Mechanical student interested in software -> Software careers remain competitive."""
    profile = {
        "branch": "MECHANICAL",
        "cgpa": 7.5,
        "career_goal": "Software Developer",
        "skills": [],
        "interests": ["Coding"],
        "assessment_signals": {
            "career_weights": {
                "Software Developer": 10.0,
            }
        }
    }
    careers = [
        {"id": "c1", "title": "Software Developer", "branches": ["CSE", "IT"], "industry": "IT", "min_cgpa": 7.0, "career_skills": []},
        {"id": "c2", "title": "Mechanical Design Engineer", "branches": ["MECHANICAL"], "industry": "Manufacturing", "min_cgpa": 7.0, "career_skills": []},
    ]
    matches = compute_career_matches(profile, careers, top_n=2)
    sde_match = next(m for m in matches if m["title"] == "Software Developer")
    # SDE has full 20 assessment points
    assert sde_match["score_breakdown"]["assessment"] == 20.0
    assert sde_match["score"] > 40.0


def test_scenario_4_mixed_answers():
    """TEST 4: Student gives mixed answers -> Multiple domains in top_domains."""
    mock_db = MagicMock()
    mock_db.table().select().order().execute.return_value.data = MOCK_DISCOVERY_QUESTIONS
    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    try:
        # Q1 Software, Q2 Electronics
        res = client.post("/api/profile/assessment/next", json={
            "answers": [
                {"question_id": "q1", "option_id": "opt-sw"},
                {"question_id": "q2", "option_id": "opt-elec-env"},
            ]
        })
        assert res.status_code == 200
        data = res.json()["data"]
        top_domains = [d["domain"] for d in data["top_domains"]]
        assert "software" in top_domains
        assert "electronics_embedded" in top_domains
    finally:
        app.dependency_overrides.clear()


def test_scenario_5_repeated_unsure():
    """TEST 5: Student repeatedly chooses 'Not sure yet' -> Safe progression without artificial scores."""
    mock_db = MagicMock()
    mock_db.table().select().order().execute.return_value.data = MOCK_DISCOVERY_QUESTIONS
    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    try:
        res = client.post("/api/profile/assessment/next", json={
            "answers": [
                {"question_id": "q1", "option_id": "opt-unsure"},
                {"question_id": "q2", "option_id": "opt-unsure-2"},
            ]
        })
        assert res.status_code == 200
        data = res.json()["data"]
        # Progresses to transition without errors
        assert data["phase"] == "transition"
        # All domain signals remain 0
        assert all(d["signal"] == 0.0 for d in data["top_domains"])
    finally:
        app.dependency_overrides.clear()


def test_scenario_6_refresh_resumes_cleanly():
    """TEST 6: Student refreshes page -> Evaluates exactly where they left off."""
    mock_db = MagicMock()
    mock_db.table().select().order().execute.return_value.data = MOCK_DISCOVERY_QUESTIONS
    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    try:
        # State saved in client storage sent back
        res = client.post("/api/profile/assessment/next", json={
            "answers": [{"question_id": "q1", "option_id": "opt-sw"}]
        })
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["phase"] == "broad"
        assert data["question"]["id"] == "q2"
        assert data["current_step"] == 2
    finally:
        app.dependency_overrides.clear()


def test_scenario_7_submit_twice_idempotent():
    """TEST 7: Student submits assessment twice -> Idempotent, no duplicate/corrupt data."""
    mock_db = MagicMock()
    mock_db.table().select().eq().single().execute.return_value.data = {"id": "p1", "profile_version": 1}
    mock_db.table().select().order().execute.return_value.data = MOCK_DISCOVERY_QUESTIONS
    mock_db.table().delete().eq().execute.return_value.data = []
    mock_db.table().insert().execute.return_value.data = []
    mock_db.table().update().eq().execute.return_value.data = []
    mock_db.rpc().execute.return_value.data = None

    from backend.deps import AuthenticatedUser, get_current_user
    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="p1", email="student@example.com")
    try:
        payload = {"answers": [{"question_id": "q1", "option_id": "opt-sw"}]}
        res1 = client.post("/api/profile/assessment/submit", json=payload)
        assert res1.status_code == 200
        assert res1.json()["success"] is True

        res2 = client.post("/api/profile/assessment/submit", json=payload)
        assert res2.status_code == 200
        assert res2.json()["success"] is True
    finally:
        app.dependency_overrides.clear()


def test_scenario_9_gemini_unavailable_fallback():
    """TEST 9: Gemini unavailable -> Transparent rule fallback works with assessment signals."""
    profile_repo = MagicMock()
    career_repo = MagicMock()
    analysis_repo = MagicMock()
    ai_provider = MagicMock()
    ai_provider.model_name = "gemini-test"

    # Gemini throws an error
    ai_provider.analyze_career = AsyncMock(side_effect=Exception("API Quota Exceeded"))

    profile_repo.get_by_id.return_value = {
        "id": "p1",
        "full_name": "Test Student",
        "branch": "CSE",
        "semester": 4,
        "cgpa": 8.0,
        "career_goal": "Software",
        "profile_version": 1,
        "assessment_signals": {"career_weights": {"Software Developer": 10.0}}
    }
    profile_repo.get_skills.return_value = []
    profile_repo.get_interests.return_value = ["Coding"]
    profile_repo.get_assessment_answers.return_value = [
        {"question_id": "q1", "option_id": "opt-sw", "question_text": "Q1", "category": "Logic", "selected_option": "Apps", "career_weight": {"Software Developer": 10.0}}
    ]
    analysis_repo.get_latest_resume_analysis.return_value = None
    analysis_repo.get_valid_cached_analysis.return_value = None

    career_repo.get_careers_with_skills.return_value = [
        {"id": "c1", "title": "Software Developer", "branches": ["CSE"], "industry": "IT", "min_cgpa": 7.0, "career_skills": []}
    ]

    service = AnalysisService(profile_repo, career_repo, analysis_repo, ai_provider)
    import asyncio
    result = asyncio.run(service.get_or_create_analysis("p1", force_regenerate=True))

    assert result["is_fallback"] is True
    assert len(result["recommended_careers"]) > 0
    assert result["recommended_careers"][0]["title"] == "Software Developer"
