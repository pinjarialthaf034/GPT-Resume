"""
CareerCompass AI — Profile Pydantic models.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Branch(str, Enum):
    CSE = "CSE"
    ECE = "ECE"
    EEE = "EEE"
    MECHANICAL = "MECHANICAL"
    CIVIL = "CIVIL"
    AUTOMOBILE = "AUTOMOBILE"
    IT = "IT"
    OTHER = "OTHER"


class ProficiencyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class StudentSkill(BaseModel):
    skill_id: Optional[str] = None
    name: Optional[str] = None
    skill_name: Optional[str] = None
    proficiency: ProficiencyLevel = ProficiencyLevel.BEGINNER


class ProfileCreate(BaseModel):
    id: Optional[str] = None
    email: Optional[str] = None
    full_name: str = Field(..., min_length=2, max_length=100)
    branch: Branch
    semester: int = Field(..., ge=1, le=6)
    cgpa: Optional[float] = Field(None, ge=0.0, le=10.0)
    career_goal: Optional[str] = Field(None, max_length=500)
    assessment_language: Optional[str] = Field("en", description="Supported: 'en', 'te'")
    skills: Optional[List[StudentSkill]] = Field(default_factory=list)
    interests: Optional[List[str]] = Field(default_factory=list)


class ProfileUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    branch: Optional[Branch] = None
    semester: Optional[int] = Field(None, ge=1, le=6)
    cgpa: Optional[float] = Field(None, ge=0.0, le=10.0)
    career_goal: Optional[str] = Field(None, max_length=500)
    assessment_language: Optional[str] = Field(None, description="Supported: 'en', 'te'")
    skills: Optional[List[StudentSkill]] = None
    interests: Optional[List[str]] = None
    assessment_signals: Optional[Dict[str, Any]] = None


class ProfileResponse(BaseModel):
    id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[int] = None
    cgpa: Optional[float] = None
    career_goal: Optional[str] = None
    assessment_language: Optional[str] = "en"
    profile_version: int = 1
    is_admin: bool = False
    skills: Optional[List[dict]] = None
    interests: Optional[List[str]] = None
    assessment_signals: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AssessmentAnswer(BaseModel):
    question_id: str
    option_id: str


class AssessmentSubmit(BaseModel):
    answers: List[AssessmentAnswer] = Field(..., min_length=1)


class DomainSignal(BaseModel):
    domain: str
    domain_label: str
    signal: float
    level: str = "Moderate"
    icon: Optional[str] = None


class AssessmentOptionModel(BaseModel):
    id: str
    option_text: str
    career_weight: Optional[Dict[str, Any]] = Field(default_factory=dict)
    domain_weight: Optional[Dict[str, Any]] = Field(default_factory=dict)


class AssessmentQuestionModel(BaseModel):
    id: str
    question_text: str
    category: str = "General"
    phase: str = "broad"
    domain: str = "general"
    order_num: int = 1
    assessment_options: Optional[List[AssessmentOptionModel]] = Field(default_factory=list)


class AdaptiveNextRequest(BaseModel):
    answers: List[AssessmentAnswer] = Field(default_factory=list)
    transition_acknowledged: bool = False


class AdaptiveNextResponse(BaseModel):
    phase: str  # 'broad', 'transition', 'deep_dive', 'complete'
    current_step: int
    total_steps: int
    progress_percent: float
    question: Optional[AssessmentQuestionModel] = None
    top_domains: Optional[List[DomainSignal]] = None
    encouragement_message: Optional[str] = None
    is_complete: bool = False
    work_preferences: Optional[Dict[str, Any]] = None

