"""
CareerCompass AI — Career Repository
Fetches careers and career-skill mappings from Supabase.
"""
import logging
from typing import Any, Dict, List, Optional

from supabase import Client

logger = logging.getLogger(__name__)


class CareerRepository:
    def __init__(self, db: Client):
        self._db = db

    def list_careers(
        self,
        branch: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """Lists careers with optional branch filter and search."""
        query = self._db.table("careers").select(
            "id, title, description, branches, min_cgpa, avg_salary_lpa, job_growth, industry"
        )
        if branch:
            # careers.branches is a text array in Postgres
            query = query.contains("branches", [branch])
        if search:
            query = query.ilike("title", f"%{search}%")
        result = query.limit(limit).execute()
        return result.data or []

    def get_career_by_id(self, career_id: str) -> Optional[Dict]:
        result = (
            self._db.table("careers")
            .select("*, career_skills(skill_id, required_level, weight, skills(name, category)), career_projects(projects(id, title, description, difficulty, estimated_hours))")
            .eq("id", career_id)
            .single()
            .execute()
        )
        return result.data

    def get_careers_with_skills(self) -> List[Dict]:
        """Returns all careers with their required skills for the matching engine."""
        result = (
            self._db.table("careers")
            .select("id, title, branches, industry, career_skills(skill_id, required_level, weight, skills(name))")
            .execute()
        )
        return result.data or []

    def get_career_skills(self, career_id: str) -> List[Dict]:
        result = (
            self._db.table("career_skills")
            .select("skill_id, required_level, weight, skills(id, name, category)")
            .eq("career_id", career_id)
            .execute()
        )
        return result.data or []

    # -----------------------------------------------------------------------
    # Admin CRUD
    # -----------------------------------------------------------------------

    def create_career(self, data: Dict) -> Dict:
        result = self._db.table("careers").insert(data).execute()
        return result.data[0] if result.data else {}

    def update_career(self, career_id: str, data: Dict) -> Dict:
        result = (
            self._db.table("careers")
            .update(data)
            .eq("id", career_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete_career(self, career_id: str) -> bool:
        result = self._db.table("careers").delete().eq("id", career_id).execute()
        return bool(result.data)

    def create_skill(self, data: Dict) -> Dict:
        result = self._db.table("skills").insert(data).execute()
        return result.data[0] if result.data else {}

    def update_skill(self, skill_id: str, data: Dict) -> Dict:
        result = (
            self._db.table("skills").update(data).eq("id", skill_id).execute()
        )
        return result.data[0] if result.data else {}

    def list_projects(self) -> List[Dict]:
        result = self._db.table("projects").select("*").execute()
        return result.data or []

    def create_project(self, data: Dict) -> Dict:
        result = self._db.table("projects").insert(data).execute()
        return result.data[0] if result.data else {}
