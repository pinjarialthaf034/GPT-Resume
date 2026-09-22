"""
CareerCompass AI — Career Analysis Service
Orchestrates: career matching → cache check → Gemini (if needed) → save → return.
ONE Gemini call per analysis. Caches results by profile_version + prompt_version.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

import uuid

from backend.ai.errors import (
    GeminiConfigError,
    GeminiTransientError,
    classify_gemini_error,
)
from backend.ai.gemini_provider import GeminiProvider
from backend.ai.prompts import CAREER_ANALYSIS_PROMPT_VERSION
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.career_repo import CareerRepository
from backend.repositories.profile_repo import ProfileRepository
from backend.services.ai_context_builder import (
    build_student_ai_context,
    compute_student_context_fingerprint,
)
from backend.services.matching_engine import (
    compute_career_matches,
    generate_fallback_roadmap,
)

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(
        self,
        profile_repo: ProfileRepository,
        career_repo: CareerRepository,
        analysis_repo: AnalysisRepository,
        ai_provider: GeminiProvider,
    ):
        self._profile_repo = profile_repo
        self._career_repo = career_repo
        self._analysis_repo = analysis_repo
        self._ai = ai_provider

    async def get_or_create_analysis(
        self,
        profile_id: str,
        force_regenerate: bool = False,
    ) -> Dict:
        """
        Main entry point for AI Career Intelligence.
        
        Flow:
          1. Build multi-signal student AI context (profile, skills, interests, assessment, resume)
          2. Compute deterministic SHA-256 fingerprint from student inputs
          3. Check cache (profile_version + prompt_version:fingerprint)
          4. If cached and not forced → return cached (0 Gemini quota consumed)
          5. Call Gemini ONCE with complete multi-signal student context
          6. Validate strictly via Pydantic + save to DB → return
          7. If Gemini fails after all keys rotate, provide real deterministic fallback and persist it
        """
        # Step 1: Assemble full multi-signal student context
        student_context = await asyncio.to_thread(
            build_student_ai_context, self._profile_repo, self._analysis_repo, profile_id
        )
        profile_version = student_context.get("profile_version", 1)

        # Step 2: Compute deterministic fingerprint
        fingerprint = compute_student_context_fingerprint(student_context)
        cache_prompt_version = f"{CAREER_ANALYSIS_PROMPT_VERSION}:{fingerprint[:16]}"

        # Step 3: Check cache
        if not force_regenerate:
            cached = await asyncio.to_thread(
                self._analysis_repo.get_valid_cached_analysis,
                profile_id,
                profile_version,
                cache_prompt_version,
            )
            if cached:
                logger.info(f"Returning fingerprint-cached analysis for profile {profile_id}")
                cached["is_cached"] = True
                cached["is_fallback"] = False
                cached["has_selected_career"] = bool(cached.get("selected_career"))
                cached["career_target"] = cached.get("selected_career")
                return cached

        # Step 4: Fetch reference career catalog (for domain guidance, not restriction)
        careers_with_skills = await asyncio.to_thread(self._career_repo.get_careers_with_skills) or []

        # Check previous analysis to preserve valid selected career or clear stale selection
        prev_analysis = await asyncio.to_thread(self._analysis_repo.get_latest_analysis, profile_id)
        prev_selected = prev_analysis.get("selected_career") if prev_analysis else None

        # Step 5: Call Gemini for genuine AI career intelligence with backend key rotation
        logger.info(
            f"Calling Gemini for profile {profile_id} (fingerprint={fingerprint[:8]}...)"
        )
        try:
            ai_result = await self._ai.analyze_career(student_context, careers_with_skills)
        except GeminiConfigError as e:
            # Do NOT silently convert configuration errors into a generic fallback
            logger.error(f"Gemini configuration error for profile {profile_id}: {e}")
            raise
        except (TypeError, KeyError, AttributeError, IndexError) as e:
            # Programming bugs must not be silently swallowed
            logger.error(f"Programming error during career analysis for profile {profile_id}: {e}", exc_info=True)
            raise
        except Exception as e:
            category = classify_gemini_error(e)
            if category in ("missing_key", "model_unavailable", "authentication_error"):
                logger.error(f"Gemini configuration error diagnosed for profile {profile_id}: {e}")
                raise GeminiConfigError(str(e))

            logger.warning(
                f"Gemini career analysis unavailable across configured keys for profile {profile_id}: {e}. "
                "Engaging transparent rule-based fallback."
            )
            fallback_data = self._build_transparent_fallback(
                profile_id, student_context, careers_with_skills, cache_prompt_version, str(e), prev_selected=prev_selected
            )

            # Persist fallback analysis to DB so roadmap.html and roadmap_progress work identically
            try:
                saved = await asyncio.to_thread(
                    self._analysis_repo.save_analysis, profile_id, profile_version, fallback_data
                )
                if isinstance(saved, dict) and saved.get("id"):
                    fallback_data["id"] = saved["id"]
                elif not fallback_data.get("id"):
                    fallback_data["id"] = str(uuid.uuid4())
            except Exception as save_err:
                logger.warning(f"Could not persist fallback analysis to database: {save_err}")
                if not fallback_data.get("id"):
                    fallback_data["id"] = str(uuid.uuid4())

            fallback_data["is_cached"] = False
            fallback_data["is_fallback"] = True
            return fallback_data

        # Step 6: Save validated AI analysis to Supabase
        recs = [c.model_dump() for c in ai_result.recommended_careers]
        top_3_titles = [c.get("title", "").strip().lower() for c in recs[:3]]
        selected_career = prev_selected if (prev_selected and prev_selected.strip().lower() in top_3_titles) else None

        save_data = {
            "model_name": self._ai.model_name,
            "prompt_version": cache_prompt_version,
            "summary": ai_result.summary,
            "recommended_careers": recs,
            "strengths": ai_result.strengths,
            "skill_gaps": [sg.model_dump() for sg in ai_result.skill_gaps],
            "priority_skills": ai_result.priority_skills,
            "roadmap_steps": [rs.model_dump() for rs in ai_result.roadmap_steps],
            "project_recommendations": [pr.model_dump() for pr in ai_result.project_recommendations],
            "next_steps": ai_result.next_steps,
            "selected_career": selected_career,
        }
        
        saved = await asyncio.to_thread(
            self._analysis_repo.save_analysis, profile_id, profile_version, save_data
        )
        saved["is_cached"] = False
        saved["is_fallback"] = False
        saved["selected_career"] = selected_career
        saved["has_selected_career"] = bool(selected_career)
        saved["career_target"] = selected_career
        logger.info(f"AI Analysis saved for profile {profile_id}, id={saved.get('id')}")
        return saved

    def _build_transparent_fallback(
        self,
        profile_id: str,
        student_context: Dict,
        careers_with_skills: List[Dict],
        cache_prompt_version: str,
        error_reason: str,
        prev_selected: Optional[str] = None,
        target_selected_career: Optional[Dict] = None,
    ) -> Dict:
        """
        Graceful non-AI fallback when Gemini is unavailable across all configured keys.
        Uses existing deterministic matching engine and generates a real, structured roadmap.
        Clearly marked as 'Preliminary Rule-Based Matches' so users know AI personalization was unavailable.
        """
        matches = []
        if careers_with_skills:
            matches = compute_career_matches(student_context, careers_with_skills, top_n=3)

        branch = student_context.get("branch") or "Engineering"
        recommended = []
        for m in matches:
            breakdown = m.get("score_breakdown") or {}
            recommended.append({
                "career_id": m.get("career_id") or "",
                "title": m.get("title", "Career Match"),
                "score": float(m.get("score", 0.0)),
                "branch_compatibility": min(100.0, float(breakdown.get("branch", 0.0)) * (100.0 / 30.0)),
                "skill_match": min(100.0, float(breakdown.get("skills", 0.0)) * (100.0 / 35.0)),
                "interest_alignment": min(100.0, float(breakdown.get("interests", 0.0)) * (100.0 / 15.0)),
                "goal_alignment": min(100.0, float(breakdown.get("career_goal", 0.0)) * (100.0 / 10.0)),
                "academic_compatibility": min(100.0, float(breakdown.get("cgpa", 0.0)) * (100.0 / 10.0)),
                "reason": f"Calculated via curriculum matching rules for {branch} students.",
                "matched_skills": m.get("matched_skills", []),
                "missing_skills": m.get("missing_skills", []),
                "career_outlook": "Standard industry demand",
                "next_steps": ["Retry AI analysis for personalized Gemini insights"],
            })

        # Determine target career for roadmap
        top_3_titles = [c.get("title", "").strip().lower() for c in recommended[:3]]
        selected_career_title = None
        if target_selected_career:
            selected_career_title = target_selected_career.get("title")
        elif prev_selected and prev_selected.strip().lower() in top_3_titles:
            selected_career_title = prev_selected

        target_career_obj = None
        if target_selected_career:
            target_career_obj = target_selected_career
        elif selected_career_title:
            for c in recommended:
                if c.get("title", "").strip().lower() == selected_career_title.strip().lower():
                    target_career_obj = c
                    break

        if not target_career_obj:
            target_career_obj = recommended[0] if recommended else {
                "title": f"{branch} Specialist",
                "matched_skills": [],
                "missing_skills": [],
            }

        # Try to resolve career projects if career_id is present
        career_projects = None
        target_id = target_career_obj.get("career_id") or target_career_obj.get("id")
        if target_id:
            try:
                career_details = self._career_repo.get_career_by_id(target_id)
                if career_details and career_details.get("career_projects"):
                    career_projects = [
                        cp["projects"] for cp in career_details["career_projects"] if cp.get("projects")
                    ]
            except Exception:
                pass

        roadmap_bundle = generate_fallback_roadmap(
            target_career=target_career_obj,
            student_context=student_context,
            career_catalog=careers_with_skills,
            career_projects=career_projects,
        )

        effective_title = selected_career_title

        return {
            "id": None,
            "profile_id": profile_id,
            "profile_version": student_context.get("profile_version", 1),
            "model_name": "rule-engine-fallback",
            "prompt_version": cache_prompt_version,
            "summary": (
                "Preliminary Rule-Based Matches: Gemini AI is temporarily offline or experiencing high traffic. "
                "The matches below and structured learning roadmap are generated using deterministic curriculum rules. "
                "Please retry in a moment to receive your complete personalized Gemini AI analysis."
            ),
            "recommended_careers": recommended,
            "strengths": [f"Diploma student in {branch}"] + (
                [f"Demonstrated foundation in {', '.join(target_career_obj['matched_skills'][:2])}"]
                if target_career_obj.get("matched_skills")
                else []
            ),
            "skill_gaps": roadmap_bundle["skill_gaps"],
            "priority_skills": roadmap_bundle["priority_skills"],
            "roadmap_steps": roadmap_bundle["roadmap_steps"],
            "project_recommendations": roadmap_bundle["project_recommendations"],
            "next_steps": [
                f"Begin Step 1: {roadmap_bundle['roadmap_steps'][0]['title']}",
                "Review required skills on the Interactive Roadmap page",
                "Click 'Re-Analyze' at any time to run Gemini AI personalization",
            ],
            "selected_career": selected_career_title,
            "has_selected_career": bool(selected_career_title),
            "career_target": effective_title,
            "is_cached": False,
            "is_fallback": True,
            "error_detail": error_reason,
        }

    async def select_career_and_generate_roadmap(
        self,
        profile_id: str,
        career_title: str,
    ) -> Dict:
        """
        Validates student's selected career against their latest Top 3 matches,
        generates a role-specific learning roadmap specifically for that selected role
        (via Gemini AI or deterministic fallback), and persists the selection.
        """
        if not career_title or not career_title.strip():
            raise ValueError("Career title is required.")

        clean_title = career_title.strip()

        # Step 1: Retrieve latest analysis for this profile
        analysis = await asyncio.to_thread(self._analysis_repo.get_latest_analysis, profile_id)
        if not analysis:
            raise ValueError("No existing career analysis found. Please generate a career analysis first.")

        # Step 2: Validate that career exists strictly in Top 3 matches
        recommended = analysis.get("recommended_careers") or []
        top_3 = recommended[:3]
        if not top_3:
            raise ValueError("No career matches found in your analysis. Please run career analysis first.")

        selected_career_obj = None
        for c in top_3:
            t = c.get("title") if isinstance(c, dict) else getattr(c, "title", None)
            if t and t.strip().lower() == clean_title.lower():
                selected_career_obj = c if isinstance(c, dict) else c.model_dump()
                break

        if not selected_career_obj:
            top_titles = [c.get("title") if isinstance(c, dict) else getattr(c, "title", "") for c in top_3]
            raise ValueError(
                f"Selected career '{clean_title}' is not among your Top 3 matches: {', '.join(top_titles)}. "
                "Please choose one of your recommended careers."
            )

        canonical_title = selected_career_obj.get("title")
        analysis_id = analysis.get("id")
        previous_selected = analysis.get("selected_career")
        career_changed = bool(previous_selected and previous_selected.strip().lower() != canonical_title.lower())

        # Step 3: Build complete student context
        student_context = await asyncio.to_thread(
            build_student_ai_context, self._profile_repo, self._analysis_repo, profile_id
        )

        careers_catalog = await asyncio.to_thread(self._career_repo.get_careers_with_skills) or []

        # Step 4: Generate role-specific roadmap (Gemini if available, fallback otherwise)
        roadmap_bundle = None
        used_model = self._ai.model_name
        is_fallback = False

        try:
            logger.info(f"Generating Gemini role-specific roadmap for '{canonical_title}' (profile={profile_id})")
            ai_roadmap = await self._ai.generate_role_roadmap(student_context, selected_career_obj)
            roadmap_bundle = {
                "career_target": ai_roadmap.career_target,
                "roadmap_steps": [rs.model_dump() for rs in ai_roadmap.roadmap_steps],
                "project_recommendations": [pr.model_dump() for pr in ai_roadmap.project_recommendations],
                "skill_gaps": [sg.model_dump() for sg in ai_roadmap.skill_gaps],
                "priority_skills": ai_roadmap.priority_skills,
            }
        except GeminiConfigError as e:
            logger.error(f"Gemini configuration error during role roadmap generation for '{canonical_title}': {e}")
            raise
        except (TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Programming error during role roadmap generation: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.warning(
                f"Gemini role roadmap generation unavailable across keys for '{canonical_title}': {e}. "
                "Engaging role-specific deterministic fallback roadmap."
            )
            is_fallback = True
            used_model = "rule-engine-fallback"

            # Resolve projects for this specific career if possible
            career_projects = None
            career_id = selected_career_obj.get("career_id") or selected_career_obj.get("id")
            if career_id:
                try:
                    career_details = await asyncio.to_thread(self._career_repo.get_career_by_id, career_id)
                    if career_details and career_details.get("career_projects"):
                        career_projects = [
                            cp["projects"] for cp in career_details["career_projects"] if cp.get("projects")
                        ]
                except Exception:
                    pass

            roadmap_bundle = generate_fallback_roadmap(
                target_career=selected_career_obj,
                student_context=student_context,
                career_catalog=careers_catalog,
                career_projects=career_projects,
            )

        # Step 5: Persist the selected career and role-specific roadmap to DB
        updated = await asyncio.to_thread(
            self._analysis_repo.update_analysis_selected_career,
            analysis_id=analysis_id,
            profile_id=profile_id,
            selected_career=canonical_title,
            roadmap_bundle=roadmap_bundle,
            model_name=used_model,
        )

        # Step 6: If career changed, reset roadmap progress for the newly selected career
        if career_changed:
            logger.info(
                f"Career target changed from '{previous_selected}' to '{canonical_title}' for profile {profile_id}. "
                "Resetting roadmap progress."
            )
            await asyncio.to_thread(self._analysis_repo.clear_roadmap_progress, analysis_id, profile_id)

        updated["is_fallback"] = is_fallback
        updated["selected_career"] = canonical_title
        updated["has_selected_career"] = True
        updated["career_target"] = canonical_title
        return updated

    def get_latest_analysis(self, profile_id: str) -> Optional[Dict]:
        """Returns the most recent analysis (any version) — used for dashboard."""
        res = self._analysis_repo.get_latest_analysis(profile_id)
        if res:
            res["has_selected_career"] = bool(res.get("selected_career"))
            res["career_target"] = res.get("selected_career")
        return res

    def update_roadmap_progress(
        self,
        analysis_id: str,
        profile_id: str,
        step_number: int,
        completed: bool,
    ) -> Dict:
        """Marks a roadmap step complete/incomplete."""
        # Validate analysis belongs to profile
        analysis = self._analysis_repo.get_latest_analysis(profile_id)
        if not analysis or analysis.get("id") != analysis_id:
            raise ValueError("Analysis not found or access denied")
        
        self._analysis_repo.set_step_progress(
            analysis_id, profile_id, step_number, completed
        )
        
        completed_steps = self._analysis_repo.get_roadmap_progress(analysis_id, profile_id)
        total_steps = len(analysis.get("roadmap_steps") or [])
        
        return {
            "analysis_id": analysis_id,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "percent_complete": round(len(completed_steps) / total_steps * 100, 1) if total_steps else 0,
        }

    def get_roadmap_progress(self, profile_id: str) -> Dict:
        """Gets roadmap progress for the latest analysis."""
        analysis = self._analysis_repo.get_latest_analysis(profile_id)
        if not analysis:
            return {
                "analysis_id": None,
                "career_target": None,
                "selected_career": None,
                "has_selected_career": False,
                "completed_steps": [],
                "total_steps": 0,
                "percent_complete": 0,
                "roadmap_steps": [],
                "project_recommendations": [],
                "is_fallback": False,
            }
        
        analysis_id = analysis["id"]
        completed_steps = self._analysis_repo.get_roadmap_progress(analysis_id, profile_id)
        total_steps = len(analysis.get("roadmap_steps") or [])
        recommended = analysis.get("recommended_careers") or []

        selected_career = analysis.get("selected_career")
        if not selected_career:
            for c in recommended:
                if isinstance(c, dict) and c.get("is_selected"):
                    selected_career = c.get("title")
                    break

        has_selected = bool(selected_career)
        career_target = selected_career
        
        return {
            "analysis_id": analysis_id,
            "career_target": career_target,
            "selected_career": selected_career,
            "has_selected_career": has_selected,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "percent_complete": round(len(completed_steps) / total_steps * 100, 1) if total_steps else 0,
            "roadmap_steps": analysis.get("roadmap_steps", []),
            "project_recommendations": analysis.get("project_recommendations", []),
            "is_fallback": analysis.get("model_name") == "rule-engine-fallback",
        }

    def _get_enriched_profile(self, profile_id: str) -> Optional[Dict]:
        """Fetches profile + skills + interests as a single dict."""
        profile = self._profile_repo.get_by_id(profile_id)
        if not profile:
            return None
        
        skills = self._profile_repo.get_skills(profile_id)
        interests = self._profile_repo.get_interests(profile_id)
        
        profile["skills"] = skills
        profile["interests"] = interests
        return profile
