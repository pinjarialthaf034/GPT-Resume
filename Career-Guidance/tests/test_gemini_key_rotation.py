"""
CareerCompass AI — Automated Tests for Gemini Key Rotation, Failover & Real Deterministic Roadmap Fallback
Validates:
  1. Scalable key discovery (GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.) & backward compatibility
  2. Key 1 succeeds -> only Key 1 is used
  3. Key 1 fails (429/quota) -> Key 2 is attempted & succeeds
  4. Key 1 (429) and Key 2 (503) fail -> Key 3 is attempted & succeeds
  5. Non-rotatable errors (ValueError/programming error) do NOT rotate keys
  6. Rate-limited keys enter cooldown and are not immediately re-selected
  7. All keys fail -> deterministic career matching engine used with preserved match percentages
  8. All keys fail -> real deterministic roadmap generated from career metadata and required skills
  9. Fallback analysis is persisted to database with a valid UUID
 10. Fallback roadmap progress tracking & persistence (roadmap_progress)
 11. Security: API keys NEVER appear in logs, exceptions, or API responses
 12. Gemini success path returns personalized AI analysis with is_fallback=False
"""
import asyncio
import json
import logging
import os
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.ai.gemini_provider import GeminiProvider
from backend.ai.key_rotator import (
    KeyRotationManager,
    is_quota_or_rate_limit,
    is_rotatable_error,
)
from backend.ai.schemas import CareerAnalysisAIResponse
from backend.config import Settings
from backend.services.analysis_service import AnalysisService
from backend.services.matching_engine import (
    compute_career_matches,
    generate_fallback_roadmap,
)


# ---------------------------------------------------------------------------
# 1. Configuration & Key Discovery Tests
# ---------------------------------------------------------------------------

def test_scalable_key_discovery():
    """Verify GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3 are discovered in numerical order."""
    env_patch = {
        "GEMINI_API_KEY_3": "secret-key-three",
        "GEMINI_API_KEY_1": "secret-key-one",
        "GEMINI_API_KEY_2": "secret-key-two",
        "GEMINI_API_KEY": "legacy-key",
    }
    with patch.dict(os.environ, env_patch, clear=False):
        settings = Settings()
        keys = settings.gemini_api_keys

        # Ordered numerically: 1, 2, 3, then legacy if distinct
        assert keys[0] == "secret-key-one"
        assert keys[1] == "secret-key-two"
        assert keys[2] == "secret-key-three"
        assert "legacy-key" in keys
        assert len(keys) == 4


def test_key_discovery_deduplication_and_fallback():
    """Verify duplicates and empty strings are removed, and GEMINI_API_KEY acts as fallback."""
    env_patch = {
        "GEMINI_API_KEY_1": "same-key",
        "GEMINI_API_KEY_2": "same-key",
        "GEMINI_API_KEY_3": "  ",
    }
    # Clear out other GEMINI_API_KEY_* env vars
    cleaned_env = {k: v for k, v in os.environ.items() if not k.startswith("GEMINI_API_KEY_")}
    cleaned_env.update(env_patch)
    cleaned_env["GEMINI_API_KEY"] = "same-key"

    with patch.dict(os.environ, cleaned_env, clear=True):
        settings = Settings()
        keys = settings.gemini_api_keys
        assert keys == ["same-key"]


# ---------------------------------------------------------------------------
# 2. Key Rotation & Error Handling Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_key1_succeeds_only_key1_used():
    """When Key 1 succeeds, keys 2 and 3 must NEVER be called."""
    manager = KeyRotationManager(["key-1", "key-2", "key-3"])
    settings = Settings(gemini_model="gemini-1.5-flash")
    provider = GeminiProvider(settings, key_manager=manager)

    client1 = MagicMock()
    client2 = MagicMock()
    client3 = MagicMock()

    mock_resp = MagicMock()
    mock_resp.text = json.dumps({
        "summary": "Detailed personalized guidance for diploma students.",
        "recommended_careers": [{
            "career_id": "c-101",
            "title": "Software Developer",
            "score": 92.0,
            "reason": "Strong programming aptitude.",
            "matched_skills": ["Python", "SQL"],
            "missing_skills": ["Docker"]
        }],
        "strengths": ["Analytical reasoning"],
        "skill_gaps": [{
            "skill_name": "Docker",
            "current_level": "none",
            "required_level": "intermediate",
            "priority": "high",
            "learning_resource": "docker.com"
        }],
        "priority_skills": ["Docker"],
        "roadmap_steps": [{
            "step_number": 1,
            "title": "Core Foundations",
            "description": "Learn fundamentals.",
            "duration_weeks": 4,
            "skills_gained": ["Docker"],
            "resources": ["docs.docker.com"]
        }],
        "project_recommendations": [{
            "title": "Dockerized App",
            "description": "Deploy app.",
            "skills_practiced": ["Docker"],
            "difficulty": "intermediate",
            "estimated_hours": 15
        }],
        "next_steps": ["Start Docker basics"]
    })
    client1.models.generate_content.return_value = mock_resp

    with patch.object(manager, "get_client") as mock_get_client:
        def client_side_effect(slot):
            if slot.slot_number == 1:
                return client1
            elif slot.slot_number == 2:
                return client2
            return client3
        mock_get_client.side_effect = client_side_effect
        provider._client = client1

        result = await provider.analyze_career(
            profile={"full_name": "Aarav", "branch": "CSE"},
            career_matches=[{"career_id": "c-101", "title": "Software Developer", "score": 92.0}]
        )

        assert isinstance(result, CareerAnalysisAIResponse)
        assert client1.models.generate_content.call_count == 1
        assert client2.models.generate_content.call_count == 0
        assert client3.models.generate_content.call_count == 0


@pytest.mark.asyncio
async def test_key1_fails_key2_attempted(caplog):
    """When Key 1 fails with 429 quota exhaustion, Key 2 is attempted and succeeds."""
    manager = KeyRotationManager(["key-1", "key-2", "key-3"])
    settings = Settings(gemini_model="gemini-1.5-flash")
    provider = GeminiProvider(settings, key_manager=manager)

    client1 = MagicMock()
    client1.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for project")

    client2 = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({
        "summary": "Valid response generated via Key 2 successfully.",
        "recommended_careers": [{
            "career_id": "c-101",
            "title": "Software Developer",
            "score": 91.0,
            "reason": "Good programming skills.",
            "matched_skills": ["Java"],
            "missing_skills": ["SQL"]
        }],
        "strengths": ["Java OOP"],
        "skill_gaps": [],
        "priority_skills": ["SQL"],
        "roadmap_steps": [{
            "step_number": 1,
            "title": "Database Fundamentals",
            "description": "Learn SQL queries.",
            "duration_weeks": 4,
            "skills_gained": ["SQL"],
            "resources": ["sqlzoo.net"]
        }],
        "project_recommendations": [],
        "next_steps": ["Complete SQL course"]
    })
    client2.models.generate_content.return_value = mock_resp

    client3 = MagicMock()

    with patch.object(manager, "get_client") as mock_get_client:
        def client_side_effect(slot):
            if slot.slot_number == 1:
                return client1
            elif slot.slot_number == 2:
                return client2
            return client3
        mock_get_client.side_effect = client_side_effect
        provider._client = client1

        with caplog.at_level(logging.WARNING):
            result = await provider.analyze_career(
                profile={"full_name": "Priya", "branch": "CSE"},
                career_matches=[]
            )

        assert isinstance(result, CareerAnalysisAIResponse)
        assert client1.models.generate_content.call_count == 1
        assert client2.models.generate_content.call_count == 1
        assert client3.models.generate_content.call_count == 0

        # Verify safe logging: slot 1 failure was logged, and next key was attempted
        assert "Gemini provider attempt 1 failed" in caplog.text
        assert "trying next configured provider key" in caplog.text


@pytest.mark.asyncio
async def test_key1_and_key2_fail_key3_attempted():
    """When Key 1 (429) and Key 2 (503) fail, Key 3 is attempted and succeeds."""
    manager = KeyRotationManager(["key-1", "key-2", "key-3"])
    settings = Settings(gemini_model="gemini-1.5-flash")
    provider = GeminiProvider(settings, key_manager=manager)

    client1 = MagicMock()
    client1.models.generate_content.side_effect = Exception("429 Quota Exceeded")

    client2 = MagicMock()
    client2.models.generate_content.side_effect = Exception("503 Service Unavailable: High server load")

    client3 = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({
        "summary": "Key 3 came through with successful analysis.",
        "recommended_careers": [{
            "career_id": "c-102",
            "title": "Frontend Developer",
            "score": 88.0,
            "reason": "Good UI skills.",
            "matched_skills": ["HTML/CSS"],
            "missing_skills": ["React.js"]
        }],
        "strengths": ["Web Design"],
        "skill_gaps": [],
        "priority_skills": ["React.js"],
        "roadmap_steps": [{
            "step_number": 1,
            "title": "React Basics",
            "description": "Learn components.",
            "duration_weeks": 4,
            "skills_gained": ["React.js"],
            "resources": ["react.dev"]
        }],
        "project_recommendations": [],
        "next_steps": ["Build first React component"]
    })
    client3.models.generate_content.return_value = mock_resp

    with patch.object(manager, "get_client") as mock_get_client:
        def client_side_effect(slot):
            if slot.slot_number == 1:
                return client1
            elif slot.slot_number == 2:
                return client2
            return client3
        mock_get_client.side_effect = client_side_effect
        provider._client = client1

        result = await provider.analyze_career(
            profile={"full_name": "Rohan", "branch": "IT"},
            career_matches=[]
        )

        assert isinstance(result, CareerAnalysisAIResponse)
        assert client1.models.generate_content.call_count == 1
        # Key 2 fails with 503 -> attempts up to MAX_RETRIES or rotated
        assert client2.models.generate_content.call_count >= 1
        assert client3.models.generate_content.call_count == 1


@pytest.mark.asyncio
async def test_no_rotation_on_programming_error():
    """Non-rotatable errors (e.g. TypeError, ValueError from bad logic) must raise immediately without rotating keys."""
    manager = KeyRotationManager(["key-1", "key-2"])
    settings = Settings(gemini_model="gemini-1.5-flash")
    provider = GeminiProvider(settings, key_manager=manager)

    client1 = MagicMock()
    # TypeError is a code bug, not a provider outage
    client1.models.generate_content.side_effect = TypeError("Invalid argument types passed to generate_content")

    client2 = MagicMock()

    with patch.object(manager, "get_client") as mock_get_client:
        mock_get_client.side_effect = lambda slot: client1 if slot.slot_number == 1 else client2
        provider._client = client1

        with pytest.raises(TypeError) as exc:
            await provider._call_with_retry("prompt", "system")

        assert "Invalid argument types" in str(exc.value)
        assert client1.models.generate_content.call_count == 1
        assert client2.models.generate_content.call_count == 0


def test_key_cooldown_prevents_immediate_reuse():
    """Rate-limited keys enter cooldown and are bypassed on subsequent requests."""
    manager = KeyRotationManager(["key-1", "key-2"], cooldown_seconds=60.0)
    slots = manager.get_candidate_slots()
    assert len(slots) == 2
    assert slots[0].slot_number == 1

    # Key 1 hits 429 quota
    quota_err = Exception("429 ResourceExhausted: rate limit exceeded")
    manager.mark_failure(slots[0], quota_err)

    # Next candidate slots should skip Key 1 and start with Key 2
    next_slots = manager.get_candidate_slots()
    assert len(next_slots) == 1
    assert next_slots[0].slot_number == 2


# ---------------------------------------------------------------------------
# 3. Deterministic Fallback & Real Roadmap Tests
# ---------------------------------------------------------------------------

def test_deterministic_matching_preserves_ranking_and_percentages():
    """When Gemini is unavailable, matching_engine computes exact match percentages and rankings."""
    student = {
        "branch": "Mechanical",
        "cgpa": 8.0,
        "career_goal": "Mechanical Design Engineer",
        "skills": [{"name": "SolidWorks", "proficiency": "intermediate"}],
        "interests": ["3D Modeling", "Automobiles"],
    }
    catalog = [
        {
            "id": "c-mech",
            "title": "Mechanical Design Engineer",
            "branches": ["MECHANICAL", "AUTOMOBILE"],
            "industry": "Manufacturing",
            "min_cgpa": 7.0,
            "career_skills": [{"skill_id": "sk-cad", "skills": {"name": "AutoCAD (Mech)"}, "required_level": "intermediate", "weight": 1.5}],
        },
        {
            "id": "c-sde",
            "title": "Software Developer",
            "branches": ["CSE", "IT"],
            "industry": "IT",
            "min_cgpa": 7.0,
            "career_skills": [{"skill_id": "sk-java", "skills": {"name": "Java"}, "required_level": "intermediate", "weight": 1.5}],
        }
    ]

    matches = compute_career_matches(student, catalog, top_n=2)
    assert len(matches) == 2
    assert matches[0]["title"] == "Mechanical Design Engineer"
    assert matches[0]["score"] > matches[1]["score"]
    assert "branch" in matches[0]["score_breakdown"]
    assert "skills" in matches[0]["score_breakdown"]


def test_all_keys_fail_generates_real_fallback_roadmap():
    """All Gemini keys fail -> generate_fallback_roadmap creates a real 4-milestone roadmap from career data."""
    target_career = {
        "career_id": "c-sde",
        "title": "Software Developer",
        "matched_skills": ["Python", "Git"],
        "missing_skills": ["SQL", "Data Structures", "Docker"],
    }
    student = {"branch": "Computer Engineering"}

    roadmap = generate_fallback_roadmap(target_career, student)

    assert roadmap["career_target"] == "Software Developer"
    steps = roadmap["roadmap_steps"]
    assert len(steps) == 4

    # Verify structured milestones
    assert steps[0]["step_number"] == 1
    assert "Core Technical Foundations" in steps[0]["title"]
    assert steps[0]["duration_weeks"] == 4
    assert len(steps[0]["skills_gained"]) > 0
    assert len(steps[0]["resources"]) > 0

    assert steps[1]["step_number"] == 2
    assert steps[2]["step_number"] == 3
    assert steps[3]["step_number"] == 4
    assert "Capstone" in steps[3]["title"]

    # Verify project recommendations from catalog
    projects = roadmap["project_recommendations"]
    assert len(projects) >= 1
    assert "Weather API Integration" in projects[0]["title"] or "CLI" in projects[0]["title"]
    assert projects[0]["difficulty"] in ("beginner", "intermediate")
    assert projects[0]["estimated_hours"] > 0


@pytest.mark.asyncio
async def test_fallback_analysis_persisted_in_database():
    """When Gemini fails, fallback analysis must be saved to DB so roadmap.html and roadmap_progress work."""
    mock_profile_repo = MagicMock()
    mock_profile_repo.get_by_id.return_value = {
        "id": "p-100",
        "full_name": "Sneha",
        "branch": "Civil",
        "semester": 5,
        "cgpa": 7.8,
        "profile_version": 1,
    }
    mock_profile_repo.get_skills.return_value = []
    mock_profile_repo.get_interests.return_value = ["Construction"]
    mock_profile_repo.get_assessment_answers.return_value = []

    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_valid_cached_analysis.return_value = None
    mock_analysis_repo.get_latest_resume_analysis.return_value = None

    # Supabase save_analysis returns the inserted row with real UUID
    saved_analysis_row = {
        "id": "uuid-analysis-fallback-999",
        "profile_id": "p-100",
        "model_name": "rule-engine-fallback",
        "summary": "Preliminary Rule-Based Matches: Gemini AI is temporarily offline...",
        "roadmap_steps": [{"step_number": 1, "title": "Step 1", "description": "Desc"}],
    }
    mock_analysis_repo.save_analysis.return_value = saved_analysis_row
    mock_analysis_repo.get_latest_analysis.return_value = saved_analysis_row
    mock_analysis_repo.get_roadmap_progress.return_value = [1]

    mock_career_repo = MagicMock()
    mock_career_repo.get_careers_with_skills.return_value = [{
        "id": "c-civil",
        "title": "Site Engineer",
        "branches": ["CIVIL"],
        "industry": "Construction",
        "career_skills": [{"skill_id": "s-surv", "skills": {"name": "Surveying"}, "required_level": "intermediate", "weight": 1.0}],
    }]
    mock_career_repo.get_career_by_id.return_value = None

    mock_ai = MagicMock(spec=GeminiProvider)
    mock_ai.model_name = "gemini-1.5-flash"
    mock_ai.analyze_career = AsyncMock(side_effect=RuntimeError("All configured Gemini API keys exhausted or unavailable: 429"))

    service = AnalysisService(
        profile_repo=mock_profile_repo,
        career_repo=mock_career_repo,
        analysis_repo=mock_analysis_repo,
        ai_provider=mock_ai,
    )

    result = await service.get_or_create_analysis("p-100", force_regenerate=True)

    # 1. Verify fallback response properties
    assert result["is_fallback"] is True
    assert result["is_cached"] is False
    assert result["model_name"] == "rule-engine-fallback"
    assert "Preliminary Rule-Based Matches" in result["summary"]
    assert result["id"] == "uuid-analysis-fallback-999"
    assert len(result["roadmap_steps"]) == 4

    # 2. Verify save_analysis was called to persist fallback
    mock_analysis_repo.save_analysis.assert_called_once()

    # 3. Verify roadmap API retrieves persisted fallback
    roadmap_progress = service.get_roadmap_progress("p-100")
    assert roadmap_progress["analysis_id"] == "uuid-analysis-fallback-999"
    assert len(roadmap_progress["roadmap_steps"]) > 0
    assert roadmap_progress["completed_steps"] == [1]


# ---------------------------------------------------------------------------
# 4. Security & Sensitive Credential Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_keys_never_appear_in_logs_or_responses(caplog):
    """Verify that actual Gemini API key strings NEVER appear in logs, exceptions, or payloads."""
    secret_key_1 = "AIzaSySecretKeyOneAlpha123456789"
    secret_key_2 = "AIzaSySecretKeyTwoBeta987654321"

    manager = KeyRotationManager([secret_key_1, secret_key_2])
    settings = Settings(gemini_model="gemini-1.5-flash")
    provider = GeminiProvider(settings, key_manager=manager)

    client1 = MagicMock()
    client1.models.generate_content.side_effect = Exception("429 ResourceExhausted: rate limit exceeded")
    client2 = MagicMock()
    client2.models.generate_content.side_effect = Exception("503 Service Unavailable")

    with patch.object(manager, "get_client") as mock_get_client:
        mock_get_client.side_effect = lambda slot: client1 if slot.slot_number == 1 else client2
        provider._client = client1

        with caplog.at_level(logging.DEBUG):
            with pytest.raises(RuntimeError) as exc_info:
                await provider._call_with_retry("prompt", "system")

        err_message = str(exc_info.value)
        logs_text = caplog.text

        # 1. Check exception string
        assert secret_key_1 not in err_message
        assert secret_key_2 not in err_message

        # 2. Check logs
        assert secret_key_1 not in logs_text
        assert secret_key_2 not in logs_text

        # 3. Ensure safe slot-based log appears
        assert "Gemini provider attempt 1 failed" in logs_text
        assert "Gemini provider attempt 2 failed" in logs_text


# ---------------------------------------------------------------------------
# 5. Gemini Success Path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gemini_success_returns_ai_analysis():
    """Verify standard happy path when Gemini succeeds returns AI-personalized analysis with is_fallback=False."""
    mock_profile_repo = MagicMock()
    mock_profile_repo.get_by_id.return_value = {
        "id": "p-200",
        "full_name": "Aarav",
        "branch": "CSE",
        "semester": 6,
        "cgpa": 8.9,
        "profile_version": 1,
    }
    mock_profile_repo.get_skills.return_value = []
    mock_profile_repo.get_interests.return_value = ["Coding"]
    mock_profile_repo.get_assessment_answers.return_value = []

    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_valid_cached_analysis.return_value = None
    mock_analysis_repo.get_latest_resume_analysis.return_value = None
    mock_analysis_repo.save_analysis.return_value = {
        "id": "ai-analysis-uuid-123",
        "summary": "Genuine AI analysis by Gemini.",
    }

    mock_career_repo = MagicMock()
    mock_career_repo.get_careers_with_skills.return_value = []

    mock_ai_result = MagicMock()
    mock_ai_result.summary = "Personalized Gemini analysis."
    mock_ai_result.recommended_careers = []
    mock_ai_result.strengths = ["Problem solving"]
    mock_ai_result.skill_gaps = []
    mock_ai_result.priority_skills = ["Python"]
    mock_ai_result.roadmap_steps = []
    mock_ai_result.project_recommendations = []
    mock_ai_result.next_steps = []

    mock_ai = MagicMock(spec=GeminiProvider)
    mock_ai.model_name = "gemini-1.5-flash"
    mock_ai.analyze_career = AsyncMock(return_value=mock_ai_result)

    service = AnalysisService(
        profile_repo=mock_profile_repo,
        career_repo=mock_career_repo,
        analysis_repo=mock_analysis_repo,
        ai_provider=mock_ai,
    )

    result = await service.get_or_create_analysis("p-200", force_regenerate=True)

    assert result["is_fallback"] is False
    assert result["is_cached"] is False
    assert result["id"] == "ai-analysis-uuid-123"
    mock_ai.analyze_career.assert_called_once()
