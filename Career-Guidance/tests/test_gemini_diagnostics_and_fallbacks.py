"""
CareerCompass AI — Targeted Tests for Gemini Error Classification, Diagnostics & Fallback Guarantees
Covers:
  1. Valid Gemini key diagnostic & safe inspection (no secret exposure)
  2. Invalid Gemini key / Auth error (401/403) diagnosed as GeminiConfigError (never quota)
  3. Missing / Mock Gemini key diagnosed as GeminiConfigError
  4. Multiple Gemini keys discovered in numeric priority order
  5. First key succeeds -> second key never called
  6. First key fails (429 quota) -> second key called & succeeds
  7. All keys fail on transient outage -> deterministic fallback persisted with valid UUID
  8. Model unavailable (404) diagnosed immediately without rotating
  9. Network timeout rotatable across keys
 10. AI roadmap persistence & progress tracking
"""
import asyncio
import json
import logging
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from backend.ai.errors import (
    GeminiConfigError,
    GeminiError,
    GeminiResponseError,
    GeminiTransientError,
    classify_gemini_error,
    get_safe_error_summary,
)
from backend.ai.gemini_provider import GeminiProvider
from backend.ai.key_rotator import KeyRotationManager, is_quota_or_rate_limit, is_rotatable_error
from backend.ai.schemas import CareerAnalysisAIResponse
from backend.config import Settings
from backend.services.analysis_service import AnalysisService
from backend.services.matching_engine import generate_fallback_roadmap


# ---------------------------------------------------------------------------
# 1. Valid Gemini Key Diagnostics & Safe Inspection
# ---------------------------------------------------------------------------

def test_valid_gemini_key_safe_diagnostics():
    """Verify get_gemini_diagnostics returns safe metadata without leaking secrets."""
    test_key = "AIzaSySecretRealKeyForTesting123456"
    settings = Settings(
        gemini_api_key=test_key,
        gemini_model="gemini-3.5-flash",
    )
    diag = settings.get_gemini_diagnostics()

    assert diag["configured"] is True
    assert diag["key_count"] >= 1
    assert diag["model"] == "gemini-3.5-flash"
    assert diag["active_key_index"] == 1

    # Ensure raw or partial keys NEVER appear in diagnostics dict or JSON serialization
    serialized = json.dumps(diag)
    assert test_key not in serialized
    assert "AIzaSy" not in serialized
    assert "123456" not in serialized


# ---------------------------------------------------------------------------
# 2. Invalid Gemini Key (Auth / 401 / 403) Diagnosed as GeminiConfigError
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_gemini_key_diagnosed_as_config_error():
    """Verify authentication error (401/403/API_KEY_INVALID) raises GeminiConfigError and is not misclassified as quota."""
    settings = Settings(gemini_api_key="invalid-key-xyz")
    manager = KeyRotationManager(["invalid-key-xyz"])
    provider = GeminiProvider(settings, key_manager=manager)

    client = MagicMock()
    client.models.generate_content.side_effect = Exception("403 PERMISSION_DENIED: API_KEY_INVALID")
    provider._client = client

    with patch.object(manager, "get_client", return_value=client):
        with pytest.raises(GeminiConfigError) as exc_info:
            await provider._call_with_retry("prompt", "system")

        err_msg = str(exc_info.value).lower()
        assert "authentication failed" in err_msg or "invalid" in err_msg
        # Must NOT be classified as quota
        assert not is_quota_or_rate_limit(Exception("403 PERMISSION_DENIED: API_KEY_INVALID"))


# ---------------------------------------------------------------------------
# 3. Missing / Mock Gemini Key Diagnosed as GeminiConfigError
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_or_mock_gemini_key_diagnosed():
    """Verify unconfigured/mock key immediately raises GeminiConfigError before network call."""
    settings = Settings(gemini_api_key="mock-gemini-key")
    # Patch gemini_api_keys to ensure only mock-gemini-key is present
    with patch.object(Settings, "gemini_api_keys", ["mock-gemini-key"]):
        provider = GeminiProvider(settings)

        with pytest.raises(GeminiConfigError) as exc_info:
            await provider._call_with_retry("test", "test")

        assert "not configured" in str(exc_info.value).lower() or "mock" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# 4. Multiple Gemini Keys Discovered in Numeric Order
# ---------------------------------------------------------------------------

def test_multiple_gemini_keys_numeric_order():
    """Verify GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3 discovery."""
    env = {
        "GEMINI_API_KEY_3": "key-three",
        "GEMINI_API_KEY_1": "key-one",
        "GEMINI_API_KEY_2": "key-two",
    }
    with patch.dict(os.environ, env, clear=False):
        settings = Settings()
        keys = settings.gemini_api_keys
        assert keys[0] == "key-one"
        assert keys[1] == "key-two"
        assert keys[2] == "key-three"


# ---------------------------------------------------------------------------
# 5. First Key Succeeds -> Second Key Never Called
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_key_succeeds_second_never_called():
    """When Key 1 succeeds, Key 2 must not be invoked."""
    manager = KeyRotationManager(["key-1", "key-2"])
    settings = Settings(gemini_model="gemini-3.5-flash")
    provider = GeminiProvider(settings, key_manager=manager)

    client1 = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({"status": "ok"})
    client1.models.generate_content.return_value = mock_resp

    client2 = MagicMock()

    with patch.object(manager, "get_client") as mock_gc:
        mock_gc.side_effect = lambda slot: client1 if slot.slot_number == 1 else client2
        provider._client = client1

        res = await provider._call_with_retry("test", "test")
        assert res == json.dumps({"status": "ok"})
        assert client1.models.generate_content.call_count == 1
        assert client2.models.generate_content.call_count == 0


# ---------------------------------------------------------------------------
# 6. First Key Fails (429 Quota) -> Second Key Called & Succeeds
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_key_fails_quota_second_succeeds():
    """When Key 1 fails with 429 quota exhaustion, Key 2 is attempted and succeeds."""
    manager = KeyRotationManager(["key-1", "key-2"])
    settings = Settings(gemini_model="gemini-3.5-flash")
    provider = GeminiProvider(settings, key_manager=manager)

    client1 = MagicMock()
    client1.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED: Quota exceeded")

    client2 = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({"status": "from-key-2"})
    client2.models.generate_content.return_value = mock_resp

    with patch.object(manager, "get_client") as mock_gc:
        mock_gc.side_effect = lambda slot: client1 if slot.slot_number == 1 else client2
        provider._client = client1

        res = await provider._call_with_retry("test", "test")
        assert res == json.dumps({"status": "from-key-2"})
        assert client1.models.generate_content.call_count == 1
        assert client2.models.generate_content.call_count == 1


# ---------------------------------------------------------------------------
# 7. All Keys Fail -> Deterministic Fallback Persisted with Valid UUID
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_all_keys_fail_triggers_persisted_fallback():
    """When all keys fail on quota/outage, deterministic fallback is generated and persisted."""
    mock_profile_repo = MagicMock()
    mock_profile_repo.get_by_id.return_value = {
        "id": "p-100",
        "full_name": "Test Student",
        "branch": "Computer Engineering",
        "semester": 6,
        "cgpa": 8.0,
        "career_goal": "Software Developer",
        "profile_version": 1,
    }
    mock_profile_repo.get_skills.return_value = [{"name": "Python", "proficiency": "intermediate"}]
    mock_profile_repo.get_interests.return_value = ["Coding"]
    mock_profile_repo.get_assessment_answers.return_value = []

    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_valid_cached_analysis.return_value = None
    mock_analysis_repo.get_latest_resume_analysis.return_value = None

    created_id = str(uuid.uuid4())
    mock_analysis_repo.save_analysis.return_value = {
        "id": created_id,
        "model_name": "rule-engine-fallback",
        "summary": "Preliminary Rule-Based Matches",
    }

    mock_career_repo = MagicMock()
    mock_career_repo.get_careers_with_skills.return_value = [{
        "career_id": "software-developer",
        "title": "Software Developer",
        "domain": "Computer Engineering",
        "required_skills": ["Python", "SQL"],
        "min_cgpa": 6.0,
    }]
    mock_career_repo.get_career_by_id.return_value = None

    mock_ai = MagicMock(spec=GeminiProvider)
    mock_ai.model_name = "gemini-3.5-flash"
    mock_ai.career_analysis_prompt_version = "v2.0"
    mock_ai.analyze_career = AsyncMock(
        side_effect=GeminiTransientError("All configured Gemini API keys exhausted")
    )

    service = AnalysisService(
        profile_repo=mock_profile_repo,
        career_repo=mock_career_repo,
        analysis_repo=mock_analysis_repo,
        ai_provider=mock_ai,
    )

    result = await service.get_or_create_analysis("p-100", force_regenerate=True)

    assert result["is_fallback"] is True
    assert result["id"] == created_id
    assert len(result["roadmap_steps"]) >= 3
    assert mock_analysis_repo.save_analysis.called


# ---------------------------------------------------------------------------
# 8. Model Unavailable (404) Diagnosed Immediately Without Rotating
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_model_unavailable_diagnosed_immediately():
    """Verify 404 NOT_FOUND model errors raise GeminiConfigError without pointless key rotation."""
    manager = KeyRotationManager(["key-1", "key-2"])
    settings = Settings(gemini_model="invalid-nonexistent-model")
    provider = GeminiProvider(settings, key_manager=manager)

    client1 = MagicMock()
    client1.models.generate_content.side_effect = Exception(
        "404 NOT_FOUND: models/invalid-nonexistent-model is not found for API version v1beta"
    )
    client2 = MagicMock()

    with patch.object(manager, "get_client") as mock_gc:
        mock_gc.side_effect = lambda slot: client1 if slot.slot_number == 1 else client2
        provider._client = client1

        with pytest.raises(GeminiConfigError) as exc_info:
            await provider._call_with_retry("test", "test")

        assert "not found" in str(exc_info.value).lower() or "unsupported" in str(exc_info.value).lower()
        # Key 2 should NOT have been called because model error is non-rotatable
        assert client2.models.generate_content.call_count == 0


# ---------------------------------------------------------------------------
# 9. Network Timeout Classified as Rotatable
# ---------------------------------------------------------------------------

def test_network_timeout_classification():
    """Verify TimeoutError and network drops are classified as rotatable network_timeout."""
    timeout_exc = asyncio.TimeoutError("Request timed out after 60s")
    assert classify_gemini_error(timeout_exc) == "network_timeout"
    assert is_rotatable_error(timeout_exc) is True


# ---------------------------------------------------------------------------
# 10. AI Roadmap Persistence & Progress Tracking
# ---------------------------------------------------------------------------

def test_ai_roadmap_progress_update():
    """Verify roadmap step progress update persists and toggles completion."""
    mock_profile_repo = MagicMock()
    mock_career_repo = MagicMock()
    mock_analysis_repo = MagicMock()

    analysis_id = "ai-analysis-uuid-999"
    profile_id = "profile-123"

    mock_analysis_repo.get_latest_analysis.return_value = {
        "id": analysis_id,
        "profile_id": profile_id,
        "is_fallback": False,
        "roadmap_steps": [
            {"step_number": 1, "title": "Learn Core Python", "completed": False},
            {"step_number": 2, "title": "Build First Web App", "completed": False},
        ],
    }
    mock_analysis_repo.get_roadmap_progress.return_value = [1]
    mock_analysis_repo.set_step_progress.return_value = None

    mock_ai = MagicMock(spec=GeminiProvider)
    service = AnalysisService(
        profile_repo=mock_profile_repo,
        career_repo=mock_career_repo,
        analysis_repo=mock_analysis_repo,
        ai_provider=mock_ai,
    )

    res = service.update_roadmap_progress(analysis_id, profile_id, step_number=1, completed=True)
    assert res["analysis_id"] == analysis_id
    assert 1 in res["completed_steps"]
    assert res["percent_complete"] == 50.0
    mock_analysis_repo.set_step_progress.assert_called_once_with(analysis_id, profile_id, 1, True)
