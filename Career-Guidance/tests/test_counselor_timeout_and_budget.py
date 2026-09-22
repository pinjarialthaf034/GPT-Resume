"""
CareerCompass AI — Tests for Dynamic Chat Deadline and Timeout Strategy
Verifies:
1. Normal success within the 21.0s budget
2. Per-attempt timeout triggers retry/rotation
3. Transient 503 error followed by successful retry (mirroring the 17.48s recovery)
4. All keys fail -> clean deterministic fallback via ChatService
5. Deadline prevents additional doomed attempts and respects the 21.0s budget
"""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai.errors import APIError

from backend.ai.gemini_provider import (
    CHAT_PER_ATTEMPT_TIMEOUT_SECONDS,
    CHAT_TOTAL_BUDGET_SECONDS,
    GeminiProvider,
)
from backend.ai.key_rotator import KeyRotationManager
from backend.config import Settings
from backend.services.chat_service import ChatService


@pytest.fixture
def mock_settings_multi_key():
    return Settings(
        gemini_api_key="primary-key-12345",
        gemini_api_key_2="secondary-key-67890",
        gemini_api_key_3="tertiary-key-11223",
        gemini_model="gemini-2.5-flash",
    )


@pytest.fixture
def sample_profile():
    return {
        "id": "prof-timeout-001",
        "full_name": "Rohan Sharma",
        "branch": "Computer Science",
        "current_year": 3,
        "cgpa": 8.5,
        "career_goal": "Cloud Architect",
    }


# ---------------------------------------------------------------------------
# 1. Normal success within budget
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_normal_success_within_budget(mock_settings_multi_key, sample_profile):
    """Verifies that Gemini chat responds normally within budget without fallback."""
    provider = GeminiProvider(mock_settings_multi_key)

    mock_sess = MagicMock()
    mock_sess.send_message.return_value = MagicMock(text="Here is your cloud architecture roadmap.")

    from google.genai.chats import Chats
    with patch.object(Chats, "create", return_value=mock_sess):
        reply = await provider.chat(
            message="How do I become a Cloud Architect?",
            profile=sample_profile,
            career_goal="Cloud Architect",
            skill_gaps=["AWS", "Docker"],
            conversation_history=[],
        )
        assert "cloud architecture" in reply.lower()
        mock_sess.send_message.assert_called_once()


# ---------------------------------------------------------------------------
# 2. Per-attempt timeout followed by retry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_per_attempt_timeout_followed_by_retry(mock_settings_multi_key, sample_profile):
    """
    Verifies that when attempt 1 stalls and times out,
    the provider catches the timeout and succeeds on attempt 2.
    """
    provider = GeminiProvider(mock_settings_multi_key)

    attempt_count = 0

    def fake_create(model, config, history):
        nonlocal attempt_count
        attempt_count += 1
        sess = MagicMock()
        if attempt_count == 1:
            # Simulate a timeout on attempt 1
            sess.send_message.side_effect = TimeoutError("Request timed out")
        else:
            sess.send_message.return_value = MagicMock(text="Recovered on attempt 2 after timeout!")
        return sess

    from google.genai.chats import Chats
    with patch.object(Chats, "create", side_effect=fake_create):
        reply = await provider.chat(
            message="Explain Docker containers",
            profile=sample_profile,
            career_goal="Cloud Architect",
            skill_gaps=[],
            conversation_history=[],
        )
        assert "Recovered on attempt 2" in reply
        assert attempt_count == 2


# ---------------------------------------------------------------------------
# 3. 503 followed by successful retry (mirroring 17.48s recovery)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_503_followed_by_successful_retry(mock_settings_multi_key, sample_profile):
    """
    Simulates:
    Attempt 1: 503 UNAVAILABLE (high demand)
    Backoff: 2s (mocked to run quickly)
    Attempt 2: 200 OK success
    Verifies recovery under the dynamic budget.
    """
    provider = GeminiProvider(mock_settings_multi_key)
    err_503 = APIError(503, {"message": "Model experiencing high demand", "status": "UNAVAILABLE"})

    attempt_count = 0

    def fake_create(model, config, history):
        nonlocal attempt_count
        attempt_count += 1
        sess = MagicMock()
        if attempt_count == 1:
            sess.send_message.side_effect = err_503
        else:
            sess.send_message.return_value = MagicMock(text="Personalized AI guidance after 503 recovery.")
        return sess

    from google.genai.chats import Chats
    with patch.object(Chats, "create", side_effect=fake_create):
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            reply = await provider.chat(
                message="Tell me about DevOps pipelines",
                profile=sample_profile,
                career_goal="Cloud Architect",
                skill_gaps=[],
                conversation_history=[],
            )
            assert "Personalized AI guidance" in reply
            assert attempt_count == 2
            mock_sleep.assert_awaited_once_with(2.0)


# ---------------------------------------------------------------------------
# 4. All keys fail -> deterministic fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_all_keys_fail_returns_deterministic_fallback(sample_profile):
    """
    Verifies that when all configured keys fail or exhaust budget,
    ChatService catches the error and cleanly returns the structured deterministic fallback.
    """
    mock_ai = MagicMock(spec=GeminiProvider)
    mock_ai.chat = AsyncMock(side_effect=RuntimeError("AI chat temporarily unavailable across keys"))

    mock_profile_repo = MagicMock()
    mock_profile_repo.get_by_id.return_value = sample_profile
    mock_profile_repo.get_skills.return_value = ["Linux", "Python"]
    mock_profile_repo.get_interests.return_value = ["Cloud Computing"]
    mock_profile_repo.get_assessment_answers.return_value = []

    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_latest_analysis.return_value = {
        "selected_career": "Cloud Architect",
        "skill_gaps": [{"skill_name": "Kubernetes"}],
    }
    mock_analysis_repo.get_latest_resume_analysis.return_value = None

    mock_chat_repo = MagicMock()
    mock_chat_repo.get_or_create_session.return_value = {"id": "session-budget-1"}
    mock_chat_repo.get_messages.return_value = []
    mock_chat_repo.save_message.side_effect = lambda sess_id, role, content: {"id": "m1", "content": content}

    service = ChatService(
        profile_repo=mock_profile_repo,
        analysis_repo=mock_analysis_repo,
        chat_repo=mock_chat_repo,
        ai_provider=mock_ai,
    )

    result = await service.send_message(
        profile_id=sample_profile["id"],
        message="What certifications should I take for Cloud Architecture?",
        session_id="session-budget-1",
    )

    assert result["error"] is False
    assert result["is_fallback"] is True
    assert "CareerCompass Academic Advisory Engine" in result["content"]
    assert "Cloud Architect" in result["content"]


# ---------------------------------------------------------------------------
# 5. Deadline prevents additional doomed attempts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_deadline_prevents_additional_doomed_attempts(mock_settings_multi_key, sample_profile):
    """
    Verifies that when the monotonic loop deadline expires (remaining <= 0),
    the loop halts immediately, avoiding any further attempts or key rotations,
    and raises RuntimeError so the caller can return the fallback.
    """
    provider = GeminiProvider(mock_settings_multi_key)
    err_503 = APIError(503, {"message": "Service unavailable", "status": "UNAVAILABLE"})

    attempt_count = 0
    loop = asyncio.get_running_loop()
    original_time = loop.time()

    def fake_create(model, config, history):
        nonlocal attempt_count
        attempt_count += 1
        # Advance mock loop time past CHAT_TOTAL_BUDGET_SECONDS (21s) on attempt 1
        with patch.object(loop, "time", return_value=original_time + CHAT_TOTAL_BUDGET_SECONDS + 5.0):
            pass
        sess = MagicMock()
        sess.send_message.side_effect = err_503
        return sess

    # Patch loop.time to simulate clock advancing past the 21s deadline after first failure
    simulated_clock = [original_time, original_time + 1.0, original_time + CHAT_TOTAL_BUDGET_SECONDS + 2.0]

    def mock_time():
        if simulated_clock:
            return simulated_clock.pop(0)
        return original_time + CHAT_TOTAL_BUDGET_SECONDS + 10.0

    from google.genai.chats import Chats
    with patch.object(Chats, "create", side_effect=fake_create):
        with patch.object(loop, "time", side_effect=mock_time):
            with pytest.raises(RuntimeError) as exc_info:
                await provider.chat(
                    message="Help me with Kubernetes",
                    profile=sample_profile,
                    career_goal="Cloud Architect",
                    skill_gaps=[],
                    conversation_history=[],
                )
            assert "AI chat temporarily unavailable across keys" in str(exc_info.value)
            # The deadline must prevent executing all 9 potential attempts across 3 keys
            assert attempt_count < 3
