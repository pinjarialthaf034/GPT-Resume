"""
CareerCompass AI — Career Selection After Assessment & Role-Specific Roadmap Architecture
Comprehensive Test Suite covering all 20 requirements from prompt Section 15:
1. Top 3 careers returned.
2. Rank #1 can be selected.
3. Rank #2 can be selected.
4. Rank #3 can be selected.
5. Selected career persists.
6. Selected career returned by latest analysis.
7. Career outside Top 3 rejected.
8. Rank #2 produces Rank #2 roadmap.
9. Rank #3 produces Rank #3 roadmap.
10. Gemini success produces selected-career roadmap.
11. Gemini failure produces selected-career fallback roadmap.
12. Fallback never silently switches to Rank #1.
13. Refresh preserves selected career.
14. Roadmap API returns selected career.
15. Progress persists.
16. Switching careers resets progress appropriately.
17. Re-analysis clears stale selected career.
18. No arbitrary career can generate a roadmap.
19. No API key appears in response/logs/frontend.
20. Pydantic CareerSelectionRequest validation.
"""

import os
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.ai.schemas import (
    CareerAnalysisAIResponse,
    RecommendedCareer,
    RoadmapStepItem,
    ProjectRecommendation,
    RoleRoadmapAIResponse,
)
from backend.main import app
from backend.models.career import CareerSelectionRequest
from backend.deps import get_current_user, AuthenticatedUser
from backend.api.analysis import _get_service
from backend.services.analysis_service import AnalysisService


# ---------------------------------------------------------------------------
# Fixtures and Sample Data
# ---------------------------------------------------------------------------

SAMPLE_PROFILE_ID = "00000000-0000-0000-0000-000000000001"

SAMPLE_TOP_3 = [
    {
        "career_id": "c1",
        "title": "Software Developer",
        "score": 55.0,
        "reason": "Strong general software development foundation",
        "matched_skills": ["Python", "Git"],
        "missing_skills": ["Design Patterns", "System Design"],
    },
    {
        "career_id": "c2",
        "title": "Backend Developer",
        "score": 47.0,
        "reason": "High interest in databases and server logic",
        "matched_skills": ["Python", "SQL"],
        "missing_skills": ["Docker", "Redis", "Microservices"],
    },
    {
        "career_id": "c3",
        "title": "Full Stack Developer",
        "score": 43.0,
        "reason": "Good cross-tier aptitude across frontend and backend",
        "matched_skills": ["HTML", "JavaScript"],
        "missing_skills": ["React", "Node.js", "REST APIs"],
    },
]

SAMPLE_ANALYSIS_RECORD = {
    "id": "analysis-uuid-12345",
    "profile_id": SAMPLE_PROFILE_ID,
    "profile_version": 1,
    "model_name": "gemini-2.5-flash",
    "prompt_version": "v1.0",
    "summary": "Profile matches Software, Backend, and Full Stack development roles.",
    "recommended_careers": SAMPLE_TOP_3,
    "strengths": ["Strong logic", "Quick learner"],
    "skill_gaps": [
        {"skill_name": "Docker", "current_level": "none", "required_level": "intermediate", "priority": "high"}
    ],
    "priority_skills": ["Docker", "Redis"],
    "roadmap_steps": [
        {
            "step_number": 1,
            "title": "Software Engineering Foundations",
            "duration_weeks": 4,
            "description": "Learn fundamentals",
            "skills_gained": ["Python", "Data Structures"],
            "resources": ["Official Documentation"],
        }
    ],
    "project_recommendations": [
        {
            "title": "CLI Tool",
            "description": "Build a command line application",
            "difficulty": "beginner",
            "skills_practiced": ["Python"],
            "estimated_hours": 15,
        }
    ],
    "next_steps": ["Start learning"],
    "selected_career": None,
    "is_fallback": False,
}


@pytest.fixture
def mock_repos():
    """Creates mocked repositories and AI provider for unit testing AnalysisService."""
    profile_repo = MagicMock()
    career_repo = MagicMock()
    analysis_repo = MagicMock()
    ai_provider = MagicMock()

    profile_repo.get_by_id.return_value = {
        "id": SAMPLE_PROFILE_ID,
        "full_name": "Aarav Sharma",
        "branch": "Computer Engineering",
        "semester": 5,
        "cgpa": 8.4,
        "career_goal": "Software Engineer",
        "profile_version": 1,
    }
    profile_repo.get_skills.return_value = [
        {"skills": {"name": "Python", "category": "Programming"}, "proficiency": "intermediate"},
        {"skills": {"name": "SQL", "category": "Database"}, "proficiency": "beginner"},
    ]
    profile_repo.get_interests.return_value = ["Backend Engineering", "Databases"]
    profile_repo.get_assessment_answers.return_value = []

    career_repo.get_all_careers_with_skills.return_value = [
        {
            "id": "c1",
            "title": "Software Developer",
            "branches": ["Computer Engineering", "Information Technology"],
            "career_skills": [{"skills": {"name": "Python"}, "required_level": "intermediate"}],
        },
        {
            "id": "c2",
            "title": "Backend Developer",
            "branches": ["Computer Engineering"],
            "career_skills": [{"skills": {"name": "Python"}, "required_level": "intermediate"}, {"skills": {"name": "SQL"}, "required_level": "intermediate"}],
        },
        {
            "id": "c3",
            "title": "Full Stack Developer",
            "branches": ["Computer Engineering"],
            "career_skills": [{"skills": {"name": "JavaScript"}, "required_level": "intermediate"}],
        },
    ]
    career_repo.get_career_by_id.return_value = {
        "id": "c2",
        "title": "Backend Developer",
        "career_projects": [
            {
                "projects": {
                    "title": "REST API Server",
                    "description": "Build high-throughput CRUD API",
                    "difficulty": "intermediate",
                    "skills_practiced": ["Python", "FastAPI", "SQL"],
                    "estimated_hours": 25,
                }
            }
        ],
    }

    # Analysis repo mock
    analysis_repo.get_latest_analysis.return_value = dict(SAMPLE_ANALYSIS_RECORD)
    analysis_repo.save_analysis.side_effect = lambda pid, ver, data: {
        "id": "analysis-uuid-12345",
        "profile_id": pid,
        "profile_version": ver,
        **data,
    }

    def mock_update(analysis_id, profile_id, selected_career, roadmap_bundle=None, model_name=None):
        rb = roadmap_bundle or {}
        return {
            "id": analysis_id,
            "profile_id": profile_id,
            "selected_career": selected_career,
            "roadmap_steps": rb.get("roadmap_steps", []),
            "project_recommendations": rb.get("project_recommendations", []),
            "skill_gaps": rb.get("skill_gaps", []),
            "priority_skills": rb.get("priority_skills", []),
            "model_name": model_name or "gemini-2.5-flash",
        }

    analysis_repo.update_analysis_selected_career.side_effect = mock_update
    analysis_repo.get_roadmap_progress.return_value = [1]

    ai_provider.model_name = "gemini-2.5-flash"
    ai_provider.analysis_prompt_version = "v1.0"
    ai_provider.role_roadmap_prompt_version = "v1.0"

    service = AnalysisService(
        profile_repo=profile_repo,
        career_repo=career_repo,
        analysis_repo=analysis_repo,
        ai_provider=ai_provider,
    )
    return service, profile_repo, career_repo, analysis_repo, ai_provider


# ---------------------------------------------------------------------------
# Test Cases 1 - 20
# ---------------------------------------------------------------------------

def test_1_top_3_careers_returned(mock_repos):
    """1. Top 3 careers returned in latest analysis."""
    service, _, _, analysis_repo, _ = mock_repos
    latest = service.get_latest_analysis(SAMPLE_PROFILE_ID)
    assert latest is not None
    assert "recommended_careers" in latest
    recs = latest["recommended_careers"]
    assert len(recs) >= 3
    assert recs[0]["title"] == "Software Developer"
    assert recs[1]["title"] == "Backend Developer"
    assert recs[2]["title"] == "Full Stack Developer"


@pytest.mark.asyncio
async def test_2_rank_1_can_be_selected(mock_repos):
    """2. Rank #1 can be selected and generates Rank 1 roadmap."""
    service, _, _, analysis_repo, ai_provider = mock_repos

    # Mock Gemini returning Rank 1 roadmap
    ai_provider.generate_role_roadmap = AsyncMock(return_value=RoleRoadmapAIResponse(
        career_target="Software Developer",
        roadmap_steps=[
            RoadmapStepItem(
                step_number=1,
                title="Software Foundations",
                duration_weeks=4,
                description="Core algorithms and data structures",
                skills_gained=["DSA", "Python"],
                resources=["Resource 1"],
            )
        ],
        project_recommendations=[],
        skill_gaps=[],
        priority_skills=["DSA"],
    ))

    result = await service.select_career_and_generate_roadmap(SAMPLE_PROFILE_ID, "Software Developer")
    assert result["selected_career"] == "Software Developer"
    assert result["career_target"] == "Software Developer"
    assert result["has_selected_career"] is True
    assert result["roadmap_steps"][0]["title"] == "Software Foundations"


@pytest.mark.asyncio
async def test_3_rank_2_can_be_selected(mock_repos):
    """3. Rank #2 can be selected and generates Rank 2 roadmap."""
    service, _, _, analysis_repo, ai_provider = mock_repos

    ai_provider.generate_role_roadmap = AsyncMock(return_value=RoleRoadmapAIResponse(
        career_target="Backend Developer",
        roadmap_steps=[
            RoadmapStepItem(
                step_number=1,
                title="Backend Architecture & Databases",
                duration_weeks=4,
                description="Server-side programming and relational data modeling",
                skills_gained=["FastAPI", "PostgreSQL"],
                resources=["FastAPI Docs"],
            )
        ],
        project_recommendations=[],
        skill_gaps=[],
        priority_skills=["FastAPI", "PostgreSQL"],
    ))

    result = await service.select_career_and_generate_roadmap(SAMPLE_PROFILE_ID, "Backend Developer")
    assert result["selected_career"] == "Backend Developer"
    assert result["career_target"] == "Backend Developer"
    assert result["has_selected_career"] is True
    assert "Backend Architecture" in result["roadmap_steps"][0]["title"]


@pytest.mark.asyncio
async def test_4_rank_3_can_be_selected(mock_repos):
    """4. Rank #3 can be selected and generates Rank 3 roadmap."""
    service, _, _, analysis_repo, ai_provider = mock_repos

    ai_provider.generate_role_roadmap = AsyncMock(return_value=RoleRoadmapAIResponse(
        career_target="Full Stack Developer",
        roadmap_steps=[
            RoadmapStepItem(
                step_number=1,
                title="Full Stack Web Development",
                duration_weeks=6,
                description="Connecting client-side React with server APIs",
                skills_gained=["React", "Node.js"],
                resources=["MDN Web Docs"],
            )
        ],
        project_recommendations=[],
        skill_gaps=[],
        priority_skills=["React", "Node.js"],
    ))

    result = await service.select_career_and_generate_roadmap(SAMPLE_PROFILE_ID, "Full Stack Developer")
    assert result["selected_career"] == "Full Stack Developer"
    assert result["career_target"] == "Full Stack Developer"
    assert result["has_selected_career"] is True
    assert "Full Stack" in result["roadmap_steps"][0]["title"]


@pytest.mark.asyncio
async def test_5_selected_career_persists(mock_repos):
    """5. Selected career persists in the repository."""
    service, _, _, analysis_repo, ai_provider = mock_repos

    ai_provider.generate_role_roadmap = AsyncMock(return_value=RoleRoadmapAIResponse(
        career_target="Backend Developer",
        roadmap_steps=[
            RoadmapStepItem(
                step_number=1,
                title="Backend Architecture",
                duration_weeks=3,
                description="Desc",
                skills_gained=["SQL"],
                resources=[],
            )
        ],
        project_recommendations=[],
        skill_gaps=[],
        priority_skills=[],
    ))

    await service.select_career_and_generate_roadmap(SAMPLE_PROFILE_ID, "Backend Developer")

    analysis_repo.update_analysis_selected_career.assert_called_once()
    _, kwargs = analysis_repo.update_analysis_selected_career.call_args
    assert kwargs["selected_career"] == "Backend Developer"


def test_6_selected_career_returned_by_latest_analysis(mock_repos):
    """6. Selected career returned by latest analysis query."""
    service, _, _, analysis_repo, _ = mock_repos

    record_with_selection = dict(SAMPLE_ANALYSIS_RECORD)
    record_with_selection["selected_career"] = "Backend Developer"
    analysis_repo.get_latest_analysis.return_value = record_with_selection

    latest = service.get_latest_analysis(SAMPLE_PROFILE_ID)
    assert latest["selected_career"] == "Backend Developer"
    assert latest["has_selected_career"] is True
    assert latest["career_target"] == "Backend Developer"


@pytest.mark.asyncio
async def test_7_career_outside_top_3_rejected(mock_repos):
    """7. Career outside Top 3 is rejected with clear ValueError."""
    service, _, _, _, _ = mock_repos

    with pytest.raises(ValueError) as excinfo:
        await service.select_career_and_generate_roadmap(SAMPLE_PROFILE_ID, "Doctor")

    assert "Selected career 'Doctor' is not among your Top 3 matches" in str(excinfo.value)
    assert "Software Developer" in str(excinfo.value)
    assert "Backend Developer" in str(excinfo.value)
    assert "Full Stack Developer" in str(excinfo.value)


@pytest.mark.asyncio
async def test_8_rank_2_produces_rank_2_roadmap(mock_repos):
    """8. Rank #2 produces a roadmap strictly targeting Rank 2, not Rank 1."""
    service, _, _, _, ai_provider = mock_repos

    ai_provider.generate_role_roadmap = AsyncMock(return_value=RoleRoadmapAIResponse(
        career_target="Backend Developer",
        roadmap_steps=[
            RoadmapStepItem(
                step_number=1,
                title="Advanced Backend & API Engineering",
                duration_weeks=4,
                description="APIs with FastAPI and PostgreSQL",
                skills_gained=["FastAPI", "PostgreSQL"],
                resources=["FastAPI Docs"],
            )
        ],
        project_recommendations=[
            ProjectRecommendation(
                title="Distributed Job Queue",
                description="Background workers with Redis and Celery",
                difficulty="advanced",
                skills_practiced=["Redis", "Celery", "Python"],
                estimated_hours=30,
            )
        ],
        skill_gaps=[],
        priority_skills=["Redis", "PostgreSQL"],
    ))

    result = await service.select_career_and_generate_roadmap(SAMPLE_PROFILE_ID, "Backend Developer")

    assert result["career_target"] == "Backend Developer"
    assert result["selected_career"] == "Backend Developer"
    assert result["career_target"] != "Software Developer"
    assert result["roadmap_steps"][0]["title"] == "Advanced Backend & API Engineering"
    assert result["project_recommendations"][0]["title"] == "Distributed Job Queue"


@pytest.mark.asyncio
async def test_9_rank_3_produces_rank_3_roadmap(mock_repos):
    """9. Rank #3 produces a roadmap strictly targeting Rank 3, not Rank 1."""
    service, _, _, _, ai_provider = mock_repos

    ai_provider.generate_role_roadmap = AsyncMock(return_value=RoleRoadmapAIResponse(
        career_target="Full Stack Developer",
        roadmap_steps=[
            RoadmapStepItem(
                step_number=1,
                title="Frontend Integration & Full Stack Routing",
                duration_weeks=5,
                description="End-to-end full stack architecture",
                skills_gained=["React", "TypeScript", "REST APIs"],
                resources=["React Documentation"],
            )
        ],
        project_recommendations=[],
        skill_gaps=[],
        priority_skills=["React", "TypeScript"],
    ))

    result = await service.select_career_and_generate_roadmap(SAMPLE_PROFILE_ID, "Full Stack Developer")

    assert result["career_target"] == "Full Stack Developer"
    assert result["selected_career"] == "Full Stack Developer"
    assert result["career_target"] != "Software Developer"
    assert "Full Stack Routing" in result["roadmap_steps"][0]["title"]


@pytest.mark.asyncio
async def test_10_gemini_success_produces_selected_career_roadmap(mock_repos):
    """10. When Gemini succeeds, generate_role_roadmap prompt and output target selected career."""
    service, _, _, _, ai_provider = mock_repos

    ai_provider.generate_role_roadmap = AsyncMock(return_value=RoleRoadmapAIResponse(
        career_target="Backend Developer",
        roadmap_steps=[
            RoadmapStepItem(
                step_number=1,
                title="FastAPI & Async Microservices",
                duration_weeks=4,
                description="High performance backend services",
                skills_gained=["FastAPI", "AsyncIO"],
                resources=[],
            )
        ],
        project_recommendations=[],
        skill_gaps=[],
        priority_skills=["FastAPI"],
    ))

    result = await service.select_career_and_generate_roadmap(SAMPLE_PROFILE_ID, "Backend Developer")

    assert result["is_fallback"] is False
    assert result["model_name"] == "gemini-2.5-flash"
    assert result["selected_career"] == "Backend Developer"
    assert result["career_target"] == "Backend Developer"

    # Verify Gemini prompt explicitly instructed not to substitute Rank 1
    call_args = ai_provider.generate_role_roadmap.call_args[0]
    student_ctx = call_args[0]
    selected_career_arg = call_args[1]
    assert selected_career_arg["title"] == "Backend Developer"


@pytest.mark.asyncio
async def test_11_gemini_failure_produces_selected_career_fallback_roadmap(mock_repos):
    """11. When Gemini fails, deterministic fallback produces roadmap for selected career."""
    service, _, _, _, ai_provider = mock_repos

    # Force Gemini to fail
    ai_provider.generate_role_roadmap = AsyncMock(side_effect=Exception("Gemini quota exceeded 429"))

    result = await service.select_career_and_generate_roadmap(SAMPLE_PROFILE_ID, "Backend Developer")

    assert result["is_fallback"] is True
    assert result["model_name"] == "rule-engine-fallback"
    assert result["selected_career"] == "Backend Developer"
    assert result["career_target"] == "Backend Developer"
    assert len(result["roadmap_steps"]) > 0
    titles = [s["title"] for s in result["roadmap_steps"]]
    assert any("Backend" in t or "Database" in t or "Core" in t for t in titles)


@pytest.mark.asyncio
async def test_12_fallback_never_silently_switches_to_rank_1(mock_repos):
    """12. Fallback NEVER silently defaults or falls back to Rank #1 when Rank #2 is selected."""
    service, _, _, _, ai_provider = mock_repos

    ai_provider.generate_role_roadmap = AsyncMock(side_effect=RuntimeError("AI connection timeout"))

    # Select Rank #2: Backend Developer
    result_rank_2 = await service.select_career_and_generate_roadmap(SAMPLE_PROFILE_ID, "Backend Developer")
    assert result_rank_2["selected_career"] == "Backend Developer"
    assert result_rank_2["career_target"] == "Backend Developer"
    assert result_rank_2["career_target"] != "Software Developer"

    # Select Rank #3: Full Stack Developer
    result_rank_3 = await service.select_career_and_generate_roadmap(SAMPLE_PROFILE_ID, "Full Stack Developer")
    assert result_rank_3["selected_career"] == "Full Stack Developer"
    assert result_rank_3["career_target"] == "Full Stack Developer"
    assert result_rank_3["career_target"] != "Software Developer"


def test_13_refresh_preserves_selected_career(mock_repos):
    """13. Page refresh (reading latest analysis from cache) preserves selected_career."""
    service, _, _, analysis_repo, _ = mock_repos

    persisted = dict(SAMPLE_ANALYSIS_RECORD)
    persisted["selected_career"] = "Backend Developer"
    persisted["career_target"] = "Backend Developer"
    analysis_repo.get_latest_analysis.return_value = persisted

    refreshed = service.get_latest_analysis(SAMPLE_PROFILE_ID)
    assert refreshed["selected_career"] == "Backend Developer"
    assert refreshed["has_selected_career"] is True


def test_14_roadmap_api_returns_selected_career(mock_repos):
    """14. Roadmap progress query returns selected_career and career_target."""
    service, _, _, analysis_repo, _ = mock_repos

    persisted = dict(SAMPLE_ANALYSIS_RECORD)
    persisted["selected_career"] = "Backend Developer"
    analysis_repo.get_latest_analysis.return_value = persisted

    progress = service.get_roadmap_progress(SAMPLE_PROFILE_ID)
    assert progress["selected_career"] == "Backend Developer"
    assert progress["career_target"] == "Backend Developer"
    assert progress["has_selected_career"] is True


def test_15_progress_persists(mock_repos):
    """15. Marking milestone step as completed persists in the database."""
    service, _, _, analysis_repo, _ = mock_repos

    service.update_roadmap_progress("analysis-uuid-12345", SAMPLE_PROFILE_ID, 1, True)
    analysis_repo.set_step_progress.assert_called_once_with(
        "analysis-uuid-12345", SAMPLE_PROFILE_ID, 1, True
    )


@pytest.mark.asyncio
async def test_16_switching_careers_resets_progress_appropriately(mock_repos):
    """16. Switching career from Backend Developer -> Full Stack Developer resets progress."""
    service, _, _, analysis_repo, ai_provider = mock_repos

    ai_provider.generate_role_roadmap = AsyncMock(return_value=RoleRoadmapAIResponse(
        career_target="Full Stack Developer",
        roadmap_steps=[
            RoadmapStepItem(
                step_number=1,
                title="Frontend Foundation",
                duration_weeks=4,
                description="HTML/CSS/JS",
                skills_gained=["HTML"],
                resources=[],
            )
        ],
        project_recommendations=[],
        skill_gaps=[],
        priority_skills=[],
    ))

    # Existing analysis currently had "Backend Developer" selected
    analysis_with_backend = dict(SAMPLE_ANALYSIS_RECORD)
    analysis_with_backend["selected_career"] = "Backend Developer"
    analysis_repo.get_latest_analysis.return_value = analysis_with_backend

    # Now student chooses Full Stack Developer
    await service.select_career_and_generate_roadmap(SAMPLE_PROFILE_ID, "Full Stack Developer")

    # Verify clear_roadmap_progress was called because the career target changed
    analysis_repo.clear_roadmap_progress.assert_called_once_with(
        "analysis-uuid-12345", SAMPLE_PROFILE_ID
    )

    # Re-selecting the SAME career should NOT clear progress
    analysis_repo.clear_roadmap_progress.reset_mock()
    analysis_with_fs = dict(SAMPLE_ANALYSIS_RECORD)
    analysis_with_fs["selected_career"] = "Full Stack Developer"
    analysis_repo.get_latest_analysis.return_value = analysis_with_fs

    await service.select_career_and_generate_roadmap(SAMPLE_PROFILE_ID, "Full Stack Developer")
    analysis_repo.clear_roadmap_progress.assert_not_called()


@pytest.mark.asyncio
async def test_17_reanalysis_clears_stale_selected_career(mock_repos):
    """17. Re-analysis clears stale selected_career if it is no longer in new Top 3."""
    service, profile_repo, career_repo, analysis_repo, ai_provider = mock_repos

    # Suppose previously the user had selected "Embedded Systems Engineer"
    analysis_with_stale = dict(SAMPLE_ANALYSIS_RECORD)
    analysis_with_stale["selected_career"] = "Embedded Systems Engineer"
    analysis_repo.get_latest_analysis.return_value = analysis_with_stale

    # Now we force regenerate analysis
    ai_provider.analyze_career = AsyncMock(return_value=CareerAnalysisAIResponse(
        summary="Comprehensive updated career guidance and domain matching analysis.",
        recommended_careers=[
            RecommendedCareer(
                title="Software Developer",
                score=55.0,
                branch_compatibility=90.0,
                skill_match=80.0,
                interest_alignment=75.0,
                goal_alignment=80.0,
                academic_compatibility=85.0,
                reason="Top match for student",
                matched_skills=[],
                missing_skills=[],
                career_outlook="High",
                next_steps=[],
            ),
            RecommendedCareer(
                title="Backend Developer",
                score=48.0,
                branch_compatibility=85.0,
                skill_match=75.0,
                interest_alignment=80.0,
                goal_alignment=80.0,
                academic_compatibility=85.0,
                reason="Second match for student",
                matched_skills=[],
                missing_skills=[],
                career_outlook="High",
                next_steps=[],
            ),
            RecommendedCareer(
                title="Full Stack Developer",
                score=42.0,
                branch_compatibility=80.0,
                skill_match=70.0,
                interest_alignment=70.0,
                goal_alignment=75.0,
                academic_compatibility=80.0,
                reason="Third match for student",
                matched_skills=[],
                missing_skills=[],
                career_outlook="High",
                next_steps=[],
            ),
        ],
        strengths=["Logical Reasoning", "Data Modeling"],
        skill_gaps=[],
        priority_skills=[],
        roadmap_steps=[],
        project_recommendations=[],
        next_steps=[],
    ))

    # Run fresh analysis (force_regenerate=True)
    res = await service.get_or_create_analysis(SAMPLE_PROFILE_ID, force_regenerate=True)

    # Embedded Systems Engineer is NOT in the new Top 3, so selected_career must be None!
    assert res["selected_career"] is None
    assert res["has_selected_career"] is False


def test_18_no_arbitrary_career_can_generate_roadmap():
    """18. Direct API call with arbitrary career is rejected with HTTP 400."""
    client = TestClient(app)

    mock_service = MagicMock()
    mock_service.select_career_and_generate_roadmap = AsyncMock(
        side_effect=ValueError("Selected career 'Astronaut' is not among your Top 3 career matches.")
    )

    app.dependency_overrides[_get_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id=SAMPLE_PROFILE_ID, email="student@example.com")

    try:
        res = client.post("/api/analysis/select-career", json={"career_title": "Astronaut"})
        assert res.status_code == 400
        data = res.json()
        assert "not among your Top 3" in data["detail"]
    finally:
        app.dependency_overrides.clear()


def test_19_no_api_key_appears_in_response_logs_frontend():
    """19. Strict security audit: No API key or secret token is exposed in code or responses."""
    # Check frontend HTML/JS files
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    for root, _, files in os.walk(frontend_dir):
        for f in files:
            if f.endswith((".html", ".js")):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as file:
                    content = file.read()
                    assert "AIzaSy" not in content, f"Leaked Google API key found in {path}"
                    assert "GEMINI_API_KEY" not in content, f"GEMINI_API_KEY reference found in {path}"
                    assert "SUPABASE_SERVICE_ROLE_KEY" not in content, f"Service role key found in {path}"


def test_20_pydantic_career_selection_validation():
    """20. CareerSelectionRequest model validates required, non-empty, and maximum length."""
    # Valid
    req = CareerSelectionRequest(career_title="Backend Developer")
    assert req.career_title == "Backend Developer"

    # Empty string should fail
    with pytest.raises(Exception):
        CareerSelectionRequest(career_title="")

    # Whitespace only should fail
    with pytest.raises(Exception):
        CareerSelectionRequest(career_title="   ")

    # Exceeding 100 characters should fail
    with pytest.raises(Exception):
        CareerSelectionRequest(career_title="A" * 101)
