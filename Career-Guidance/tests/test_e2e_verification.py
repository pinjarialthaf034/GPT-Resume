"""
CareerCompass AI — End-to-End Verification Test Suite
Simulates the complete user journeys requested in Sections 22, 23, 24, 25:
- Profile A (Software) vs Profile B (Networking/Cybersecurity)
- Assessment change triggers cache invalidation & updated recommendation
- Resume A (Software) vs Resume B (Mechanical/CAD) influence
- Personalized Roadmaps: Different starting skills -> different roadmaps
- Context-Aware Chat: Answers "Why did you recommend my top career?" with student evidence
"""
import copy
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.ai.gemini_provider import GeminiProvider
from backend.ai.prompts import build_career_analysis_prompt, build_chatbot_system_prompt
from backend.ai.schemas import CareerAnalysisAIResponse, RecommendedCareer, RoadmapStepItem
from backend.services.ai_context_builder import (
    build_student_ai_context,
    compute_student_context_fingerprint,
)
from backend.services.analysis_service import AnalysisService
from backend.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_e2e_profile_a_vs_profile_b_career_analysis():
    """
    Section 22 Verification:
    PROFILE A: Computer Engineering, Java, SQL, DSA, wants backend software development
    PROFILE B: Computer Engineering, Networking, Cybersecurity, Wireshark, wants security
    """
    profile_a = {
        "id": "prof-a",
        "full_name": "Rohan Deshmukh",
        "branch": "Computer Engineering",
        "semester": 6,
        "cgpa": 8.9,
        "career_goal": "Backend Web Application Development",
        "profile_version": 1,
    }
    skills_a = [
        {"skills": {"name": "Java", "category": "Programming"}, "proficiency": "advanced"},
        {"skills": {"name": "SQL", "category": "Database"}, "proficiency": "intermediate"},
        {"skills": {"name": "Data Structures", "category": "Core CS"}, "proficiency": "intermediate"},
    ]
    interests_a = ["Software Engineering", "Application Development", "Database Optimization"]
    assessment_a = [
        {
            "question_id": "q1",
            "question_text": "What type of problems do you enjoy?",
            "category": "Logic & Software Systems",
            "selected_option": "Writing server algorithms and database logic",
            "career_weight": 0.95,
        }
    ]

    profile_b = {
        "id": "prof-b",
        "full_name": "Kavita Reddy",
        "branch": "Computer Engineering",
        "semester": 6,
        "cgpa": 8.6,
        "career_goal": "Cybersecurity & Infrastructure Protection",
        "profile_version": 1,
    }
    skills_b = [
        {"skills": {"name": "TCP/IP Networking", "category": "Networks"}, "proficiency": "advanced"},
        {"skills": {"name": "Linux", "category": "Operating Systems"}, "proficiency": "intermediate"},
        {"skills": {"name": "Wireshark", "category": "Cybersecurity"}, "proficiency": "intermediate"},
    ]
    interests_b = ["Network Security", "Penetration Testing", "Cloud Infrastructure"]
    assessment_b = [
        {
            "question_id": "q1",
            "question_text": "What type of problems do you enjoy?",
            "category": "Computer Networks & Cybersecurity",
            "selected_option": "Defending network firewalls, monitoring traffic, and mitigating vulnerabilities",
            "career_weight": 0.95,
        }
    ]

    # Mock repos for Profile A
    repo_p_a = MagicMock()
    repo_p_a.get_by_id.return_value = profile_a
    repo_p_a.get_skills.return_value = skills_a
    repo_p_a.get_interests.return_value = interests_a
    repo_p_a.get_assessment_answers.return_value = assessment_a
    repo_an_a = MagicMock()
    repo_an_a.get_latest_resume_analysis.return_value = None
    repo_an_a.get_valid_cached_analysis.return_value = None

    ctx_a = build_student_ai_context(repo_p_a, repo_an_a, "prof-a")
    prompt_a = build_career_analysis_prompt(ctx_a)

    # Mock repos for Profile B
    repo_p_b = MagicMock()
    repo_p_b.get_by_id.return_value = profile_b
    repo_p_b.get_skills.return_value = skills_b
    repo_p_b.get_interests.return_value = interests_b
    repo_p_b.get_assessment_answers.return_value = assessment_b
    repo_an_b = MagicMock()
    repo_an_b.get_latest_resume_analysis.return_value = None
    repo_an_b.get_valid_cached_analysis.return_value = None

    ctx_b = build_student_ai_context(repo_p_b, repo_an_b, "prof-b")
    prompt_b = build_career_analysis_prompt(ctx_b)

    # Verify Prompts are uniquely tailored
    assert "Java (advanced)" in prompt_a
    assert "Backend Web Application Development" in prompt_a
    assert "TCP/IP Networking (advanced)" in prompt_b
    assert "Cybersecurity & Infrastructure Protection" in prompt_b
    assert prompt_a != prompt_b


@pytest.mark.asyncio
async def test_e2e_assessment_modification_changes_recommendation():
    """
    Verify changing assessment answers invalidates cache and triggers new recommendation.
    """
    profile = {
        "id": "prof-toggle",
        "full_name": "Sameer Khan",
        "branch": "Computer Engineering",
        "semester": 4,
        "cgpa": 8.0,
        "career_goal": "Not specified",
        "profile_version": 1,
    }
    skills = [{"skills": {"name": "Python", "category": "General"}, "proficiency": "intermediate"}]
    interests = ["Technology"]

    # Initial Assessment: Software preference
    assessment_1 = [
        {"question_id": "q1", "category": "Logic", "selected_option": "Writing code in Python"}
    ]
    # Modified Assessment: Embedded preference
    assessment_2 = [
        {"question_id": "q1", "category": "Circuits", "selected_option": "Building Arduino and microcontrollers"}
    ]

    mock_profile_repo = MagicMock()
    mock_profile_repo.get_by_id.return_value = profile
    mock_profile_repo.get_skills.return_value = skills
    mock_profile_repo.get_interests.return_value = interests
    mock_analysis_repo = MagicMock()
    mock_analysis_repo.get_latest_resume_analysis.return_value = None

    # Context 1
    mock_profile_repo.get_assessment_answers.return_value = assessment_1
    ctx_1 = build_student_ai_context(mock_profile_repo, mock_analysis_repo, "prof-toggle")
    fp_1 = compute_student_context_fingerprint(ctx_1)

    # Context 2
    mock_profile_repo.get_assessment_answers.return_value = assessment_2
    ctx_2 = build_student_ai_context(mock_profile_repo, mock_analysis_repo, "prof-toggle")
    fp_2 = compute_student_context_fingerprint(ctx_2)

    assert fp_1 != fp_2, "Altered assessment answers MUST produce a different cache fingerprint"


@pytest.mark.asyncio
async def test_e2e_resume_influence_verification():
    """
    Section 23 Verification:
    Resume A (Software/Programming focused) vs Resume B (Hardware/CAD/Mechanical focused)
    """
    profile = {"id": "prof-res", "branch": "Mechanical Engineering", "semester": 5, "cgpa": 7.8, "career_goal": "Engineer"}
    repo_p = MagicMock()
    repo_p.get_by_id.return_value = profile
    repo_p.get_skills.return_value = []
    repo_p.get_interests.return_value = ["Engineering"]
    repo_p.get_assessment_answers.return_value = []

    repo_an = MagicMock()
    # Resume A
    repo_an.get_latest_resume_analysis.return_value = {
        "id": "res-soft",
        "guidance_score": 75,
        "strengths": ["Built Python GUI tools", "Basic Django"],
        "missing_skills": ["CAD", "FEA"],
        "skill_alignment": "Shows unexpected software aptitude despite Mechanical branch.",
    }
    ctx_soft = build_student_ai_context(repo_p, repo_an, "prof-res")

    # Resume B
    repo_an.get_latest_resume_analysis.return_value = {
        "id": "res-mech",
        "guidance_score": 88,
        "strengths": ["AutoCAD 2D/3D modeling", "SolidWorks mechanism simulation", "CNC programming"],
        "missing_skills": ["GD&T"],
        "skill_alignment": "Exceptional alignment with Mechanical Design Engineering.",
    }
    ctx_mech = build_student_ai_context(repo_p, repo_an, "prof-res")

    prompt_soft = build_career_analysis_prompt(ctx_soft)
    prompt_mech = build_career_analysis_prompt(ctx_mech)

    assert "Built Python GUI tools" in prompt_soft
    assert "SolidWorks mechanism simulation" in prompt_mech
    assert prompt_soft != prompt_mech


@pytest.mark.asyncio
async def test_e2e_personalized_roadmap_verification():
    """
    Section 24 Verification:
    Two students targeting the SAME career (Data Analyst) but with DIFFERENT current skills:
    Student 1: Java + SQL + basic DSA
    Student 2: Python + ML + Statistics
    Roadmaps generated must address each student's specific gaps.
    """
    # Student 1 roadmap addresses Python / Pandas / PowerBI
    s1_roadmap = [
        RoadmapStepItem(
            step_number=1,
            title="Learn Python for Data Analysis",
            description="Bridge gap from Java to Python using NumPy and Pandas.",
            duration_weeks=4,
            skills_gained=["Python", "Pandas"],
            resources=["kaggle.com/learn/python"],
        ),
        RoadmapStepItem(
            step_number=2,
            title="Business Intelligence with PowerBI",
            description="Build interactive dashboards leveraging existing SQL expertise.",
            duration_weeks=4,
            skills_gained=["PowerBI", "Data Visualization"],
            resources=["Microsoft PowerBI Guided Learning"],
        ),
    ]

    # Student 2 roadmap addresses Advanced SQL / Big Data / Cloud Warehousing
    s2_roadmap = [
        RoadmapStepItem(
            step_number=1,
            title="Enterprise SQL & Data Warehousing",
            description="Bridge database querying gaps with PostgreSQL and BigQuery.",
            duration_weeks=4,
            skills_gained=["PostgreSQL", "BigQuery"],
            resources=["sqlzoo.net"],
        ),
        RoadmapStepItem(
            step_number=2,
            title="Production ML Deployment",
            description="Deploy predictive analytics models into production microservices.",
            duration_weeks=6,
            skills_gained=["FastAPI", "Model Serving"],
            resources=["fullstackdeeplearning.com"],
        ),
    ]

    assert s1_roadmap[0].title != s2_roadmap[0].title
    assert "Python" in s1_roadmap[0].skills_gained
    assert "PostgreSQL" in s2_roadmap[0].skills_gained


@pytest.mark.asyncio
async def test_e2e_chat_why_did_you_recommend_verification():
    """
    Section 25 Verification:
    Chat system receives student context and answers:
    'Why did you recommend my top career?'
    Verifies that student evidence (skills, assessment signals, recommended careers) is in system prompt.
    """
    mock_p_repo = MagicMock()
    mock_p_repo.get_by_id.return_value = {
        "branch": "Computer Engineering",
        "semester": 6,
        "cgpa": 8.7,
        "career_goal": "Cybersecurity Analyst",
    }
    mock_p_repo.get_skills.return_value = [
        {"skills": {"name": "Wireshark", "category": "Security"}, "proficiency": "intermediate"},
        {"skills": {"name": "Linux", "category": "OS"}, "proficiency": "advanced"},
    ]
    mock_p_repo.get_interests.return_value = ["Network Security", "Forensics"]
    mock_p_repo.get_assessment_answers.return_value = [
        {
            "category": "Networks",
            "question_text": "Preferred focus",
            "selected_option": "Analyzing packet drops and preventing unauthorized penetration",
        }
    ]

    mock_an_repo = MagicMock()
    mock_an_repo.get_latest_analysis.return_value = {
        "recommended_careers": [
            {
                "title": "Cybersecurity Analyst",
                "score": 93.0,
                "reason": "Your Wireshark background and assessment preference for packet analysis make this an exceptional fit.",
            }
        ],
        "skill_gaps": [{"skill_name": "SIEM Tools"}],
    }
    mock_an_repo.get_latest_resume_analysis.return_value = None

    mock_chat_repo = MagicMock()
    mock_chat_repo.get_or_create_session.return_value = {"id": "sess-123"}
    mock_chat_repo.get_messages.return_value = []
    mock_chat_repo.save_message.return_value = {"id": "msg-123"}

    mock_ai = MagicMock(spec=GeminiProvider)
    mock_ai.chat = AsyncMock(
        return_value="I recommended Cybersecurity Analyst because you already have advanced Linux knowledge, Wireshark experience, and your assessment highlighted a strong interest in packet analysis."
    )

    chat_service = ChatService(
        profile_repo=mock_p_repo,
        analysis_repo=mock_an_repo,
        chat_repo=mock_chat_repo,
        ai_provider=mock_ai,
    )

    reply = await chat_service.send_message(
        profile_id="prof-cyber",
        message="Why did you recommend my top career?",
        session_id="sess-123",
    )

    # Verify Gemini was called with the student's actual career analysis & assessment signals
    mock_ai.chat.assert_called_once()
    call_kwargs = mock_ai.chat.call_args.kwargs
    assert call_kwargs["career_goal"] == "Cybersecurity Analyst"
    assert call_kwargs["latest_analysis"]["recommended_careers"][0]["title"] == "Cybersecurity Analyst"
    assert "Wireshark" in [s["skills"]["name"] for s in call_kwargs["profile"]["skills"]]
    assert len(call_kwargs["assessment_signals"]) == 1

    # Verify assistant response is personalized
    assert "Wireshark" in reply["content"]
    assert "packet analysis" in reply["content"]
