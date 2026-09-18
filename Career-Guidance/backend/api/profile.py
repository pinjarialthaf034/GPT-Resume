"""
CareerCompass AI — Profile API
CRUD for student profiles, skills, interests, and assessment without authentication.
"""
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from backend.deps import AuthenticatedUser, get_current_user, get_current_user_optional, get_service_supabase
from backend.models.common import APIResponse
from backend.models.profile import (
    AdaptiveNextRequest,
    AdaptiveNextResponse,
    AssessmentOptionModel,
    AssessmentQuestionModel,
    AssessmentSubmit,
    DomainSignal,
    ProfileCreate,
    ProfileUpdate,
)
from backend.repositories.profile_repo import ProfileRepository

router = APIRouter(prefix="/profile", tags=["Profile"])

VERSION_BUMP_FIELDS = {"branch", "semester", "cgpa", "career_goal", "assessment_language"}


def _get_repo(db: Client = Depends(get_service_supabase)) -> ProfileRepository:
    return ProfileRepository(db)


@router.get("", response_model=APIResponse)
async def get_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo: ProfileRepository = Depends(_get_repo),
):
    profile = repo.get_by_id(current_user.id)
    if not profile:
        return APIResponse(success=True, data=None, message="Profile not created yet")
    
    target_id = profile["id"]
    skills = repo.get_skills(target_id)
    interests = repo.get_interests(target_id)
    profile["skills"] = skills
    profile["interests"] = interests
    
    return APIResponse(success=True, data=profile)


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    body: ProfileCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo: ProfileRepository = Depends(_get_repo),
):
    target_id = current_user.id
    existing = repo.get_by_id(target_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already exists. Use PUT to update.",
        )
    
    email = current_user.email or body.email or ""
    profile = repo.create(
        target_id,
        email,
        body.model_dump(),
    )
    
    # Set skills and interests
    if body.skills:
        repo.set_skills(
            target_id,
            [s.model_dump() for s in body.skills],
        )
    if body.interests:
        # Convert interest names to IDs — look up by name
        interest_list = repo.list_all_interests()
        name_to_id = {i["name"].lower(): i["id"] for i in interest_list}
        ids = [name_to_id[n.lower()] for n in body.interests if n.lower() in name_to_id]
        repo.set_interests(target_id, ids)
    
    profile["skills"] = repo.get_skills(target_id)
    profile["interests"] = repo.get_interests(target_id)
    return APIResponse(success=True, message="Profile created", data=profile)


@router.put("", response_model=APIResponse)
async def update_profile(
    body: ProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo: ProfileRepository = Depends(_get_repo),
):
    existing = repo.get_by_id(current_user.id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create a profile first.",
        )
    
    target_id = existing["id"]
    update_data = body.model_dump(exclude_none=True)
    
    # Determine if we should bump profile_version
    bump = any(k in VERSION_BUMP_FIELDS for k in update_data.keys())
    if body.skills is not None or body.interests is not None:
        bump = True
    
    # Update core profile fields
    core_data = {k: v for k, v in update_data.items() if k not in ("skills", "interests")}
    if core_data:
        repo.update(target_id, core_data, bump_version=bump)
    elif bump:
        repo.update(
            target_id,
            {"updated_at": datetime.now(timezone.utc).isoformat()},
            bump_version=True,
        )
    
    # Update skills
    if body.skills is not None:
        repo.set_skills(
            target_id,
            [s.model_dump() for s in body.skills],
        )
    
    # Update interests
    if body.interests is not None:
        interest_list = repo.list_all_interests()
        name_to_id = {i["name"].lower(): i["id"] for i in interest_list}
        ids = [name_to_id[n.lower()] for n in body.interests if n.lower() in name_to_id]
        repo.set_interests(target_id, ids)
    
    updated = repo.get_by_id(target_id)
    if updated:
        updated["skills"] = repo.get_skills(target_id)
        updated["interests"] = repo.get_interests(target_id)
    
    return APIResponse(
        success=True,
        message="Profile updated" + (" — previous AI analysis is now outdated." if bump else ""),
        data=updated,
    )


# ---------------------------------------------------------------------------
# Reference data (public read)
# ---------------------------------------------------------------------------

@router.get("/skills/all", response_model=APIResponse)
async def list_skills(repo: ProfileRepository = Depends(_get_repo)):
    skills = repo.list_all_skills()
    return APIResponse(success=True, data=skills)


@router.get("/interests/all", response_model=APIResponse)
async def list_interests(repo: ProfileRepository = Depends(_get_repo)):
    interests = repo.list_all_interests()
    return APIResponse(success=True, data=interests)


@router.get("/assessment/questions", response_model=APIResponse)
async def get_assessment_questions(
    lang: str = Query("en", description="Language code: 'en' for English, 'te' for Telugu"),
    repo: ProfileRepository = Depends(_get_repo),
):
    questions = repo.list_assessment_questions(lang=lang)
    return APIResponse(success=True, data=questions)


@router.post("/assessment/next", response_model=APIResponse)
async def get_adaptive_next_question(
    body: AdaptiveNextRequest,
    lang: str = Query("en", description="Language code: 'en' for English, 'te' for Telugu"),
    repo: ProfileRepository = Depends(_get_repo),
):
    """
    Pure deterministic adaptive question selector.
    Evaluates current answers and returns the next question or transition / completion state.
    Strictly follows:
    - Steps 1-5: Broad discovery questions (zero domain names/labels)
    - Step 5 complete: Silent internal domain scoring + Neutral transition screen
    - Steps 6-8: Adaptive deep-dives targeted to top 3 domains
    - Step 9: Universal Work Style question
    - Step 10: Universal Problem Solving question
    - Step 10 complete: Discovery complete -> ready for submission & results.html
    """
    all_questions = repo.list_assessment_questions(lang=lang)
    if not all_questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No assessment questions available in database."
        )

    broad_questions = sorted(
        [q for q in all_questions if q.get("phase") == "broad"],
        key=lambda x: x.get("order_num", 99)
    )
    if len(broad_questions) < 5 and len(all_questions) >= 5:
        # Guarantee at least 5 broad discovery questions
        broad_questions = all_questions[:5]
        for idx, q in enumerate(broad_questions):
            q["phase"] = "broad"
            q["order_num"] = idx + 1

    deep_dive_questions = [
        q for q in all_questions if q.get("phase") == "deep_dive" or (q.get("order_num", 0) > 5 and q.get("phase") not in ("work_style", "problem_solving"))
    ]
    work_style_questions = [
        q for q in all_questions if q.get("phase") == "work_style" or q.get("domain") == "work_style"
    ]
    problem_solving_questions = [
        q for q in all_questions if q.get("phase") == "problem_solving" or q.get("domain") == "problem_solving"
    ]

    answered_ids = {str(a.question_id) for a in body.answers}
    broad_count = len(broad_questions)
    target_deep_count = min(3, len(deep_dive_questions)) if deep_dive_questions else 0
    total_steps = 10 if (work_style_questions or len(all_questions) >= 10) else (broad_count + target_deep_count)

    # 1. Broad Discovery Phase (Steps 1 to broad_count)
    unanswered_broad = [q for q in broad_questions if str(q["id"]) not in answered_ids]
    if len(body.answers) < broad_count and unanswered_broad:
        next_q = unanswered_broad[0]
        step = len(body.answers) + 1
        pct = round((step / total_steps) * 100, 1)
        return APIResponse(
            success=True,
            data=AdaptiveNextResponse(
                phase="broad",
                current_step=step,
                total_steps=total_steps,
                progress_percent=pct,
                question=AssessmentQuestionModel(**next_q),
                encouragement_message="Let's discover what kind of work and problems you naturally enjoy.",
            )
        )

    # Compute current domain signals silently
    signals = repo.calculate_assessment_signals([a.model_dump() for a in body.answers])
    top_domains = [DomainSignal(**d) for d in (signals.get("top_interest_domains") or [])]

    # 2. Silent Domain Analysis & Neutral Transition Screen
    answered_deep = [q for q in deep_dive_questions if str(q["id"]) in answered_ids]
    if len(answered_deep) == 0 and len(body.answers) == broad_count and not body.transition_acknowledged:
        return APIResponse(
            success=True,
            data=AdaptiveNextResponse(
                phase="transition",
                current_step=broad_count,
                total_steps=total_steps,
                progress_percent=50.0,
                top_domains=top_domains,
                encouragement_message="Nice! We're getting a better picture of the kinds of problems you enjoy. Your answers gave us a few clues. Let's explore them a little deeper.",
            )
        )

    # 3. Adaptive Deep Dive Phase (Steps 6, 7, 8 targeting top domains)
    if len(answered_deep) < target_deep_count:
        target_rank_index = len(answered_deep)
        target_domain_key = None
        if len(top_domains) > target_rank_index and top_domains[target_rank_index].signal > 0:
            target_domain_key = top_domains[target_rank_index].domain

        unanswered_deep = [q for q in deep_dive_questions if str(q["id"]) not in answered_ids]
        candidate_q = None

        if target_domain_key:
            matching_questions = [q for q in unanswered_deep if q.get("domain") == target_domain_key]
            if matching_questions:
                candidate_q = matching_questions[0]

        if not candidate_q:
            # Check other top domains
            for d in top_domains:
                matching_questions = [q for q in unanswered_deep if q.get("domain") == d.domain]
                if matching_questions:
                    candidate_q = matching_questions[0]
                    break

        if not candidate_q and unanswered_deep:
            candidate_q = unanswered_deep[0]

        if candidate_q:
            step = broad_count + len(answered_deep) + 1
            pct = round((step / total_steps) * 100, 1)
            return APIResponse(
                success=True,
                data=AdaptiveNextResponse(
                    phase="deep_dive",
                    current_step=step,
                    total_steps=total_steps,
                    progress_percent=pct,
                    question=AssessmentQuestionModel(**candidate_q),
                    top_domains=top_domains,
                    encouragement_message="Let's explore this kind of work a little deeper.",
                )
            )

    # 4. Universal Work Style (Step 9)
    unanswered_work_style = [q for q in work_style_questions if str(q["id"]) not in answered_ids]
    if unanswered_work_style:
        candidate_q = unanswered_work_style[0]
        step = len(body.answers) + 1
        pct = round((step / total_steps) * 100, 1)
        return APIResponse(
            success=True,
            data=AdaptiveNextResponse(
                phase="work_style",
                current_step=step,
                total_steps=total_steps,
                progress_percent=pct,
                question=AssessmentQuestionModel(**candidate_q),
                top_domains=top_domains,
                encouragement_message="Now let's see which way of working feels most natural to you.",
            )
        )

    # 5. Universal Problem Solving (Step 10)
    unanswered_problem_solving = [q for q in problem_solving_questions if str(q["id"]) not in answered_ids]
    if unanswered_problem_solving:
        candidate_q = unanswered_problem_solving[0]
        step = len(body.answers) + 1
        pct = round((step / total_steps) * 100, 1)
        return APIResponse(
            success=True,
            data=AdaptiveNextResponse(
                phase="problem_solving",
                current_step=step,
                total_steps=total_steps,
                progress_percent=pct,
                question=AssessmentQuestionModel(**candidate_q),
                top_domains=top_domains,
                encouragement_message="Finally, how do you naturally tackle unexpected challenges?",
            )
        )

    # 6. Fallback if any unanswered questions remain and under 10 answers
    remaining_unanswered = [q for q in all_questions if str(q["id"]) not in answered_ids]
    if remaining_unanswered and len(body.answers) < 10:
        candidate_q = remaining_unanswered[0]
        step = len(body.answers) + 1
        pct = round((step / total_steps) * 100, 1)
        return APIResponse(
            success=True,
            data=AdaptiveNextResponse(
                phase="deep_dive",
                current_step=step,
                total_steps=total_steps,
                progress_percent=pct,
                question=AssessmentQuestionModel(**candidate_q),
                top_domains=top_domains,
                encouragement_message="Exploring deeper into what excites you most.",
            )
        )

    # 7. Assessment Complete (Exactly 10 questions completed)
    return APIResponse(
        success=True,
        data=AdaptiveNextResponse(
            phase="complete",
            current_step=total_steps,
            total_steps=total_steps,
            progress_percent=100.0,
            top_domains=top_domains,
            is_complete=True,
            work_preferences=signals.get("work_preferences"),
            encouragement_message="Discovery complete! View your Career Analysis.",
        )
    )


@router.post("/assessment/submit", response_model=APIResponse)
async def submit_assessment(
    body: AssessmentSubmit,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo: ProfileRepository = Depends(_get_repo),
):
    target_id = current_user.id
    existing = repo.get_by_id(target_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please create a profile before submitting assessment.",
        )

    # Save answers
    repo.save_assessment_answers(
        target_id,
        [a.model_dump() for a in body.answers],
    )

    # Calculate and persist domain signals
    signals = repo.calculate_assessment_signals([a.model_dump() for a in body.answers])
    repo.save_assessment_signals(target_id, signals)

    # Assessment submission bumps profile version
    repo.update(
        target_id,
        {},
        bump_version=True,
    )
    return APIResponse(
        success=True,
        message="Assessment submitted. Profile updated — AI analysis will use new results.",
        data=signals,
    )

