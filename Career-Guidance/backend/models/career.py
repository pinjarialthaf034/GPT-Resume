"""
CareerCompass AI — Career & Analysis Pydantic models.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Career models
# ---------------------------------------------------------------------------

class CareerBase(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    branches: Optional[List[str]] = None
    min_cgpa: Optional[float] = None
    avg_salary_lpa: Optional[float] = None
    job_growth: Optional[str] = None
    industry: Optional[str] = None


class CareerDetail(CareerBase):
    required_skills: Optional[List[dict]] = None
    related_projects: Optional[List[dict]] = None
    roadmap_overview: Optional[str] = None


class CareerMatchResult(BaseModel):
    career_id: str
    title: str
    score: float
    score_breakdown: dict
    matched_skills: List[str]
    missing_skills: List[str]


# ---------------------------------------------------------------------------
# Analysis models
# ---------------------------------------------------------------------------

class AnalysisTrigger(BaseModel):
    force_regenerate: bool = False


class CareerSelectionRequest(BaseModel):
    career_title: str = Field(..., min_length=1, max_length=100, description="Title of career selected from Top 3 matches")

    @field_validator("career_title")
    @classmethod
    def validate_career_title(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("career_title cannot be empty or whitespace only")
        return trimmed


class RoadmapStep(BaseModel):
    step_number: int
    title: str
    description: str
    duration_weeks: Optional[int] = None
    resources: Optional[List[str]] = None
    skills_gained: Optional[List[str]] = None


class SkillGap(BaseModel):
    skill_name: str
    current_level: Optional[str] = None
    required_level: str
    priority: str  # high / medium / low


class CareerAnalysisResponse(BaseModel):
    id: str
    profile_id: str
    profile_version: int
    model_name: str
    prompt_version: str
    generated_at: datetime
    is_cached: bool = False
    is_fallback: bool = False
    selected_career: Optional[str] = None
    has_selected_career: bool = False
    career_target: Optional[str] = None

    # AI-generated content
    summary: str
    recommended_careers: List[CareerMatchResult]
    strengths: List[str]
    skill_gaps: List[SkillGap]
    priority_skills: List[str]
    roadmap_steps: List[RoadmapStep]
    project_recommendations: List[dict]
    next_steps: List[str]


# ---------------------------------------------------------------------------
# Roadmap progress models
# ---------------------------------------------------------------------------

class RoadmapProgressUpdate(BaseModel):
    step_number: int = Field(..., ge=1)
    completed: bool


class RoadmapProgressResponse(BaseModel):
    analysis_id: str
    selected_career: Optional[str] = None
    has_selected_career: bool = False
    career_target: Optional[str] = None
    is_fallback: bool = False
    completed_steps: List[int]
    total_steps: int
    percent_complete: float


# ---------------------------------------------------------------------------
# Chat models
# ---------------------------------------------------------------------------

class ChatMessageCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str  # user / assistant
    content: str
    created_at: datetime
    is_fallback: Optional[bool] = False


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatMessageResponse]


# ---------------------------------------------------------------------------
# Resume models
# ---------------------------------------------------------------------------

class ResumeAnalysisResponse(BaseModel):
    id: str
    profile_id: str
    guidance_score: int  # 0-100
    strengths: List[str]
    missing_skills: List[str]
    formatting_feedback: List[str]
    project_suggestions: List[str]
    skill_alignment: str
    improvement_suggestions: List[str]
    analyzed_at: datetime
