"""
CareerCompass AI — Analysis Repository
Stores and retrieves AI career analyses and roadmap progress.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from supabase import Client

logger = logging.getLogger(__name__)


class AnalysisRepository:
    def __init__(self, db: Client):
        self._db = db

    # -----------------------------------------------------------------------
    # Career Analysis
    # -----------------------------------------------------------------------

    def _normalize_analysis(self, analysis: Optional[Dict]) -> Optional[Dict]:
        if not analysis or not isinstance(analysis, dict):
            return analysis
        analysis = dict(analysis)
        selected = analysis.get("selected_career")
        if not selected:
            recs = analysis.get("recommended_careers") or []
            for c in recs:
                if isinstance(c, dict) and c.get("is_selected"):
                    selected = c.get("title")
                    break
        analysis["selected_career"] = selected
        analysis["has_selected_career"] = bool(selected)
        analysis["career_target"] = selected
        return analysis

    def get_latest_analysis(self, profile_id: str) -> Optional[Dict]:
        """Gets the most recent analysis for a profile."""
        result = (
            self._db.table("career_analyses")
            .select("*")
            .eq("profile_id", profile_id)
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )
        data = result.data[0] if result.data else None
        return self._normalize_analysis(data)

    def get_valid_cached_analysis(
        self, profile_id: str, profile_version: int, prompt_version: str
    ) -> Optional[Dict]:
        """
        Returns a cached analysis if it matches the current profile_version and prompt_version.
        This prevents unnecessary Gemini calls.
        """
        result = (
            self._db.table("career_analyses")
            .select("*")
            .eq("profile_id", profile_id)
            .eq("profile_version", profile_version)
            .eq("prompt_version", prompt_version)
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )
        data = result.data[0] if result.data else None
        return self._normalize_analysis(data)

    def save_analysis(self, profile_id: str, profile_version: int, data: Dict) -> Dict:
        """Saves a new analysis result to Supabase."""
        selected_career = data.get("selected_career")
        recommended = list(data.get("recommended_careers") or [])
        if selected_career:
            for c in recommended:
                if isinstance(c, dict):
                    c["is_selected"] = (c.get("title", "").strip().lower() == selected_career.strip().lower())

        payload = {
            "profile_id": profile_id,
            "profile_version": profile_version,
            "model_name": data.get("model_name"),
            "prompt_version": data.get("prompt_version"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            # AI-generated content stored as JSONB
            "summary": data.get("summary"),
            "recommended_careers": recommended,
            "strengths": data.get("strengths"),
            "skill_gaps": data.get("skill_gaps"),
            "priority_skills": data.get("priority_skills"),
            "roadmap_steps": data.get("roadmap_steps"),
            "project_recommendations": data.get("project_recommendations"),
            "next_steps": data.get("next_steps"),
            "selected_career": selected_career,
        }
        try:
            result = self._db.table("career_analyses").insert(payload).execute()
        except Exception as e:
            if "selected_career" in str(e) or "PGRST204" in str(e):
                payload_without = {k: v for k, v in payload.items() if k != "selected_career"}
                result = self._db.table("career_analyses").insert(payload_without).execute()
            else:
                raise

        saved = result.data[0] if result.data else {}
        if saved and selected_career:
            saved["selected_career"] = selected_career
        return self._normalize_analysis(saved)

    def update_analysis_selected_career(
        self,
        analysis_id: str,
        profile_id: str,
        selected_career: str,
        roadmap_bundle: Dict,
        model_name: Optional[str] = None,
    ) -> Dict:
        """Updates the selected career and role-specific roadmap for an analysis."""
        analysis = (
            self._db.table("career_analyses")
            .select("*")
            .eq("id", analysis_id)
            .eq("profile_id", profile_id)
            .limit(1)
            .execute()
        )
        rows = analysis.data if analysis else []
        row = rows[0] if rows else {}

        recommended = list(row.get("recommended_careers") or [])
        for c in recommended:
            if isinstance(c, dict):
                c["is_selected"] = (c.get("title", "").strip().lower() == selected_career.strip().lower())

        update_payload = {
            "selected_career": selected_career,
            "recommended_careers": recommended,
            "roadmap_steps": roadmap_bundle.get("roadmap_steps") or [],
            "project_recommendations": roadmap_bundle.get("project_recommendations") or [],
            "skill_gaps": roadmap_bundle.get("skill_gaps") or [],
            "priority_skills": roadmap_bundle.get("priority_skills") or [],
        }
        if model_name:
            update_payload["model_name"] = model_name

        try:
            result = (
                self._db.table("career_analyses")
                .update(update_payload)
                .eq("id", analysis_id)
                .execute()
            )
        except Exception as e:
            if "selected_career" in str(e) or "PGRST204" in str(e):
                update_without = {k: v for k, v in update_payload.items() if k != "selected_career"}
                result = (
                    self._db.table("career_analyses")
                    .update(update_without)
                    .eq("id", analysis_id)
                    .execute()
                )
            else:
                raise

        updated = result.data[0] if result.data else dict(row, **update_payload)
        updated["selected_career"] = selected_career
        return self._normalize_analysis(updated)

    # -----------------------------------------------------------------------
    # Roadmap Progress
    # -----------------------------------------------------------------------

    def get_roadmap_progress(self, analysis_id: str, profile_id: str) -> List[int]:
        """Returns list of completed step numbers for this analysis."""
        result = (
            self._db.table("roadmap_progress")
            .select("step_number")
            .eq("analysis_id", analysis_id)
            .eq("profile_id", profile_id)
            .eq("completed", True)
            .execute()
        )
        return [row["step_number"] for row in (result.data or [])]

    def set_step_progress(
        self,
        analysis_id: str,
        profile_id: str,
        step_number: int,
        completed: bool,
    ) -> None:
        """Upserts a roadmap step completion."""
        payload = {
            "analysis_id": analysis_id,
            "profile_id": profile_id,
            "step_number": step_number,
            "completed": completed,
            "completed_at": datetime.now(timezone.utc).isoformat() if completed else None,
        }
        self._db.table("roadmap_progress").upsert(
            payload,
            on_conflict="analysis_id,profile_id,step_number"
        ).execute()

    def clear_roadmap_progress(self, analysis_id: str, profile_id: str) -> None:
        """Deletes all completed steps for an analysis/profile (e.g. when career target changes)."""
        self._db.table("roadmap_progress").delete().eq("analysis_id", analysis_id).eq("profile_id", profile_id).execute()

    # -----------------------------------------------------------------------
    # Resume Analysis
    # -----------------------------------------------------------------------

    def save_resume_analysis(self, profile_id: str, data: Dict) -> Dict:
        payload = {
            "profile_id": profile_id,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        result = self._db.table("resume_analyses").insert(payload).execute()
        return result.data[0] if result.data else {}

    def get_latest_resume_analysis(self, profile_id: str) -> Optional[Dict]:
        result = (
            self._db.table("resume_analyses")
            .select("*")
            .eq("profile_id", profile_id)
            .order("analyzed_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def delete_resume_analysis(self, profile_id: str) -> bool:
        """Deletes only resume analysis records for this profile."""
        try:
            self._db.table("resume_analyses").delete().eq("profile_id", profile_id).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete resume analysis for {profile_id}: {e}")
            return False
