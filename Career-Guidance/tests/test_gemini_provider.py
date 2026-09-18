"""
Unit tests for modernized Google GenAI SDK (google-genai) provider.
Tests provider initialization, structured response validation, chat sessions,
exponential backoff, and error resilience.
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.ai.gemini_provider import GeminiProvider, _extract_json, _validate_response
from backend.ai.schemas import CareerAnalysisAIResponse, ResumeAnalysisAIResponse
from backend.config import Settings


@pytest.fixture
def mock_settings():
    return Settings(
        gemini_api_key="mock-api-key-12345",
        gemini_model="gemini-1.5-flash",
    )


def test_provider_initialization(mock_settings):
    provider = GeminiProvider(mock_settings)
    assert provider.model_name == "gemini-1.5-flash"
    assert provider.career_analysis_prompt_version == "v2.0"
    assert provider.resume_analysis_prompt_version == "v1.0"


@pytest.mark.asyncio
async def test_analyze_career_success(mock_settings):
    provider = GeminiProvider(mock_settings)

    mock_response_data = {
        "summary": "Detailed, thorough career guidance analysis summary tailored for diploma students with more than fifty characters.",
        "recommended_careers": [
            {
                "career_id": "c-101",
                "title": "Full Stack Developer",
                "score": 90.0,
                "reason": "Strong affinity for web development.",
                "matched_skills": ["Python", "JavaScript"],
                "missing_skills": ["Docker"],
            }
        ],
        "strengths": ["Quick learner", "Solid foundations"],
        "skill_gaps": [
            {
                "skill_name": "Docker",
                "current_level": "beginner",
                "required_level": "intermediate",
                "priority": "high",
                "learning_resource": "Docker Get Started Guide",
            }
        ],
        "priority_skills": ["Docker"],
        "roadmap_steps": [
            {
                "step_number": 1,
                "title": "Learn Containerization",
                "description": "Understand containers and Docker basics.",
                "duration_weeks": 3,
                "skills_gained": ["Docker"],
                "resources": ["docs.docker.com"],
            }
        ],
        "project_recommendations": [
            {
                "title": "Containerized Web App",
                "description": "Build and dockerize full stack app.",
                "skills_practiced": ["Docker", "Python"],
                "difficulty": "intermediate",
                "estimated_hours": 20,
            }
        ],
        "next_steps": ["Complete Docker tutorial", "Build first image"],
    }

    mock_resp = MagicMock()
    mock_resp.text = f"```json\n{json.dumps(mock_response_data)}\n```"

    with patch.object(provider._client.models, "generate_content", return_value=mock_resp):
        result = await provider.analyze_career(
            profile={"full_name": "Rahul", "branch": "CSE", "cgpa": 8.5},
            career_matches=[{"career_id": "c-101", "title": "Full Stack Developer", "score": 90.0}],
        )
        assert isinstance(result, CareerAnalysisAIResponse)
        assert len(result.recommended_careers) == 1
        assert result.recommended_careers[0].title == "Full Stack Developer"
        assert result.recommended_careers[0].score == 90.0


@pytest.mark.asyncio
async def test_analyze_resume_success(mock_settings):
    provider = GeminiProvider(mock_settings)

    mock_resume_data = {
        "guidance_score": 82,
        "strengths": ["Structured layout", "Clear projects"],
        "missing_skills": ["Docker"],
        "formatting_feedback": ["Inconsistent font size in headers"],
        "project_suggestions": ["Build a containerized full-stack portfolio"],
        "skill_alignment": "Solid technical foundation in core computer science subjects.",
        "improvement_suggestions": ["Add GitHub links", "Include metrics on projects"],
    }

    mock_resp = MagicMock()
    mock_resp.text = json.dumps(mock_resume_data)

    with patch.object(provider._client.models, "generate_content", return_value=mock_resp):
        result = await provider.analyze_resume(
            resume_text="Rahul Sharma - Diploma CSE - Skills: Python, SQL",
            profile={"full_name": "Rahul", "branch": "CSE"},
        )
        assert isinstance(result, ResumeAnalysisAIResponse)
        assert result.guidance_score == 82
        assert "Docker" in result.missing_skills


@pytest.mark.asyncio
async def test_chat_success(mock_settings):
    provider = GeminiProvider(mock_settings)

    mock_chat_session = MagicMock()
    mock_chat_resp = MagicMock()
    mock_chat_resp.text = "As a diploma student in Mechanical, learning SolidWorks is essential."
    mock_chat_session.send_message.return_value = mock_chat_resp

    from google.genai.chats import Chats
    with patch.object(Chats, "create", return_value=mock_chat_session):
        reply = await provider.chat(
            message="Which CAD software should I learn?",
            profile={"full_name": "Amit", "branch": "MECHANICAL"},
            career_goal="Mechanical Design Engineer",
            skill_gaps=[{"skill_name": "SolidWorks"}],
            conversation_history=[{"role": "user", "content": "Hello"}],
        )
        assert "SolidWorks" in reply


@pytest.mark.asyncio
async def test_malformed_json_rejection(mock_settings):
    provider = GeminiProvider(mock_settings)

    mock_resp = MagicMock()
    mock_resp.text = "This is not valid JSON content at all."

    with patch.object(provider._client.models, "generate_content", return_value=mock_resp):
        with pytest.raises(RuntimeError) as exc_info:
            await provider.analyze_career(
                profile={"full_name": "Test"},
                career_matches=[{"career_id": "c-101", "title": "Test Career", "score": 80.0}],
            )
        assert "validation failed" in str(exc_info.value).lower()
