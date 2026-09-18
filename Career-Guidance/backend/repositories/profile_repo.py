"""
CareerCompass AI — Profile Repository
All database operations for profiles, skills, interests, and assessments.
Uses the service-role client to bypass RLS — authorization is enforced at the service/API layer.
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from supabase import Client

logger = logging.getLogger(__name__)


class ProfileRepository:
    def __init__(self, db: Client):
        self._db = db

    # -----------------------------------------------------------------------
    # Profile CRUD
    # -----------------------------------------------------------------------

    def get_by_id(self, profile_id: str) -> Optional[Dict]:
        """Fetches profile with skills and interests."""
        try:
            result = (
                self._db.table("profiles")
                .select("*")
                .eq("id", profile_id)
                .single()
                .execute()
            )
            return result.data
        except Exception:
            return None

    def create(self, profile_id: str, email: str, data: Dict) -> Dict:
        """Creates a new profile record for the authenticated user."""
        target_email = email or data.get("email") or ""
        payload = {
            "id": profile_id,
            "email": target_email,
            "full_name": data.get("full_name"),
            "branch": data.get("branch"),
            "semester": data.get("semester"),
            "cgpa": data.get("cgpa"),
            "career_goal": data.get("career_goal"),
            "assessment_language": data.get("assessment_language", "en"),
            "profile_version": 1,
            "is_admin": False,
        }
        result = self._db.table("profiles").insert(payload).execute()
        return result.data[0] if result.data else {}

    def update(self, profile_id: str, data: Dict, bump_version: bool = False) -> Dict:
        """Updates profile. If bump_version=True, increments profile_version."""
        payload = {k: v for k, v in data.items() if v is not None}
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        if bump_version:
            # Increment version atomically via DB function
            self._db.rpc("increment_profile_version", {"profile_id": profile_id}).execute()
        
        result = (
            self._db.table("profiles")
            .update(payload)
            .eq("id", profile_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def get_profile_version(self, profile_id: str) -> int:
        """Returns current profile_version."""
        result = (
            self._db.table("profiles")
            .select("profile_version")
            .eq("id", profile_id)
            .single()
            .execute()
        )
        return result.data.get("profile_version", 1) if result.data else 1

    # -----------------------------------------------------------------------
    # Skills
    # -----------------------------------------------------------------------

    def get_skills(self, profile_id: str) -> List[Dict]:
        result = (
            self._db.table("student_skills")
            .select("skill_id, proficiency, skills(id, name, category)")
            .eq("profile_id", profile_id)
            .execute()
        )
        return result.data or []

    def set_skills(self, profile_id: str, skills: List[Dict]) -> None:
        """Replaces all skills for a profile (delete + insert). Supports skill_id or name."""
        self._db.table("student_skills").delete().eq("profile_id", profile_id).execute()
        if skills:
            # Map of skill name -> id in case skill_id was not provided
            all_skills = self.list_all_skills()
            name_to_id = {s["name"].lower(): s["id"] for s in all_skills}
            
            rows = []
            for s in skills:
                sid = s.get("skill_id")
                if not sid:
                    name = s.get("name") or s.get("skill_name")
                    if name and name.lower() in name_to_id:
                        sid = name_to_id[name.lower()]
                if sid:
                    rows.append({
                        "profile_id": profile_id,
                        "skill_id": sid,
                        "proficiency": s.get("proficiency", "beginner"),
                    })
            if rows:
                self._db.table("student_skills").insert(rows).execute()

    # -----------------------------------------------------------------------
    # Interests
    # -----------------------------------------------------------------------

    def get_interests(self, profile_id: str) -> List[str]:
        result = (
            self._db.table("student_interests")
            .select("interest_id, interests(name)")
            .eq("profile_id", profile_id)
            .execute()
        )
        return [row["interests"]["name"] for row in (result.data or []) if row.get("interests")]

    def set_interests(self, profile_id: str, interest_ids: List[str]) -> None:
        """Replaces all interests for a profile."""
        self._db.table("student_interests").delete().eq("profile_id", profile_id).execute()
        if interest_ids:
            rows = [{"profile_id": profile_id, "interest_id": iid} for iid in interest_ids]
            self._db.table("student_interests").insert(rows).execute()

    # -----------------------------------------------------------------------
    # Assessment & Adaptive Discovery
    # -----------------------------------------------------------------------

    def save_assessment_answers(
        self, profile_id: str, answers: List[Dict]
    ) -> None:
        """Saves assessment answers (upsert)."""
        self._db.table("assessment_answers").delete().eq("profile_id", profile_id).execute()
        if answers:
            rows = [
                {
                    "profile_id": profile_id,
                    "question_id": a["question_id"],
                    "option_id": a["option_id"],
                }
                for a in answers
            ]
            self._db.table("assessment_answers").insert(rows).execute()

    def get_assessment_answers(self, profile_id: str) -> List[Dict]:
        try:
            result = (
                self._db.table("assessment_answers")
                .select(
                    "question_id, option_id, "
                    "assessment_questions(question_text, category, phase, domain), "
                    "assessment_options(option_text, career_weight, domain_weight)"
                )
                .eq("profile_id", profile_id)
                .execute()
            )
            raw = result.data or []
            formatted = []
            for item in raw:
                q_info = item.get("assessment_questions") or {}
                opt_info = item.get("assessment_options") or {}
                formatted.append({
                    "question_id": item.get("question_id"),
                    "option_id": item.get("option_id"),
                    "question_text": q_info.get("question_text", ""),
                    "category": q_info.get("category", ""),
                    "phase": q_info.get("phase", "broad"),
                    "domain": q_info.get("domain", "general"),
                    "option_text": opt_info.get("option_text", ""),
                    "career_weight": opt_info.get("career_weight"),
                    "domain_weight": opt_info.get("domain_weight"),
                })
            return formatted
        except Exception as e:
            logger.warning(f"Error fetching rich assessment answers with new columns: {e}, trying standard query")
            try:
                result = (
                    self._db.table("assessment_answers")
                    .select(
                        "question_id, option_id, "
                        "assessment_questions(question_text, category), "
                        "assessment_options(option_text, career_weight)"
                    )
                    .eq("profile_id", profile_id)
                    .execute()
                )
                raw = result.data or []
                formatted = []
                for item in raw:
                    q_info = item.get("assessment_questions") or {}
                    opt_info = item.get("assessment_options") or {}
                    formatted.append({
                        "question_id": item.get("question_id"),
                        "option_id": item.get("option_id"),
                        "question_text": q_info.get("question_text", ""),
                        "category": q_info.get("category", ""),
                        "phase": "broad",
                        "domain": "general",
                        "option_text": opt_info.get("option_text", ""),
                        "career_weight": opt_info.get("career_weight"),
                        "domain_weight": {},
                    })
                return formatted
            except Exception as e2:
                logger.warning(f"Error fetching basic assessment answers: {e2}")
                return []

    def save_assessment_signals(self, profile_id: str, signals: Dict) -> None:
        """Persists computed assessment signals to profiles table if supported."""
        try:
            self._db.table("profiles").update({"assessment_signals": signals}).eq("id", profile_id).execute()
        except Exception as e:
            logger.warning(f"Could not persist assessment_signals to profile {profile_id}: {e}")

    def list_assessment_questions(self, phase: Optional[str] = None, lang: str = "en") -> List[Dict]:
        """Lists assessment questions with options, supporting phase filtering, multilingual display, and schema fallback."""
        questions = []
        try:
            query = (
                self._db.table("assessment_questions")
                .select("id, question_text, question_text_te, category, phase, domain, order_num, assessment_options(id, option_text, option_text_te, career_weight, domain_weight)")
            )
            result = query.order("order_num").execute()
            questions = result.data or []
        except Exception as e:
            logger.warning(f"Could not query expanded assessment_questions ({e}), falling back to standard columns")
            try:
                result = (
                    self._db.table("assessment_questions")
                    .select("id, question_text, category, assessment_options(id, option_text, career_weight)")
                    .order("category")
                    .execute()
                )
                questions = result.data or []
            except Exception as e2:
                logger.error(f"Failed to fetch assessment questions: {e2}")
                return []

        # Standard category mapping for questions that lack phase/domain/order_num in legacy databases
        cat_meta = {
            "Logic": ("broad", "software", 1),
            "Hardware": ("broad", "electronics_embedded", 2),
            "Environment": ("broad", "general", 3),
            "Analytics": ("broad", "data_ai", 4),
            "Design": ("broad", "mechanical_design", 5),
            "Civil": ("deep_dive", "construction_infra", 6),
            "Electrical": ("deep_dive", "electrical_energy", 7),
            "Automotive": ("deep_dive", "automotive_ev", 8),
            "Security": ("deep_dive", "cybersecurity", 9),
            "Mechanical": ("deep_dive", "mechanical_design", 10),
            "Software": ("deep_dive", "software", 11),
            "Data": ("deep_dive", "data_ai", 12),
            "Electronics": ("deep_dive", "electronics_embedded", 13),
            "Work Style": ("work_style", "work_style", 14),
            "Problem Solving": ("problem_solving", "problem_solving", 15),
        }

        # Normalize and enrich questions
        enriched = []
        for idx, q in enumerate(questions):
            q_copy = dict(q)
            cat = q_copy.get("category") or "Logic"
            txt = (q_copy.get("question_text") or "").lower()

            # Smart text-based detection if phase/domain not present
            if "free project" in txt or "build or improve something useful" in txt:
                default_phase, default_domain, default_order = "broad", "software", 1
            elif "smart hospital clinic" in txt:
                default_phase, default_domain, default_order = "broad", "electronics_embedded", 2
            elif "feel most energized and productive" in txt:
                default_phase, default_domain, default_order = "broad", "general", 3
            elif "facts and numbers" in txt:
                default_phase, default_domain, default_order = "broad", "data_ai", 4
            elif "electric vehicle or modern machine" in txt:
                default_phase, default_domain, default_order = "broad", "mechanical_design", 5
            elif "creating a digital application" in txt:
                default_phase, default_domain, default_order = "deep_dive", "software", 11
            elif "exploring patterns in information" in txt:
                default_phase, default_domain, default_order = "deep_dive", "data_ai", 12
            elif "working with electronic devices" in txt:
                default_phase, default_domain, default_order = "deep_dive", "electronics_embedded", 13
            elif "way of working feels most natural" in txt or "work_style" in cat.lower():
                default_phase, default_domain, default_order = "work_style", "work_style", 14
            elif "does not work as expected" in txt or "problem" in cat.lower():
                default_phase, default_domain, default_order = "problem_solving", "problem_solving", 15
            else:
                default_phase, default_domain, default_order = cat_meta.get(cat, ("deep_dive", "general", idx + 1))

            if not q_copy.get("phase"):
                q_copy["phase"] = default_phase
            if not q_copy.get("domain"):
                q_copy["domain"] = default_domain
            if q_copy.get("order_num") is None:
                q_copy["order_num"] = default_order

            # Enrich options with domain weights if missing
            opts = q_copy.get("assessment_options") or []
            enriched_opts = []
            for opt in opts:
                opt_copy = dict(opt)
                if not opt_copy.get("domain_weight"):
                    # Infer domain weights from career weights
                    dw = {}
                    cw = opt_copy.get("career_weight") or {}
                    for car in cw:
                        car_lower = car.lower()
                        if any(k in car_lower for k in ["software", "frontend", "backend", "full stack"]):
                            dw["software"] = 10
                        elif "data" in car_lower:
                            dw["data_ai"] = 10
                        elif "cyber" in car_lower:
                            dw["cybersecurity"] = 10
                        elif any(k in car_lower for k in ["embedded", "vlsi"]):
                            dw["electronics_embedded"] = 10
                        elif "electrical" in car_lower:
                            dw["electrical_energy"] = 10
                        elif any(k in car_lower for k in ["mechanical", "hvac"]):
                            dw["mechanical_design"] = 10
                        elif any(k in car_lower for k in ["automobile", "ev"]):
                            dw["automotive_ev"] = 10
                        elif any(k in car_lower for k in ["structural", "site"]):
                            dw["construction_infra"] = 10
                        elif "manufacturing" in car_lower:
                            dw["manufacturing_automation"] = 10
                    opt_copy["domain_weight"] = dw
                enriched_opts.append(opt_copy)

            if lang == "te":
                if q_copy.get("question_text_te"):
                    q_copy["question_text"] = q_copy["question_text_te"]
                for opt in enriched_opts:
                    if opt.get("option_text_te"):
                        opt["option_text"] = opt["option_text_te"]

            q_copy["assessment_options"] = enriched_opts
            enriched.append(q_copy)

        # Sort enriched questions by order_num
        enriched.sort(key=lambda x: x.get("order_num", 99))

        if phase:
            return [q for q in enriched if q.get("phase") == phase]
        return enriched

    def calculate_assessment_signals(self, answers: List[Dict]) -> Dict[str, Any]:
        """
        Pure deterministic calculation of interest domains and career weights
        from submitted answers.
        """
        domain_meta = {
            "software": {"label": "Software & Web Development", "icon": "💻"},
            "data_ai": {"label": "Data Intelligence & Analytics", "icon": "📊"},
            "cybersecurity": {"label": "Cybersecurity & Systems Defense", "icon": "🔐"},
            "electronics_embedded": {"label": "Electronics & Embedded Systems", "icon": "⚡"},
            "electrical_energy": {"label": "Electrical Systems & Clean Energy", "icon": "🔋"},
            "mechanical_design": {"label": "Mechanical Design & Machinery", "icon": "⚙️"},
            "automotive_ev": {"label": "Automotive & Electric Mobility", "icon": "🏎️"},
            "construction_infra": {"label": "Civil Infrastructure & Construction", "icon": "🏗️"},
            "manufacturing_automation": {"label": "Manufacturing & Automation", "icon": "🏭"},
        }

        # Fetch questions and options map
        all_questions = self.list_assessment_questions()
        option_map: Dict[str, Dict] = {}
        for q in all_questions:
            opts = q.get("assessment_options") or []
            for opt in opts:
                option_map[str(opt["id"])] = {
                    "question_id": str(q["id"]),
                    "category": q.get("category", "General"),
                    "domain": q.get("domain", "general"),
                    "career_weight": opt.get("career_weight") or {},
                    "domain_weight": opt.get("domain_weight") or {},
                    "option_text": opt.get("option_text", ""),
                }

        domain_scores: Dict[str, float] = {d: 0.0 for d in domain_meta}
        career_weights: Dict[str, float] = {}
        work_style: Dict[str, int] = {"digital": 0, "physical": 0, "analytical": 0, "creative": 0}

        for ans in answers:
            opt_id = str(ans.get("option_id") or "")
            opt_data = option_map.get(opt_id)
            if not opt_data:
                continue

            # Accumulate domain weights
            dw = opt_data.get("domain_weight") or {}
            for dom, pts in dw.items():
                if dom in domain_scores:
                    domain_scores[dom] += float(pts)

            # Accumulate career weights
            cw = opt_data.get("career_weight") or {}
            for car, pts in cw.items():
                career_weights[car] = career_weights.get(car, 0.0) + float(pts)

            # Infer work style
            text_lower = opt_data.get("option_text", "").lower()
            if any(k in text_lower for k in ["website", "app", "code", "software", "screen", "digital"]):
                work_style["digital"] += 1
            if any(k in text_lower for k in ["physical", "hands-on", "site", "engine", "motor", "soldering"]):
                work_style["physical"] += 1
            if any(k in text_lower for k in ["data", "trend", "calculat", "logic", "analyz"]):
                work_style["analytical"] += 1
            if any(k in text_lower for k in ["design", "creative", "styling", "visual", "craft"]):
                work_style["creative"] += 1

        # Calculate max domain score for normalization
        max_score = max(domain_scores.values()) if domain_scores and max(domain_scores.values()) > 0 else 1.0

        # Sort domains descending
        sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        top_domain_signals = []
        for dom, score in sorted_domains:
            norm_signal = round((score / max(max_score, 10.0)) * 100, 1) if score > 0 else 0.0
            level = "Strong" if norm_signal >= 70 else ("Moderate" if norm_signal >= 35 else "Emerging")
            meta = domain_meta.get(dom, {"label": dom.title(), "icon": "🎯"})
            top_domain_signals.append({
                "domain": dom,
                "domain_label": meta["label"],
                "icon": meta["icon"],
                "raw_score": score,
                "signal": norm_signal,
                "level": level,
            })

        return {
            "top_interest_domains": top_domain_signals[:3],
            "all_domain_signals": top_domain_signals,
            "career_weights": career_weights,
            "work_preferences": {
                "digital_orientation": "high" if work_style["digital"] > work_style["physical"] else "balanced",
                "problem_solving": "analytical" if work_style["analytical"] >= work_style["creative"] else "creative",
            },
        }

    # -----------------------------------------------------------------------
    # Reference data
    # -----------------------------------------------------------------------

    def list_all_skills(self) -> List[Dict]:
        result = (
            self._db.table("skills")
            .select("id, name, category")
            .order("category")
            .execute()
        )
        return result.data or []

    def list_all_interests(self) -> List[Dict]:
        result = (
            self._db.table("interests")
            .select("id, name")
            .order("name")
            .execute()
        )
        return result.data or []

