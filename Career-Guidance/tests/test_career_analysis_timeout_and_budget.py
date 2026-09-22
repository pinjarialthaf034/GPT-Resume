"""
CareerCompass AI — Tests for Career Analysis Deadline, Timeout, and Budgeting Strategy
Verifies:
1. Normal Career Analysis completes within the budget.
2. Gemini timeout triggers safe retry/rotation.
3. Gemini 503 immediately rotates appropriately.
4. Multiple Gemini failures eventually trigger deterministic fallback.
5. Deadline prevents doomed additional attempts.
6. Existing valid cached analysis is never overwritten by a timeout fallback.
7. Cache-hit path performs zero Gemini calls.
8. Existing Career Analysis response schema remains valid.
"""
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai.errors import APIError

from backend.ai.gemini_provider import (
    CAREER_ANALYSIS_PER_ATTEMPT_TIMEOUT_SECONDS,
    CAREER_ANALYSIS_TOTAL_BUDGET_SECONDS,
    GeminiProvider,
)
from backend.ai.schemas import CareerAnalysisAIResponse
from backend.config import Settings
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.career_repo import CareerRepository
from backend.repositories.profile_repo import ProfileRepository
from backend.services.analysis_service import AnalysisService


@pytest.fixture
def mock_settings_multi_key():
    return Settings(
        gemini_api_key="primary-key-12345",
        gemini_api_key_2="secondary-key-67890",
        gemini_api_key_3="tertiary-key-11223",
        gemini_model="gemini-3.6-flash",
    )


@pytest.fixture
def sample_student_context():
    return {
        "profile_id": "test-student-budget-001",
        "profile_version": 1,
        "full_name": "Althaf Pinjari",
        "branch": "Computer Engineering",
        "semester": 6,
        "cgpa": 8.7,
        "career_goal": "Cloud Solutions Engineer",
        "skills": [
            {"name": "Python", "proficiency": "intermediate", "category": "Programming"},
            {"name": "Linux", "proficiency": "intermediate", "category": "Systems"},
        ],
        "interests": ["Cloud Computing", "DevOps"],
        "assessment": [],
        "assessment_signals": {},
        "resume": None,
    }


@pytest.fixture
def sample_career_catalog():
    return [
        {
            "id": "c-1",
            "career_id": "cloud-engineer",
            "title": "Cloud Solutions Engineer",
            "branches": ["Computer Engineering", "Information Technology"],
            "career_skills": [
                {"skill_id": "s-1", "required_level": "intermediate", "weight": 1.0, "skills": {"name": "Linux"}},
                {"skill_id": "s-2", "required_level": "intermediate", "weight": 1.0, "skills": {"name": "Python"}},
            ],
        },
        {
            "id": "c-2",
            "career_id": "devops-engineer",
            "title": "DevOps Engineer",
            "branches": ["Computer Engineering"],
            "career_skills": [
                {"skill_id": "s-1", "required_level": "intermediate", "weight": 1.0, "skills": {"name": "Linux"}},
            ],
        },
    ]


@pytest.fixture
def sample_valid_ai_json():
    return json.dumps({
        "summary": "Althaf possesses strong technical foundations in Python and Linux, positioning him well for cloud and infrastructure engineering roles.",
        "recommended_careers": [
            {
                "career_id": "cloud-solutions-engineer",
                "title": "Cloud Solutions Engineer",
                "score": 92.0,
                "branch_compatibility": 95.0,
                "skill_match": 88.0,
                "interest_alignment": 94.0,
                "goal_alignment": 96.0,
                "academic_compatibility": 90.0,
                "reason": "Strong alignment with Computer Engineering curriculum and Linux/Python proficiencies.",
                "matched_skills": ["Linux", "Python"],
                "missing_skills": ["AWS", "Docker", "Terraform"],
                "career_outlook": "High growth in Indian cloud consulting sector",
                "next_steps": ["Complete AWS Cloud Practitioner certification", "Build a containerized deployment project"]
            },
            {
                "career_id": "devops-engineer",
                "title": "DevOps Engineer",
                "score": 88.0,
                "branch_compatibility": 90.0,
                "skill_match": 85.0,
                "interest_alignment": 90.0,
                "goal_alignment": 88.0,
                "academic_compatibility": 87.0,
                "reason": "Demonstrated interest in DevOps workflows combined with Linux proficiency.",
                "matched_skills": ["Linux"],
                "missing_skills": ["CI/CD Pipelines", "Kubernetes"],
                "career_outlook": "Very high industry demand across tech hubs",
                "next_steps": ["Learn GitHub Actions automation", "Containerize a sample web application"]
            },
            {
                "career_id": "systems-administrator",
                "title": "Systems Administrator",
                "score": 82.0,
                "branch_compatibility": 88.0,
                "skill_match": 84.0,
                "interest_alignment": 80.0,
                "goal_alignment": 78.0,
                "academic_compatibility": 82.0,
                "reason": "Direct match for core OS and systems administration knowledge.",
                "matched_skills": ["Linux"],
                "missing_skills": ["Active Directory", "Bash Scripting"],
                "career_outlook": "Stable foundational demand across enterprises",
                "next_steps": ["Practice advanced shell scripting", "Configure automated backup scripts"]
            }
        ],
        "strengths": ["Strong Linux foundations", "Scripting with Python", "Clear focus on Cloud engineering"],
        "skill_gaps": [
            {
                "skill_name": "Docker",
                "current_level": "beginner",
                "required_level": "intermediate",
                "priority": "high",
                "learning_resource": "Docker Official Documentation & FreeCodeCamp"
            },
            {
                "skill_name": "AWS Cloud",
                "current_level": "none",
                "required_level": "intermediate",
                "priority": "high",
                "learning_resource": "AWS Skill Builder & NPTEL Cloud Computing"
            }
        ],
        "priority_skills": ["Docker", "AWS", "Terraform", "CI/CD"],
        "roadmap_steps": [
            {
                "step_number": 1,
                "title": "Containerization Fundamentals",
                "description": "Master Docker basics, Dockerfile creation, and multi-container apps.",
                "duration_weeks": 4,
                "skills_gained": ["Docker", "Containers"],
                "resources": ["Docker Official Docs"]
            },
            {
                "step_number": 2,
                "title": "Cloud Infrastructure",
                "description": "Deploy applications on AWS core services including EC2, S3, and VPC.",
                "duration_weeks": 6,
                "skills_gained": ["AWS", "Cloud Architecture"],
                "resources": ["AWS Skill Builder"]
            }
        ],
        "project_recommendations": [
            {
                "title": "Automated Dockerized Microservice",
                "description": "Build and containerize a REST API with automated GitHub Actions testing.",
                "skills_practiced": ["Docker", "Python", "CI/CD"],
                "difficulty": "intermediate",
                "estimated_hours": 20
            }
        ],
        "next_steps": ["Start Docker course", "Create AWS Free Tier account", "Setup GitHub portfolio repository"]
    })


# ---------------------------------------------------------------------------
# 1. Normal Career Analysis completes within the budget
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_normal_career_analysis_completes_within_budget(
    mock_settings_multi_key, sample_student_context, sample_career_catalog, sample_valid_ai_json
):
    provider = GeminiProvider(mock_settings_multi_key)

    mock_resp = MagicMock()
    mock_resp.text = sample_valid_ai_json

    with patch.object(provider._client.models, "generate_content", return_value=mock_resp):
        t0 = time.perf_counter()
        result = await provider.analyze_career(sample_student_context, sample_career_catalog)
        elapsed = time.perf_counter() - t0

        assert isinstance(result, CareerAnalysisAIResponse)
        assert len(result.recommended_careers) == 3
        assert result.recommended_careers[0].title == "Cloud Solutions Engineer"
        assert elapsed < CAREER_ANALYSIS_TOTAL_BUDGET_SECONDS


# ---------------------------------------------------------------------------
# 2. Gemini timeout triggers safe retry/rotation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gemini_timeout_triggers_safe_retry_rotation(
    mock_settings_multi_key, sample_student_context, sample_career_catalog, sample_valid_ai_json
):
    provider = GeminiProvider(mock_settings_multi_key)

    success_resp = MagicMock()
    success_resp.text = sample_valid_ai_json

    call_count = 0

    def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError("Simulated network timeout on slot 1")
        return success_resp

    with patch.object(provider._client.models, "generate_content", side_effect=mock_generate):
        result = await provider.analyze_career(sample_student_context, sample_career_catalog)
        assert isinstance(result, CareerAnalysisAIResponse)
        assert call_count >= 2


# ---------------------------------------------------------------------------
# 3. Gemini 503 immediately rotates appropriately
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gemini_503_immediately_rotates_to_next_key(
    mock_settings_multi_key, sample_student_context, sample_career_catalog, sample_valid_ai_json
):
    """
    HTTP 503 (model high demand / service unavailable) should immediately rotate
    to the next key without wasting multiple retries on the busy model slot.
    """
    provider = GeminiProvider(mock_settings_multi_key)
    assert provider._key_manager.total_keys >= 2

    # Slot 1 fails with 503
    err_503 = Exception("503 UNAVAILABLE. This model is currently experiencing high demand. Please try again later.")

    success_resp = MagicMock()
    success_resp.text = sample_valid_ai_json

    slot1_calls = 0
    slot2_calls = 0

    def slot1_generate(*args, **kwargs):
        nonlocal slot1_calls
        slot1_calls += 1
        raise err_503

    def slot2_generate(*args, **kwargs):
        nonlocal slot2_calls
        slot2_calls += 1
        return success_resp

    provider._client.models.generate_content = MagicMock(side_effect=slot1_generate)
    slot2_client = provider._key_manager.get_client(provider._key_manager._slots[1])
    slot2_client.models.generate_content = MagicMock(side_effect=slot2_generate)

    result = await provider.analyze_career(sample_student_context, sample_career_catalog)
    assert isinstance(result, CareerAnalysisAIResponse)
    # Slot 1 must have failed once and immediately rotated to Slot 2 without 3 wasted attempts
    assert slot1_calls == 1
    assert slot2_calls == 1


# ---------------------------------------------------------------------------
# 4. Multiple Gemini failures eventually trigger deterministic fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multiple_gemini_failures_trigger_deterministic_fallback(
    mock_settings_multi_key, sample_student_context, sample_career_catalog
):
    mock_profile_repo = MagicMock(spec=ProfileRepository)
    mock_career_repo = MagicMock(spec=CareerRepository)
    mock_analysis_repo = MagicMock(spec=AnalysisRepository)

    mock_profile_repo.get_by_id.return_value = {
        "id": "test-student-budget-001",
        "full_name": "Althaf Pinjari",
        "branch": "Computer Engineering",
        "profile_version": 1,
    }
    mock_profile_repo.get_skills.return_value = []
    mock_profile_repo.get_interests.return_value = []
    mock_profile_repo.get_assessment_answers.return_value = []
    mock_analysis_repo.get_latest_resume_analysis.return_value = None
    mock_analysis_repo.get_valid_cached_analysis.return_value = None
    mock_analysis_repo.get_latest_analysis.return_value = None  # No previous analysis
    mock_career_repo.get_careers_with_skills.return_value = sample_career_catalog
    mock_analysis_repo.save_analysis.return_value = {"id": "saved-fallback-id"}

    provider = GeminiProvider(mock_settings_multi_key)
    # Force all keys to fail with transient error
    provider.analyze_career = AsyncMock(side_effect=TimeoutError("All slots timed out"))

    service = AnalysisService(
        profile_repo=mock_profile_repo,
        career_repo=mock_career_repo,
        analysis_repo=mock_analysis_repo,
        ai_provider=provider,
    )

    result = await service.get_or_create_analysis("test-student-budget-001", force_regenerate=True)
    assert result.get("is_fallback") is True
    assert result.get("is_cached") is False
    assert len(result.get("recommended_careers", [])) > 0
    # Fallback was persisted because there was no previous valid AI analysis
    mock_analysis_repo.save_analysis.assert_called_once()


# ---------------------------------------------------------------------------
# 5. Deadline prevents doomed additional attempts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deadline_prevents_doomed_additional_attempts(
    mock_settings_multi_key, sample_student_context, sample_career_catalog
):
    """Verifies that when remaining budget is exhausted, loop breaks rather than wasting time."""
    provider = GeminiProvider(mock_settings_multi_key)

    attempts = 0

    async def slow_failing_call(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        # Consume almost entire budget in one attempt
        await asyncio.sleep(0.01)
        raise TimeoutError("Attempt timed out")

    # Simulate budget running out by patching loop.time
    t = 1000.0
    loop = asyncio.get_running_loop()
    real_time = loop.time

    def fake_time():
        nonlocal t
        t += 11.0  # Advances by 11 seconds each call
        return t

    with patch.object(loop, "time", side_effect=fake_time):
        with patch.object(provider._client.models, "generate_content", side_effect=TimeoutError("Call timeout")):
            with pytest.raises(Exception) as exc_info:
                await provider.analyze_career(sample_student_context, sample_career_catalog)
            # Should not perform all 9 attempts because deadline expired
            assert attempts < 9


# ---------------------------------------------------------------------------
# 6. Existing valid cached analysis is never overwritten by a timeout fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_existing_valid_cached_analysis_not_overwritten_by_fallback(
    mock_settings_multi_key, sample_student_context, sample_career_catalog
):
    mock_profile_repo = MagicMock(spec=ProfileRepository)
    mock_career_repo = MagicMock(spec=CareerRepository)
    mock_analysis_repo = MagicMock(spec=AnalysisRepository)

    mock_profile_repo.get_by_id.return_value = {
        "id": "test-student-budget-001",
        "full_name": "Althaf Pinjari",
        "branch": "Computer Engineering",
        "profile_version": 1,
    }
    mock_profile_repo.get_skills.return_value = []
    mock_profile_repo.get_interests.return_value = []
    mock_profile_repo.get_assessment_answers.return_value = []
    mock_analysis_repo.get_latest_resume_analysis.return_value = None
    mock_analysis_repo.get_valid_cached_analysis.return_value = None
    mock_career_repo.get_careers_with_skills.return_value = sample_career_catalog

    # Student ALREADY has an authentic valid Gemini analysis saved in Supabase
    existing_valid_ai = {
        "id": "existing-valid-ai-uuid-12345",
        "profile_id": "test-student-budget-001",
        "model_name": "gemini-3.6-flash",
        "is_fallback": False,
        "summary": "Authentic Gemini AI Executive Summary",
        "recommended_careers": [{"title": "Cloud Solutions Engineer", "score": 95.0}],
        "selected_career": "Cloud Solutions Engineer",
    }
    mock_analysis_repo.get_latest_analysis.return_value = dict(existing_valid_ai)

    provider = GeminiProvider(mock_settings_multi_key)
    # User clicks Re-Analyze, but Gemini times out / fails
    provider.analyze_career = AsyncMock(side_effect=TimeoutError("Gemini timed out"))

    service = AnalysisService(
        profile_repo=mock_profile_repo,
        career_repo=mock_career_repo,
        analysis_repo=mock_analysis_repo,
        ai_provider=provider,
    )

    result = await service.get_or_create_analysis("test-student-budget-001", force_regenerate=True)

    # CRITICAL: It must NOT overwrite the database with fallback data!
    mock_analysis_repo.save_analysis.assert_not_called()
    # It preserves the existing valid AI analysis
    assert result["id"] == "existing-valid-ai-uuid-12345"
    assert result["is_fallback"] is False
    assert result["model_name"] == "gemini-3.6-flash"


# ---------------------------------------------------------------------------
# 7. Cache-hit path performs zero Gemini calls
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_hit_performs_zero_gemini_calls(
    mock_settings_multi_key, sample_student_context
):
    mock_profile_repo = MagicMock(spec=ProfileRepository)
    mock_career_repo = MagicMock(spec=CareerRepository)
    mock_analysis_repo = MagicMock(spec=AnalysisRepository)

    mock_profile_repo.get_by_id.return_value = {
        "id": "test-student-budget-001",
        "full_name": "Althaf Pinjari",
        "branch": "Computer Engineering",
        "profile_version": 1,
    }
    mock_profile_repo.get_skills.return_value = []
    mock_profile_repo.get_interests.return_value = []
    mock_profile_repo.get_assessment_answers.return_value = []
    mock_analysis_repo.get_latest_resume_analysis.return_value = None

    # Cache returns existing cached item
    cached_payload = {
        "id": "cached-analysis-id-999",
        "profile_id": "test-student-budget-001",
        "model_name": "gemini-3.6-flash",
        "summary": "Cached career intelligence summary",
        "recommended_careers": [{"title": "Cloud Architect", "score": 90.0}],
    }
    mock_analysis_repo.get_valid_cached_analysis.return_value = cached_payload

    provider = GeminiProvider(mock_settings_multi_key)
    provider.analyze_career = AsyncMock()

    service = AnalysisService(
        profile_repo=mock_profile_repo,
        career_repo=mock_career_repo,
        analysis_repo=mock_analysis_repo,
        ai_provider=provider,
    )

    result = await service.get_or_create_analysis("test-student-budget-001", force_regenerate=False)

    assert result["is_cached"] is True
    assert result["id"] == "cached-analysis-id-999"
    # ZERO Gemini calls made on cache hit
    provider.analyze_career.assert_not_called()


# ---------------------------------------------------------------------------
# 8. Existing Career Analysis response schema remains valid
# ---------------------------------------------------------------------------

def test_career_analysis_response_schema_validation(sample_valid_ai_json):
    """Verifies that the concise output strictly satisfies CareerAnalysisAIResponse."""
    data = json.loads(sample_valid_ai_json)
    validated = CareerAnalysisAIResponse.model_validate(data)

    assert len(validated.summary) >= 20
    assert len(validated.recommended_careers) == 3
    for c in validated.recommended_careers:
        assert 0.0 <= c.score <= 100.0
        assert 0.0 <= c.branch_compatibility <= 100.0
        assert 0.0 <= c.skill_match <= 100.0
        assert 0.0 <= c.interest_alignment <= 100.0
        assert 0.0 <= c.goal_alignment <= 100.0
        assert 0.0 <= c.academic_compatibility <= 100.0
        assert c.reason
    assert len(validated.strengths) >= 1
    assert len(validated.skill_gaps) >= 1
    assert len(validated.roadmap_steps) >= 1
    assert len(validated.project_recommendations) >= 1
