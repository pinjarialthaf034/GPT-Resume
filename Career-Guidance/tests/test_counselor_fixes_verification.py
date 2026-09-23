"""
CareerCompass AI — Verification Tests for Counselor Fixes
Covers all 6 required scenarios:
  TEST 1: Gemini successful response -> is_fallback = false, genuine Gemini response returned
  TEST 2: Gemini 503 -> retry/key rotation occurs, no sub-10s timeout, fallback only if all attempts fail
  TEST 3: Gemini 429 -> classified as quota_rate_limit, rotates keys, no false network_timeout classification
  TEST 4: Gemini 400 INVALID_ARGUMENT containing 'deadline' -> classified as programming_error, non-rotatable
  TEST 5: Remaining budget < 10 seconds -> NO Gemini request sent with timeout < 10.0s (HttpOptions >= 10000ms)
  TEST 6: Valid Gemini response reaches caller and is NOT replaced with offline fallback
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from google.genai.errors import APIError, ClientError

from backend.ai.errors import classify_gemini_error, get_safe_error_summary
from backend.ai.gemini_provider import (
    GeminiProvider,
    MIN_ALLOWED_DEADLINE_SECONDS,
    CHAT_TOTAL_BUDGET_SECONDS,
)
from backend.ai.key_rotator import is_rotatable_error
from backend.config import Settings
from backend.services.chat_service import ChatService


@pytest.fixture
def multi_key_settings():
    return Settings(
        gemini_api_key_1="test-fix-key-1",
        gemini_api_key_2="test-fix-key-2",
        gemini_api_key_3="test-fix-key-3",
        gemini_model="gemini-3.6-flash",
    )


@pytest.fixture
def mock_profile():
    return {
        "id": "student-verified-fix-1",
        "full_name": "Althaf Pinjari",
        "branch": "Computer Engineering",
        "semester": 6,
        "cgpa": 8.8,
        "career_goal": "Cloud Solutions Engineer",
        "selected_career": "Cloud Solutions Engineer",
        "skills": ["Python", "FastAPI", "Docker"],
        "interests": ["Cloud Architecture"],
    }


# ---------------------------------------------------------------------------
# TEST 1: Gemini successful response -> is_fallback = false
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_1_gemini_successful_response(multi_key_settings, mock_profile):
    """Verifies that genuine Gemini responses are returned with is_fallback=False."""
    provider = GeminiProvider(multi_key_settings)

    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Here is genuine, non-fallback Gemini counseling advice for Cloud Solutions Engineer."
    mock_session.send_message.return_value = mock_resp

    from google.genai.chats import Chats
    with patch.object(Chats, "create", return_value=mock_session):
        reply = await provider.chat(
            message="What are key skills for Cloud Solutions?",
            profile=mock_profile,
            career_goal="Cloud Solutions Engineer",
            skill_gaps=[],
            conversation_history=[],
        )
        assert "genuine, non-fallback" in reply
        assert not reply.startswith("{")


# ---------------------------------------------------------------------------
# TEST 2: Gemini 503 -> retry/key rotation, no sub-10s timeout
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_2_gemini_503_retry_and_rotation(multi_key_settings, mock_profile):
    """Verifies 503 retry behavior: respects backoff and never sends sub-10s timeouts."""
    provider = GeminiProvider(multi_key_settings)
    err_503 = APIError(503, {"message": "Model experiencing temporary high demand", "status": "UNAVAILABLE"})

    attempts_timeouts = []

    def fake_create(model, config, history):
        timeout_val = getattr(config.http_options, "timeout", None) if hasattr(config, "http_options") else None
        attempts_timeouts.append(timeout_val)
        sess = MagicMock()
        if len(attempts_timeouts) == 1:
            sess.send_message.side_effect = err_503
        else:
            sess.send_message.return_value = MagicMock(text="Recovered from 503 on retry!")
        return sess

    from google.genai.chats import Chats
    with patch.object(Chats, "create", side_effect=fake_create):
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            reply = await provider.chat(
                message="Tell me about DevOps",
                profile=mock_profile,
                career_goal="Cloud Solutions Engineer",
                skill_gaps=[],
                conversation_history=[],
            )
            assert "Recovered from 503" in reply
            assert len(attempts_timeouts) == 2
            # Verify that every attempt timeout sent in http_options is AT LEAST 10,000 ms (10 seconds)
            for t in attempts_timeouts:
                assert t is not None
                assert t >= 10000, f"Attempt timeout {t} ms is under 10,000 ms minimum allowed deadline!"


# ---------------------------------------------------------------------------
# TEST 3: Gemini 429 -> correct classification, rotates key, not network_timeout
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_3_gemini_429_classification_and_rotation(multi_key_settings, mock_profile):
    """Verifies 429 quota exhaustion is classified as quota_rate_limit and rotates keys."""
    err_429 = APIError(429, {"message": "Resource exhausted", "status": "RESOURCE_EXHAUSTED"})
    category = classify_gemini_error(err_429)
    assert category == "quota_rate_limit"
    assert category != "network_timeout"
    assert is_rotatable_error(err_429) is True

    provider = GeminiProvider(multi_key_settings)
    assert provider._key_manager.total_keys >= 2

    call_slots = []

    def fake_create(model, config, history):
        # Record attempt
        sess = MagicMock()
        if len(call_slots) == 0:
            call_slots.append(1)
            sess.send_message.side_effect = err_429
        else:
            call_slots.append(2)
            sess.send_message.return_value = MagicMock(text="Key 2 responded after key 1 hit 429 quota!")
        return sess

    from google.genai.chats import Chats
    with patch.object(Chats, "create", side_effect=fake_create):
        reply = await provider.chat(
            message="What is Docker?",
            profile=mock_profile,
            career_goal="Cloud Solutions Engineer",
            skill_gaps=[],
            conversation_history=[],
        )
        assert "Key 2 responded" in reply
        # Key 1 was attempted, hit 429, and Key 2 was used
        assert len(call_slots) == 2
        assert provider._key_manager._slots[0].is_cooling_down is True


# ---------------------------------------------------------------------------
# TEST 4: Gemini 400 INVALID_ARGUMENT containing 'deadline' -> programming_error
# ---------------------------------------------------------------------------
def test_4_gemini_400_invalid_argument_with_deadline_classified_properly():
    """
    Verifies that a 400 error containing 'deadline' (e.g. 'Manually set deadline 7s is too short')
    is classified as a programming_error, NOT a network_timeout, and is non-rotatable.
    """
    err_400 = ClientError(
        400,
        {
            "error": {
                "code": 400,
                "message": "Manually set deadline 7s is too short. Minimum allowed deadline is 10s.",
                "status": "INVALID_ARGUMENT",
            }
        },
    )

    category = classify_gemini_error(err_400)
    assert category == "programming_error"
    assert category != "network_timeout"
    # Must NOT be rotatable so it does not burn all other API keys
    assert is_rotatable_error(err_400) is False


# ---------------------------------------------------------------------------
# TEST 5: Remaining budget < 10 seconds -> NO Gemini request sent with timeout < 10s
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_5_remaining_budget_under_10s_never_sends_sub10s_request(multi_key_settings, mock_profile):
    """
    Verifies that when remaining budget drops below 10.0s (MIN_ALLOWED_DEADLINE_SECONDS),
    the code halts rotation rather than sending an invalid sub-10s deadline to Google API.
    """
    provider = GeminiProvider(multi_key_settings)
    loop = asyncio.get_running_loop()
    start_time = loop.time()

    observed_http_timeouts = []

    # Simulate clock: first call starts at t=0, fails after 15s.
    # At t=15s, remaining = 24.0 - 15.0 = 9.0s (< 10.0s).
    # The loop MUST NOT send a second request with timeout=9.0s or 7.0s.
    simulated_times = [
        start_time,          # deadline initialization
        start_time + 1.0,    # candidate slot 1 remaining check (23.0s)
        start_time + 1.1,    # attempt 1 check (22.9s)
        start_time + 15.0,   # after attempt 1 timeout (remaining is 9.0s < 10.0s)
        start_time + 15.1,   # attempt 2 check
        start_time + 25.0,   # subsequent checks
    ]

    def mock_time():
        if simulated_times:
            return simulated_times.pop(0)
        return start_time + 30.0

    def fake_create(model, config, history):
        t_val = getattr(config.http_options, "timeout", None) if hasattr(config, "http_options") else None
        observed_http_timeouts.append(t_val)
        sess = MagicMock()
        sess.send_message.side_effect = TimeoutError("Simulated attempt 1 timeout")
        return sess

    from google.genai.chats import Chats
    with patch.object(Chats, "create", side_effect=fake_create):
        with patch.object(loop, "time", side_effect=mock_time):
            with pytest.raises(RuntimeError):
                await provider.chat(
                    message="Explain VPC Peering",
                    profile=mock_profile,
                    career_goal="Cloud Solutions Engineer",
                    skill_gaps=[],
                    conversation_history=[],
                )

            # Only attempt 1 should have been made; attempt 2 should be stopped because remaining < 10.0s
            assert len(observed_http_timeouts) == 1
            assert observed_http_timeouts[0] >= 10000


# ---------------------------------------------------------------------------
# TEST 6: Gemini returns valid response -> ChatService does NOT replace with fallback
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_6_chat_service_preserves_genuine_gemini_response(mock_profile):
    """Verifies that ChatService returns is_fallback=False when Gemini responds."""
    mock_ai = MagicMock(spec=GeminiProvider)
    mock_ai.model_name = "gemini-3.6-flash"
    mock_ai.chat = AsyncMock(return_value="Detailed genuine AI response for semester 6 student.")

    mock_profile_repo = MagicMock()
    mock_profile_repo.get_by_id.return_value = mock_profile
    mock_profile_repo.get_skills.return_value = ["Python"]
    mock_profile_repo.get_interests.return_value = ["Cloud"]
    mock_profile_repo.get_assessment_answers.return_value = []

    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_latest_analysis.return_value = None
    mock_analysis_repo.get_latest_resume_analysis.return_value = None

    mock_chat_repo = MagicMock()
    mock_chat_repo.get_or_create_session.return_value = {"id": "session-real-1"}
    mock_chat_repo.get_messages.return_value = []
    mock_chat_repo.save_message.side_effect = lambda sess_id, role, content: {"id": "msg-real-1", "content": content}

    service = ChatService(
        profile_repo=mock_profile_repo,
        analysis_repo=mock_analysis_repo,
        chat_repo=mock_chat_repo,
        ai_provider=mock_ai,
    )

    result = await service.send_message(
        profile_id=mock_profile["id"],
        message="What are top cloud certifications?",
        session_id="session-real-1",
    )

    assert result["error"] is False
    assert result["is_fallback"] is False
    assert "Detailed genuine AI response" in result["content"]
    assert "CareerCompass Placement Engine (Offline Fallback)" not in result["content"]
    assert "Academic Advisory Engine" not in result["content"]
