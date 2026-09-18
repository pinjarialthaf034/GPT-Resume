"""
Unit tests for AI Pydantic schemas and JSON parsing.
Verifies strict validation, schema bounds, and extraction from markdown code fences.
"""
import pytest
from pydantic import ValidationError

from backend.ai.gemini_provider import _extract_json, _validate_response
from backend.ai.schemas import CareerAnalysisAIResponse, ResumeAnalysisAIResponse


def test_extract_json_from_code_fences():
    raw_fence = "```json\n{\"test\": 123}\n```"
    assert _extract_json(raw_fence) == "{\"test\": 123}"

    raw_fence_no_tag = "```\n{\"test\": 456}\n```"
    assert _extract_json(raw_fence_no_tag) == "{\"test\": 456}"

    raw_text = "Some intro text {\"test\": 789} outro text"
    assert _extract_json(raw_text) == "{\"test\": 789}"


def test_valid_career_analysis_response():
    valid_data = {
        "summary": "This is a detailed and comprehensive career analysis summary for diploma engineering students with over fifty characters.",
        "recommended_careers": [
            {
                "career_id": "car-1",
                "title": "Software Developer",
                "score": 85.5,
                "reason": "Strong alignment with programming skills.",
                "matched_skills": ["Python", "SQL"],
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
                "learning_resource": "Docker for Beginners",
            }
        ],
        "priority_skills": ["Docker", "Git"],
        "roadmap_steps": [
            {
                "step_number": 1,
                "title": "Master Docker Basics",
                "description": "Learn containerization fundamentals.",
                "duration_weeks": 4,
                "skills_gained": ["Docker"],
                "resources": ["Official Documentation"],
            }
        ],
        "project_recommendations": [
            {
                "title": "Containerized Flask App",
                "description": "Deploy app inside Docker container.",
                "skills_practiced": ["Docker", "Python"],
                "difficulty": "intermediate",
                "estimated_hours": 15,
            }
        ],
        "next_steps": ["Install Docker Desktop", "Complete container tutorial"],
    }

    model = CareerAnalysisAIResponse.model_validate(valid_data)
    assert model.summary.startswith("This is a detailed")
    assert len(model.recommended_careers) == 1
    assert model.recommended_careers[0].score == 85.5


def test_career_analysis_invalid_score_boundary():
    data = {
        "summary": "This is a detailed and comprehensive career analysis summary for diploma engineering students with over fifty characters.",
        "recommended_careers": [
            {
                "career_id": "car-1",
                "title": "Software Developer",
                "score": 150.0,  # Invalid: > 100
                "reason": "Test",
            }
        ],
        "strengths": ["Strengths"],
        "priority_skills": ["Python"],
        "roadmap_steps": [
            {
                "step_number": 1,
                "title": "Step 1",
                "description": "Desc",
            }
        ],
        "next_steps": ["Step 1"],
    }
    with pytest.raises(ValidationError):
        CareerAnalysisAIResponse.model_validate(data)


def test_resume_analysis_validation():
    valid_resume_data = {
        "guidance_score": 78,
        "strengths": ["Clear project descriptions", "Relevant coursework"],
        "missing_skills": ["Git version control"],
        "formatting_feedback": ["Use consistent bullet points"],
        "project_suggestions": ["Build a deployed web portfolio"],
        "skill_alignment": "Good foundational programming skills, lacks modern deployment tools.",
        "improvement_suggestions": ["Add GitHub profile link"],
    }

    model = ResumeAnalysisAIResponse.model_validate(valid_resume_data)
    assert model.guidance_score == 78
    assert len(model.strengths) == 2


def test_validate_response_helper():
    raw_json = """
    ```json
    {
        "guidance_score": 82,
        "strengths": ["Good academic record"],
        "missing_skills": ["Docker"],
        "formatting_feedback": ["Good fonts"],
        "project_suggestions": ["Add capstone"],
        "skill_alignment": "Strong alignment with junior developer role expectations.",
        "improvement_suggestions": ["Highlight internships"]
    }
    ```
    """
    res = _validate_response(raw_json, ResumeAnalysisAIResponse)
    assert res.guidance_score == 82
