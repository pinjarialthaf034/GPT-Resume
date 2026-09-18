"""
CareerCompass AI — Automated Tests for Genuine AI Career Intelligence
Covers:
  - Multi-signal Student AI Context Builder (profile, skills, interests, assessment, resume)
  - Deterministic SHA-256 Fingerprint & Cache Invalidation
  - Dynamic Career Discovery (non-restricted to seed SQL)
  - 5-Dimension Compatibility Scores & Strict Pydantic Validation
  - Personalization (Profile A vs Profile B produce distinct prompts and results)
  - Context-Aware Chatbot with Assessment & Career Analysis Injection
  - Transparent Non-AI Rule-Engine Fallback (no fake AI)
"""
import copy
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.ai.gemini_provider import GeminiProvider
from backend.ai.prompts import (
    CAREER_ANALYSIS_PROMPT_VERSION,
    build_career_analysis_prompt,
    build_chatbot_system_prompt,
)
from backend.ai.schemas import CareerAnalysisAIResponse, RecommendedCareer
from backend.services.ai_context_builder import (
    build_student_ai_context,
    compute_student_context_fingerprint,
)
from backend.services.analysis_service import AnalysisService
from backend.services.chat_service import ChatService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_profile_a():
    """Profile A: Software / Backend focused student"""
    return {
        "id": "prof-001",
        "user_id": "user-001",
        "full_name": "Aarav Sharma",
        "branch": "Computer Engineering",
        "semester": 5,
        "cgpa": 8.8,
        "career_goal": "Backend Software Developer",
        "profile_version": 1,
    }

@pytest.fixture
def sample_skills_a():
    return [
        {"skills": {"name": "Java", "category": "Backend"}, "proficiency": "advanced"},
        {"skills": {"name": "SQL", "category": "Databases"}, "proficiency": "intermediate"},
        {"skills": {"name": "Data Structures", "category": "Computer Science"}, "proficiency": "intermediate"},
    ]

@pytest.fixture
def sample_interests_a():
    return ["Software Development", "Database Architecture", "Problem Solving"]

@pytest.fixture
def sample_assessment_a():
    return [
        {
            "question_id": "q1",
            "question_text": "What type of technical problems excite you most?",
            "category": "Logic & Software Systems",
            "selected_option": "Writing backend algorithms and optimizing database queries",
            "career_weight": 0.9,
        },
        {
            "question_id": "q3",
            "question_text": "Which work environment do you prefer?",
            "category": "Work Environment",
            "selected_option": "Software tech office or remote development",
            "career_weight": 0.8,
        },
    ]

@pytest.fixture
def sample_resume_a():
    return {
        "id": "res-001",
        "guidance_score": 85,
        "strengths": ["Built Java Spring Boot REST API", "Strong SQL schemas"],
        "missing_skills": ["Docker", "Kubernetes"],
        "skill_alignment": "Well-aligned with junior backend software engineering roles.",
        "project_suggestions": ["Deploy a containerized microservice portfolio project"],
    }


@pytest.fixture
def sample_profile_b():
    """Profile B: Networking / Cybersecurity focused student"""
    return {
        "id": "prof-002",
        "user_id": "user-002",
        "full_name": "Priya Nair",
        "branch": "Computer Engineering",
        "semester": 5,
        "cgpa": 8.4,
        "career_goal": "Cybersecurity & Network Defense",
        "profile_version": 1,
    }

@pytest.fixture
def sample_skills_b():
    return [
        {"skills": {"name": "TCP/IP Networking", "category": "Networking"}, "proficiency": "advanced"},
        {"skills": {"name": "Linux Admin", "category": "Systems"}, "proficiency": "intermediate"},
        {"skills": {"name": "Wireshark", "category": "Security"}, "proficiency": "intermediate"},
    ]

@pytest.fixture
def sample_interests_b():
    return ["Network Security", "Ethical Hacking", "Cloud Infrastructure"]

@pytest.fixture
def sample_assessment_b():
    return [
        {
            "question_id": "q1",
            "question_text": "What type of technical problems excite you most?",
            "category": "Computer Networks & Cybersecurity",
            "selected_option": "Analyzing packet captures, securing network perimeters and defending systems",
            "career_weight": 0.95,
        },
        {
            "question_id": "q3",
            "question_text": "Which work environment do you prefer?",
            "category": "Work Environment",
            "selected_option": "Security operations center (SOC) or network operations room",
            "career_weight": 0.85,
        },
    ]


# ---------------------------------------------------------------------------
# Test AI Context Builder
# ---------------------------------------------------------------------------

def test_build_student_ai_context(sample_profile_a, sample_skills_a, sample_interests_a, sample_assessment_a, sample_resume_a):
    mock_profile_repo = MagicMock()
    mock_profile_repo.get_by_id.return_value = sample_profile_a
    mock_profile_repo.get_skills.return_value = sample_skills_a
    mock_profile_repo.get_interests.return_value = sample_interests_a
    mock_profile_repo.get_assessment_answers.return_value = sample_assessment_a

    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_latest_resume_analysis.return_value = sample_resume_a

    context = build_student_ai_context(mock_profile_repo, mock_analysis_repo, "prof-001")

    assert context["full_name"] == "Aarav Sharma"
    assert context["branch"] == "Computer Engineering"
    assert len(context["skills"]) == 3
    assert context["skills"][0]["name"] in ["Data Structures", "Java", "SQL"]
    assert "Software Development" in context["interests"]
    assert len(context["assessment"]) == 2
    assert context["assessment"][0]["category"] == "Logic & Software Systems"
    assert context["resume"]["guidance_score"] == 85


def test_fingerprint_deterministic_and_invalidation(sample_profile_a, sample_skills_a, sample_interests_a, sample_assessment_a, sample_resume_a):
    mock_profile_repo = MagicMock()
    mock_profile_repo.get_by_id.return_value = sample_profile_a
    mock_profile_repo.get_skills.return_value = sample_skills_a
    mock_profile_repo.get_interests.return_value = sample_interests_a
    mock_profile_repo.get_assessment_answers.return_value = sample_assessment_a
    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_latest_resume_analysis.return_value = sample_resume_a

    ctx1 = build_student_ai_context(mock_profile_repo, mock_analysis_repo, "prof-001")
    ctx2 = build_student_ai_context(mock_profile_repo, mock_analysis_repo, "prof-001")

    fp1 = compute_student_context_fingerprint(ctx1)
    fp2 = compute_student_context_fingerprint(ctx2)
    assert fp1 == fp2, "Identical student input must generate the exact same fingerprint"

    # Invalidation 1: Profile change (e.g. student updates CGPA or career goal)
    ctx_modified_goal = copy.deepcopy(ctx1)
    ctx_modified_goal["career_goal"] = "AI / ML Engineer"
    assert compute_student_context_fingerprint(ctx_modified_goal) != fp1

    # Invalidation 2: Skills change
    ctx_modified_skills = copy.deepcopy(ctx1)
    ctx_modified_skills["skills"].append({"name": "Docker", "proficiency": "beginner", "category": "DevOps"})
    assert compute_student_context_fingerprint(ctx_modified_skills) != fp1

    # Invalidation 3: Assessment change
    ctx_modified_assessment = copy.deepcopy(ctx1)
    ctx_modified_assessment["assessment"][0]["selected_option"] = "Designing UI / UX mockups"
    assert compute_student_context_fingerprint(ctx_modified_assessment) != fp1

    # Invalidation 4: Resume change
    ctx_modified_resume = copy.deepcopy(ctx1)
    ctx_modified_resume["resume"]["resume_id"] = "res-002"
    assert compute_student_context_fingerprint(ctx_modified_resume) != fp1


# ---------------------------------------------------------------------------
# Test Personalization: Profile A vs Profile B
# ---------------------------------------------------------------------------

def test_personalization_prompts_differ(sample_profile_a, sample_skills_a, sample_interests_a, sample_assessment_a, sample_resume_a,
                                        sample_profile_b, sample_skills_b, sample_interests_b, sample_assessment_b):
    # Context A
    mock_p_repo_a = MagicMock()
    mock_p_repo_a.get_by_id.return_value = sample_profile_a
    mock_p_repo_a.get_skills.return_value = sample_skills_a
    mock_p_repo_a.get_interests.return_value = sample_interests_a
    mock_p_repo_a.get_assessment_answers.return_value = sample_assessment_a
    mock_a_repo_a = MagicMock()
    mock_a_repo_a.get_latest_resume_analysis.return_value = sample_resume_a
    ctx_a = build_student_ai_context(mock_p_repo_a, mock_a_repo_a, "prof-001")

    # Context B
    mock_p_repo_b = MagicMock()
    mock_p_repo_b.get_by_id.return_value = sample_profile_b
    mock_p_repo_b.get_skills.return_value = sample_skills_b
    mock_p_repo_b.get_interests.return_value = sample_interests_b
    mock_p_repo_b.get_assessment_answers.return_value = sample_assessment_b
    mock_a_repo_b = MagicMock()
    mock_a_repo_b.get_latest_resume_analysis.return_value = None
    ctx_b = build_student_ai_context(mock_p_repo_b, mock_a_repo_b, "prof-002")

    prompt_a = build_career_analysis_prompt(ctx_a)
    prompt_b = build_career_analysis_prompt(ctx_b)

    assert "Java" in prompt_a
    assert "Backend Software Developer" in prompt_a
    assert "Logic & Software Systems" in prompt_a

    assert "TCP/IP Networking" in prompt_b
    assert "Cybersecurity & Network Defense" in prompt_b
    assert "Computer Networks & Cybersecurity" in prompt_b

    assert prompt_a != prompt_b


# ---------------------------------------------------------------------------
# Test Dynamic Career Discovery & 5-Dimension Validation
# ---------------------------------------------------------------------------

def test_dynamic_career_discovery_and_dimension_scores():
    dynamic_ai_response = {
        "summary": "Comprehensive personalized career intelligence for diploma engineering student with modern industry alignment.",
        "recommended_careers": [
            {
                "career_id": "devops-engineer",
                "title": "Cloud DevOps Engineer",
                "score": 93.5,
                "branch_compatibility": 95.0,
                "skill_match": 88.0,
                "interest_alignment": 96.0,
                "goal_alignment": 92.0,
                "academic_compatibility": 94.0,
                "reason": "Strong Linux and networking foundations match modern cloud automation engineering.",
                "matched_skills": ["Linux", "Networking"],
                "missing_skills": ["Kubernetes", "Terraform", "CI/CD"],
                "career_outlook": "High growth in Indian tech ecosystem",
                "next_steps": ["Learn Docker containerization", "Practice GitHub Actions CI/CD"],
            },
            {
                "career_id": "security-analyst",
                "title": "SOC Cybersecurity Analyst",
                "score": 91.0,
                "branch_compatibility": 90.0,
                "skill_match": 86.0,
                "interest_alignment": 95.0,
                "goal_alignment": 93.0,
                "academic_compatibility": 90.0,
                "reason": "Packet capture and perimeter defense assessment signals indicate strong incident response aptitude.",
                "matched_skills": ["Wireshark", "Linux"],
                "missing_skills": ["SIEM Tools", "Network Security Fundamentals"],
                "career_outlook": "Critical demand across banking, defense, and IT services",
                "next_steps": ["Complete Splunk fundamentals", "Study for CompTIA Security+"],
            },
        ],
        "strengths": ["Strong systems understanding", "Methodical security mindset"],
        "skill_gaps": [
            {
                "skill_name": "Kubernetes",
                "current_level": "none",
                "required_level": "intermediate",
                "priority": "high",
                "learning_resource": "Kubernetes Official Interactive Tutorials",
            }
        ],
        "priority_skills": ["Kubernetes", "Terraform"],
        "roadmap_steps": [
            {
                "step_number": 1,
                "title": "Container Orchestration",
                "description": "Learn container management and pods with Kubernetes.",
                "duration_weeks": 6,
                "skills_gained": ["Kubernetes"],
                "resources": ["kubernetes.io"],
            }
        ],
        "project_recommendations": [
            {
                "title": "Multi-tier Microservices on Kubernetes",
                "description": "Deploy backend API and database on local minikube cluster.",
                "skills_practiced": ["Kubernetes", "Linux"],
                "difficulty": "intermediate",
                "estimated_hours": 25,
            }
        ],
        "next_steps": ["Set up local Minikube cluster", "Deploy first deployment manifest"],
    }

    validated = CareerAnalysisAIResponse.model_validate(dynamic_ai_response)
    assert len(validated.recommended_careers) == 2
    top = validated.recommended_careers[0]
    assert top.title == "Cloud DevOps Engineer"
    assert top.score == 93.5
    assert top.branch_compatibility == 95.0
    assert top.skill_match == 88.0
    assert top.interest_alignment == 96.0
    assert top.goal_alignment == 92.0
    assert top.academic_compatibility == 94.0


# ---------------------------------------------------------------------------
# Test Cache Invalidation in AnalysisService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analysis_service_cache_hit_and_miss(sample_profile_a, sample_skills_a, sample_interests_a, sample_assessment_a):
    mock_profile_repo = MagicMock()
    mock_profile_repo.get_by_id.return_value = sample_profile_a
    mock_profile_repo.get_skills.return_value = sample_skills_a
    mock_profile_repo.get_interests.return_value = sample_interests_a
    mock_profile_repo.get_assessment_answers.return_value = sample_assessment_a

    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_latest_resume_analysis.return_value = None

    mock_career_repo = MagicMock()
    mock_career_repo.get_careers_with_skills.return_value = []

    mock_ai = MagicMock(spec=GeminiProvider)
    mock_ai.model_name = "gemini-1.5-flash"

    # 1. When cache exists
    mock_analysis_repo.get_valid_cached_analysis.return_value = {
        "id": "cached-analysis-1",
        "summary": "Existing cached analysis",
        "recommended_careers": [{"title": "Software Developer", "score": 90.0}],
    }

    service = AnalysisService(
        profile_repo=mock_profile_repo,
        career_repo=mock_career_repo,
        analysis_repo=mock_analysis_repo,
        ai_provider=mock_ai,
    )

    result = await service.get_or_create_analysis("prof-001", force_regenerate=False)
    assert result["is_cached"] is True
    mock_ai.analyze_career.assert_not_called()

    # 2. When forced regenerate or cache missing
    mock_analysis_repo.get_valid_cached_analysis.return_value = None
    mock_ai_result = MagicMock()
    mock_ai_result.summary = "Fresh AI analysis generated by Gemini"
    mock_ai_result.recommended_careers = [
        RecommendedCareer(
            career_id="software-engineer",
            title="Software Engineer",
            score=92.0,
            reason="Strong Java foundation",
        )
    ]
    mock_ai_result.strengths = ["Java fundamentals"]
    mock_ai_result.skill_gaps = []
    mock_ai_result.priority_skills = ["DSA"]
    mock_ai_result.roadmap_steps = []
    mock_ai_result.project_recommendations = []
    mock_ai_result.next_steps = ["Build a project"]
    mock_ai.analyze_career = AsyncMock(return_value=mock_ai_result)

    mock_analysis_repo.save_analysis.return_value = {
        "id": "new-analysis-1",
        "summary": "Fresh AI analysis generated by Gemini",
    }

    fresh_result = await service.get_or_create_analysis("prof-001", force_regenerate=True)
    assert fresh_result["is_cached"] is False
    mock_ai.analyze_career.assert_called_once()


# ---------------------------------------------------------------------------
# Test Transparent Fallback when Gemini is Unavailable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analysis_service_fallback_when_gemini_unavailable(sample_profile_a, sample_skills_a, sample_interests_a):
    mock_profile_repo = MagicMock()
    mock_profile_repo.get_by_id.return_value = sample_profile_a
    mock_profile_repo.get_skills.return_value = sample_skills_a
    mock_profile_repo.get_interests.return_value = sample_interests_a
    mock_profile_repo.get_assessment_answers.return_value = []

    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_valid_cached_analysis.return_value = None
    mock_analysis_repo.get_latest_resume_analysis.return_value = None

    mock_career_repo = MagicMock()
    mock_career_repo.get_careers_with_skills.return_value = [
        {
            "id": "car-1",
            "title": "Software Developer",
            "branches": ["Computer Engineering"],
            "industry": "IT",
            "career_skills": [],
        }
    ]

    mock_ai = MagicMock(spec=GeminiProvider)
    mock_ai.model_name = "gemini-1.5-flash"
    mock_ai.analyze_career = AsyncMock(side_effect=RuntimeError("Gemini quota exceeded or timeout"))

    service = AnalysisService(
        profile_repo=mock_profile_repo,
        career_repo=mock_career_repo,
        analysis_repo=mock_analysis_repo,
        ai_provider=mock_ai,
    )

    fallback_result = await service.get_or_create_analysis("prof-001", force_regenerate=True)

    assert fallback_result["is_fallback"] is True
    assert fallback_result["model_name"] == "rule-engine-fallback"
    assert "temporarily offline" in fallback_result["summary"]
    assert len(fallback_result["recommended_careers"]) >= 1


# ---------------------------------------------------------------------------
# Test Chatbot Context-Aware System Prompt
# ---------------------------------------------------------------------------

def test_chatbot_context_injection():
    profile = {"branch": "CSE", "semester": 5, "cgpa": 8.5, "skills": [{"name": "Java", "proficiency": "advanced"}]}
    career_goal = "Backend Engineer"
    skill_gaps = [{"skill_name": "Docker"}]
    latest_analysis = {
        "recommended_careers": [
            {"title": "Backend Software Developer", "score": 94.0, "reason": "Strong Java + SQL skills"}
        ]
    }
    assessment_signals = [
        {"category": "Software Architecture", "question_text": "Preferred focus", "selected_option": "Backend APIs"}
    ]
    resume_context = {"guidance_score": 85, "strengths": ["Spring Boot REST APIs"]}

    prompt = build_chatbot_system_prompt(
        profile=profile,
        career_goal=career_goal,
        skill_gaps=skill_gaps,
        latest_analysis=latest_analysis,
        assessment_signals=assessment_signals,
        resume_context=resume_context,
    )

    assert "Backend Software Developer" in prompt
    assert "94% Match" in prompt
    assert "Backend APIs" in prompt
    assert "Spring Boot REST APIs" in prompt
    assert "Why did you recommend [career] for me?" in prompt
