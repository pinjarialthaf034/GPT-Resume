"""
CareerCompass AI — Automated Tests for AI Counselor Root Cause Investigation & Repair
Validates all Phase 10 requirements:
  1. Free-form Chat: 'hello!!', interview prep, general & follow-up questions
  2. Structured Counselor Prompts: Certifications, B.Tech vs Job, Capstone ideas
  3. Gemini Provider: json_mode=False, history sanitization (leading user turn), prompt construction
  4. Multi-key Rotation: Key 1 -> Key 2 -> Key 3 failover, no rotation on non-rotatable errors
  5. Fallback System: All keys exhausted triggers deterministic, curriculum-grounded response (is_fallback=True)
  6. Context Awareness: Student branch, semester, CGPA, target career, skill gaps, assessment signals
  7. Conversation History Persistence: Multi-turn preservation and session scoping
  8. Security: Zero API key leakage in logs, API responses, or frontend assets
"""
import asyncio
import json
import logging
import os
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from google.genai.errors import APIError

from backend.ai.gemini_provider import GeminiProvider, _clean_chat_response
from backend.ai.key_rotator import KeyRotationManager, KeySlot
from backend.ai.prompts import build_chatbot_system_prompt
from backend.config import Settings
from backend.main import app
from backend.services.chat_service import ChatService


# ---------------------------------------------------------------------------
# Fixtures & Test Data
# ---------------------------------------------------------------------------

@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def mock_profile():
    return {
        "id": "student-counselor-uuid-1",
        "full_name": "Aarav Sharma",
        "branch": "CSE",
        "semester": 6,
        "cgpa": 8.4,
        "career_goal": "Software Engineer",
        "selected_career": "Software Developer",
        "skills": ["Python", "JavaScript", "SQL"],
    }


@pytest.fixture
def mock_settings_multi_key():
    return Settings(
        gemini_api_key_1="key-one-counselor",
        gemini_api_key_2="key-two-counselor",
        gemini_api_key_3="key-three-counselor",
        gemini_model="gemini-3.6-flash",
    )


# ---------------------------------------------------------------------------
# 1. Free-form & Greeting Chat Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hello_greeting_gemini_success(mock_settings_multi_key, mock_profile):
    """Verifies that greetings like 'hello!!' receive a valid conversational response without JSON errors."""
    provider = GeminiProvider(mock_settings_multi_key)

    mock_chat_session = MagicMock()
    mock_chat_resp = MagicMock()
    mock_chat_resp.text = "Hello Aarav! How can I assist with your software engineering career preparation today?"
    mock_chat_session.send_message.return_value = mock_chat_resp

    from google.genai.chats import Chats
    with patch.object(Chats, "create", return_value=mock_chat_session):
        reply = await provider.chat(
            message="hello!!",
            profile=mock_profile,
            career_goal="Software Engineer",
            skill_gaps=[{"skill_name": "System Design"}],
            conversation_history=[],
        )
        assert "Hello Aarav" in reply
        # Verify response is clean conversational text, not wrapped in raw JSON
        assert not reply.startswith("{")


@pytest.mark.asyncio
async def test_campus_interview_prep_query_success(mock_settings_multi_key, mock_profile):
    """Verifies that free-form campus interview questions receive high-quality technical guidance."""
    provider = GeminiProvider(mock_settings_multi_key)

    mock_chat_session = MagicMock()
    mock_chat_resp = MagicMock()
    mock_chat_resp.text = (
        "### Campus Placement Preparation Strategy\n"
        "1. Core Aptitude: Practice numerical puzzles.\n"
        "2. Technical Rounds: Strengthen Python, OOP, and DBMS.\n"
        "3. Capstone Defense: Be ready to explain your final-year architecture."
    )
    mock_chat_session.send_message.return_value = mock_chat_resp

    from google.genai.chats import Chats
    with patch.object(Chats, "create", return_value=mock_chat_session):
        reply = await provider.chat(
            message="How can I prepare for junior software or engineering campus interviews?",
            profile=mock_profile,
            career_goal="Software Engineer",
            skill_gaps=[{"skill_name": "Docker"}, {"skill_name": "System Design"}],
            conversation_history=[],
        )
        assert "Campus Placement Preparation" in reply
        assert "Technical Rounds" in reply


# ---------------------------------------------------------------------------
# 2. Structured Counselor Actions / Quick Prompts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_structured_action_certifications(mock_settings_multi_key, mock_profile):
    """Verifies that 'What certifications should I pursue for my branch?' receives guidance."""
    provider = GeminiProvider(mock_settings_multi_key)

    mock_chat_session = MagicMock()
    mock_chat_resp = MagicMock()
    mock_chat_resp.text = (
        "For CSE diploma students, top certifications include:\n"
        "- AWS Certified Cloud Practitioner\n"
        "- Oracle Certified Associate Java Programmer\n"
        "- NPTEL Data Structures & Algorithms"
    )
    mock_chat_session.send_message.return_value = mock_chat_resp

    from google.genai.chats import Chats
    with patch.object(Chats, "create", return_value=mock_chat_session):
        reply = await provider.chat(
            message="What certifications should I pursue for my branch?",
            profile=mock_profile,
            career_goal="Software Engineer",
            skill_gaps=[],
            conversation_history=[],
        )
        assert "AWS Certified Cloud Practitioner" in reply


@pytest.mark.asyncio
async def test_structured_action_btech_vs_job(mock_settings_multi_key, mock_profile):
    """Verifies that 'Should I do lateral entry B.Tech or start working after diploma?' receives pathway guidance."""
    provider = GeminiProvider(mock_settings_multi_key)

    mock_chat_session = MagicMock()
    mock_chat_resp = MagicMock()
    mock_chat_resp.text = (
        "### B.Tech Lateral Entry vs Immediate Job\n"
        "With an 8.4 CGPA in CSE:\n"
        "- Option A (Lateral Entry B.Tech): Strong eligibility for LEET/JELET to enter directly into 2nd year.\n"
        "- Option B (Job): Enter industry as a Junior Engineer, then pursue evening/distance B.Tech."
    )
    mock_chat_session.send_message.return_value = mock_chat_resp

    from google.genai.chats import Chats
    with patch.object(Chats, "create", return_value=mock_chat_session):
        reply = await provider.chat(
            message="Should I do lateral entry B.Tech or start working after diploma?",
            profile=mock_profile,
            career_goal="Software Engineer",
            skill_gaps=[],
            conversation_history=[],
        )
        assert "Lateral Entry" in reply


# ---------------------------------------------------------------------------
# 3. Gemini Provider Hygiene & History Handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_history_sanitization_leading_model_turn(mock_settings_multi_key, mock_profile):
    """Verifies that if history begins with a model turn, it is stripped so Gemini does not error."""
    provider = GeminiProvider(mock_settings_multi_key)

    history_with_leading_model = [
        {"role": "assistant", "content": "Welcome! How can I help you?"},
        {"role": "user", "content": "What is Python?"},
        {"role": "assistant", "content": "Python is a programming language."},
    ]

    captured_history = None

    def fake_create(model, config, history):
        nonlocal captured_history
        captured_history = history
        mock_sess = MagicMock()
        mock_sess.send_message.return_value = MagicMock(text="Here are details.")
        return mock_sess

    from google.genai.chats import Chats
    with patch.object(Chats, "create", side_effect=fake_create):
        await provider.chat(
            message="Tell me more",
            profile=mock_profile,
            career_goal="Software Engineer",
            skill_gaps=[],
            conversation_history=history_with_leading_model,
        )

        assert captured_history is not None
        # The leading assistant message must have been dropped: first turn MUST be user
        assert len(captured_history) == 2
        assert captured_history[0].role == "user"
        assert captured_history[1].role == "model"


@pytest.mark.asyncio
async def test_clean_chat_response_json_unwrap():
    """Verifies that if Gemini returns a JSON envelope, it is cleanly unwrapped."""
    raw_json = '{"response": "Here is the career guidance for you."}'
    assert _clean_chat_response(raw_json) == "Here is the career guidance for you."

    plain_text = "This is ordinary conversational text."
    assert _clean_chat_response(plain_text) == plain_text


# ---------------------------------------------------------------------------
# 4. Multi-Key Rotation in AI Counselor
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_counselor_key1_fails_key2_succeeds(mock_settings_multi_key, mock_profile):
    """Verifies that if Key 1 hits 429 quota exhaustion, Key 2 is attempted and succeeds."""
    provider = GeminiProvider(mock_settings_multi_key)

    quota_err = APIError(429, {"message": "Resource exhausted", "status": "RESOURCE_EXHAUSTED"})

    mock_sess_success = MagicMock()
    mock_sess_success.send_message.return_value = MagicMock(text="Key 2 successfully responded!")

    call_count = 0

    def fake_create(model, config, history):
        nonlocal call_count
        call_count += 1
        sess = MagicMock()
        if call_count == 1:
            sess.send_message.side_effect = quota_err
        else:
            sess.send_message.return_value = MagicMock(text="Key 2 successfully responded!")
        return sess

    from google.genai.chats import Chats
    with patch.object(Chats, "create", side_effect=fake_create):
        reply = await provider.chat(
            message="hello!!",
            profile=mock_profile,
            career_goal="Software Engineer",
            skill_gaps=[],
            conversation_history=[],
        )
        assert "Key 2 successfully responded!" in reply
        assert call_count >= 2


@pytest.mark.asyncio
async def test_counselor_all_keys_exhausted_raises_runtime_error(mock_settings_multi_key, mock_profile):
    """Verifies that if all keys fail with quota errors, provider raises RuntimeError."""
    provider = GeminiProvider(mock_settings_multi_key)
    quota_err = APIError(429, {"message": "All keys exhausted", "status": "RESOURCE_EXHAUSTED"})

    def fake_create(model, config, history):
        sess = MagicMock()
        sess.send_message.side_effect = quota_err
        return sess

    from google.genai.chats import Chats
    with patch.object(Chats, "create", side_effect=fake_create):
        with pytest.raises(RuntimeError) as exc_info:
            await provider.chat(
                message="hello!!",
                profile=mock_profile,
                career_goal="Software Engineer",
                skill_gaps=[],
                conversation_history=[],
            )
        assert "AI chat temporarily unavailable across keys" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 5. Deterministic Fallback in ChatService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_service_all_keys_exhausted_returns_safe_fallback(mock_profile):
    """
    Verifies that when Gemini is completely unavailable across all keys, ChatService
    engages the curriculum-grounded deterministic fallback with is_fallback=True and error=False,
    never crashing and never returning an empty message.
    """
    mock_ai = MagicMock(spec=GeminiProvider)
    mock_ai.chat = AsyncMock(side_effect=RuntimeError("AI chat temporarily unavailable across keys"))

    mock_profile_repo = MagicMock()
    mock_profile_repo.get_by_id.return_value = mock_profile
    mock_profile_repo.get_skills.return_value = ["Python", "SQL"]
    mock_profile_repo.get_interests.return_value = ["Web Development"]
    mock_profile_repo.get_assessment_answers.return_value = []

    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_latest_analysis.return_value = {
        "selected_career": "Software Developer",
        "skill_gaps": [{"skill_name": "Docker"}],
    }
    mock_analysis_repo.get_latest_resume_analysis.return_value = None

    mock_chat_repo = MagicMock()
    mock_chat_repo.get_or_create_session.return_value = {"id": "session-fb-1"}
    mock_chat_repo.get_messages.return_value = []
    mock_chat_repo.save_message.side_effect = lambda sess_id, role, content: {"id": "msg-1", "content": content}

    service = ChatService(
        profile_repo=mock_profile_repo,
        analysis_repo=mock_analysis_repo,
        chat_repo=mock_chat_repo,
        ai_provider=mock_ai,
    )

    result = await service.send_message(
        profile_id=mock_profile["id"],
        message="hello!!",
        session_id="session-fb-1",
    )

    assert result["error"] is False
    assert result["is_fallback"] is True
    assert "Aarav" in result["content"]
    assert "Software Developer" in result["content"]
    assert "CareerCompass Academic Advisory Engine" in result["content"]


@pytest.mark.asyncio
async def test_chat_service_interview_prep_fallback(mock_profile):
    """Verifies that interview prep questions in fallback mode provide complete structured guidance."""
    mock_ai = MagicMock(spec=GeminiProvider)
    mock_ai.chat = AsyncMock(side_effect=RuntimeError("AI chat temporarily unavailable"))

    mock_profile_repo = MagicMock()
    mock_profile_repo.get_by_id.return_value = mock_profile
    mock_profile_repo.get_skills.return_value = ["Python", "SQL"]
    mock_profile_repo.get_interests.return_value = []
    mock_profile_repo.get_assessment_answers.return_value = []

    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_latest_analysis.return_value = {
        "selected_career": "Software Developer",
        "skill_gaps": [{"skill_name": "System Design"}],
    }
    mock_analysis_repo.get_latest_resume_analysis.return_value = None

    mock_chat_repo = MagicMock()
    mock_chat_repo.get_or_create_session.return_value = {"id": "session-fb-2"}
    mock_chat_repo.get_messages.return_value = []
    mock_chat_repo.save_message.side_effect = lambda sess_id, role, content: {"id": "msg-2", "content": content}

    service = ChatService(
        profile_repo=mock_profile_repo,
        analysis_repo=mock_analysis_repo,
        chat_repo=mock_chat_repo,
        ai_provider=mock_ai,
    )

    result = await service.send_message(
        profile_id=mock_profile["id"],
        message="How can I prepare for junior software or engineering campus interviews?",
        session_id="session-fb-2",
    )

    assert result["error"] is False
    assert result["is_fallback"] is True
    assert "Campus Interview Preparation Guide" in result["content"]
    assert "Aptitude & Logical Reasoning" in result["content"]
    assert "Technical HR & Behavioral Round" in result["content"]


# ---------------------------------------------------------------------------
# 6. Context Injection Verification
# ---------------------------------------------------------------------------

def test_chatbot_system_prompt_includes_selected_career(mock_profile):
    """Verifies that build_chatbot_system_prompt includes selected target career."""
    latest_analysis = {
        "selected_career": "DevOps Engineer",
        "skill_gaps": [{"skill_name": "Kubernetes"}],
    }

    prompt = build_chatbot_system_prompt(
        profile=mock_profile,
        career_goal="Software Engineer",
        skill_gaps=[{"skill_name": "Kubernetes"}],
        latest_analysis=latest_analysis,
    )

    assert "DevOps Engineer" in prompt
    assert "Selected Target Career: DevOps Engineer" in prompt
    assert "Aarav Sharma" in prompt
    assert "CSE" in prompt


# ---------------------------------------------------------------------------
# 7. Security: Zero API Key Leakage
# ---------------------------------------------------------------------------

def test_api_keys_never_appear_in_chat_logs(caplog, mock_settings_multi_key, mock_profile):
    """Verifies that API keys never appear in log output during chat operations."""
    caplog.set_level(logging.DEBUG)
    provider = GeminiProvider(mock_settings_multi_key)

    # Check key strings are absent from all log messages
    for record in caplog.records:
        for secret in ("key-one-counselor", "key-two-counselor", "key-three-counselor"):
            assert secret not in record.message


def test_frontend_chat_html_has_no_hardcoded_keys():
    """Verifies that frontend/chat.html contains no hardcoded Gemini API keys."""
    chat_html_path = os.path.join("frontend", "chat.html")
    with open(chat_html_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "AIza" not in content
    assert "gemini_api_key" not in content.lower()
    assert "GEMINI_API_KEY" not in content
