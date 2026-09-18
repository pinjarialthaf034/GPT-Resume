"""
CareerCompass AI — Student AI Context Builder
Assembles rich, multi-signal student context for Gemini career intelligence.
Synthesizes:
  - Profile & Academic Info (branch, semester, CGPA, career goal)
  - Technical Skills & Proficiencies
  - Student Interests
  - Assessment Responses & Signals
  - Resume Intelligence (if uploaded)
Also computes deterministic SHA-256 fingerprint for precise cache invalidation.
"""
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.profile_repo import ProfileRepository

logger = logging.getLogger(__name__)


def build_student_ai_context(
    profile_repo: ProfileRepository,
    analysis_repo: AnalysisRepository,
    profile_id: str,
) -> Dict[str, Any]:
    """
    Assembles complete student context across all data stores.
    Returns normalized dictionary representing the student's holistic state.
    """
    profile = profile_repo.get_by_id(profile_id)
    if not profile:
        raise ValueError(f"Profile {profile_id} not found")

    # 1. Skills
    raw_skills = profile_repo.get_skills(profile_id)
    skills: List[Dict[str, str]] = []
    for s in raw_skills:
        skill_meta = s.get("skills") or {}
        name = s.get("name") or s.get("skill_name") or skill_meta.get("name") or ""
        category = s.get("category") or skill_meta.get("category") or "Technical"
        proficiency = s.get("proficiency") or "beginner"
        if name:
            skills.append({
                "name": name,
                "proficiency": proficiency.lower(),
                "category": category,
            })

    # Sort skills for canonical stability
    skills.sort(key=lambda x: x["name"].lower())

    # 2. Interests
    interests = profile_repo.get_interests(profile_id)
    sorted_interests = sorted([str(i) for i in interests if i])

    # 3. Assessment Responses & Signals
    raw_assessment = profile_repo.get_assessment_answers(profile_id)
    assessment: List[Dict[str, Any]] = []
    for a in raw_assessment:
        q_text = a.get("question_text") or a.get("question") or ""
        category = a.get("category") or "General"
        opt_text = a.get("option_text") or a.get("selected_option") or ""
        weight = a.get("career_weight")
        assessment.append({
            "question_id": str(a.get("question_id") or ""),
            "question_text": q_text,
            "category": category,
            "phase": a.get("phase", "broad"),
            "domain": a.get("domain", "general"),
            "selected_option": opt_text,
            "career_weight": weight,
        })
    assessment.sort(key=lambda x: x["question_id"])

    # Computed assessment signals (top domains, work style)
    assessment_signals = profile.get("assessment_signals")
    if (not assessment_signals or not isinstance(assessment_signals, dict)) and raw_assessment:
        assessment_signals = profile_repo.calculate_assessment_signals(raw_assessment)

    # 4. Resume Intelligence (if available)
    latest_resume = analysis_repo.get_latest_resume_analysis(profile_id)
    resume_context: Optional[Dict[str, Any]] = None
    if latest_resume:
        resume_context = {
            "resume_id": str(latest_resume.get("id") or ""),
            "guidance_score": latest_resume.get("guidance_score"),
            "strengths": latest_resume.get("strengths") or [],
            "missing_skills": latest_resume.get("missing_skills") or [],
            "skill_alignment": latest_resume.get("skill_alignment") or "",
            "project_suggestions": latest_resume.get("project_suggestions") or [],
        }

    context = {
        "profile_id": str(profile_id),
        "profile_version": int(profile.get("profile_version") or 1),
        "full_name": profile.get("full_name") or "Student",
        "branch": profile.get("branch") or "",
        "semester": profile.get("semester"),
        "cgpa": float(profile["cgpa"]) if profile.get("cgpa") is not None else None,
        "career_goal": profile.get("career_goal") or "",
        "skills": skills,
        "interests": sorted_interests,
        "assessment": assessment,
        "assessment_signals": assessment_signals or {},
        "resume": resume_context,
    }

    return context


def compute_student_context_fingerprint(context: Dict[str, Any]) -> str:
    """
    Computes a deterministic SHA-256 fingerprint from the normalized student inputs.
    Excludes profile_id or timestamps to reflect ONLY student content that affects career fit.
    """
    normalized_payload = {
        "branch": (context.get("branch") or "").strip().upper(),
        "semester": context.get("semester"),
        "cgpa": round(context.get("cgpa"), 2) if context.get("cgpa") is not None else None,
        "career_goal": (context.get("career_goal") or "").strip().lower(),
        "skills": [
            {
                "name": s["name"].strip().lower(),
                "proficiency": s["proficiency"].strip().lower(),
            }
            for s in (context.get("skills") or [])
        ],
        "interests": [i.strip().lower() for i in (context.get("interests") or [])],
        "assessment": [
            {
                "q": a.get("question_id") or a.get("question_text", ""),
                "opt": a.get("selected_option") or a.get("option_id", ""),
            }
            for a in (context.get("assessment") or [])
        ],
        "resume_id": (context.get("resume") or {}).get("resume_id") if context.get("resume") else None,
    }

    serialized = json.dumps(normalized_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
