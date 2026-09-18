"""
CareerCompass AI — Chat Service
Manages chat sessions, persists messages, builds intent-routed context for Gemini,
and provides robust, deterministic fallbacks tailored to the exact user intent.
"""
import logging
import re
from typing import Any, Dict, List, Optional

from backend.ai.gemini_provider import GeminiProvider
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.chat_repo import ChatRepository
from backend.repositories.profile_repo import ProfileRepository

logger = logging.getLogger(__name__)


def classify_intent(message: str) -> str:
    """
    Classifies user message intent into one of 10 categories to route relevant context:
    1. personal_profile: asks about CGPA, branch, semester, personal details, student skills
    2. resume: asks about uploaded resume, resume feedback, resume score, formatting
    3. assessment: asks about assessment results, domain signals, interest scores
    4. roadmap: asks about roadmap, next steps, milestone completion
    5. analysis: asks about recommended careers, career match score, why a career was suggested
    6. current_affairs: asks about current news, latest tech news, latest events
    7. general_knowledge: general facts, math, science, definitions, world trivia
    8. education: questions about college, diploma, B.Tech lateral entry, degrees, exams
    9. career: questions about career options, job roles, salary, industries, placements
    10. other: general greetings and chat
    """
    lower = message.lower().strip()

    # 1. Personal Profile queries
    if any(k in lower for k in [
        "my cgpa", "what is my gpa", "my grade", "my branch", "registered branch",
        "which branch", "my semester", "current semester", "my full name", "my name",
        "what is my name", "my profile", "my skills", "what skills do i have", "skills on my profile"
    ]):
        return "personal_profile"

    # 2. Resume queries
    if any(k in lower for k in [
        "my resume", "resume score", "resume feedback", "improve my resume",
        "resume formatting", "cv feedback", "review my resume", "resume review"
    ]):
        return "resume"

    # 3. Assessment queries
    if any(k in lower for k in [
        "assessment result", "assessment score", "my assessment", "top interest domain",
        "domain signal", "test results", "my signals", "what did the assessment say"
    ]):
        return "assessment"

    # 4. Roadmap queries
    if any(k in lower for k in [
        "my roadmap", "next step", "roadmap progress", "completed step",
        "what is my next step", "milestone", "step 1", "step 2", "learning path"
    ]):
        return "roadmap"

    # 5. Career Recommendations / Analysis
    if any(k in lower for k in [
        "recommended career", "why did you recommend", "my career match", "career match",
        "career matches", "top match", "top career", "career analysis", "why software developer for me"
    ]):
        return "analysis"

    # 6. Current Affairs / Latest News
    if any(k in lower for k in [
        "latest news", "current affairs", "today's news", "recent news",
        "latest ai news", "latest tech update", "breaking news", "news today"
    ]):
        return "current_affairs"

    # 7. General Knowledge
    if any(k in lower for k in [
        "capital of", "who is the president", "who is the prime minister", "prime minister",
        "photosynthesis", "speed of light", "what is gravity", "what is a computer",
        "who wrote", "tell me about earth", "who discovered", "who invented"
    ]):
        return "general_knowledge"

    # 8. Education & Higher Studies
    if any(k in lower for k in [
        "lateral entry", "b.tech after diploma", "btech after diploma", "ecet",
        "polytechnic syllabus", "c-20", "sbtet", "higher studies", "degree vs diploma"
    ]):
        return "education"

    # 9. Career & Placements
    if any(k in lower for k in [
        "placement", "interview", "salary", "job", "career", "hiring",
        "certif", "nptel", "coursera", "capstone", "project"
    ]):
        return "career"

    return "other"


class ChatService:
    def __init__(
        self,
        profile_repo: ProfileRepository,
        analysis_repo: AnalysisRepository,
        chat_repo: ChatRepository,
        ai_provider: GeminiProvider,
        max_context_tokens: int = 2000,
    ):
        self._profile_repo = profile_repo
        self._analysis_repo = analysis_repo
        self._chat_repo = chat_repo
        self._ai = ai_provider
        self._max_context_tokens = max_context_tokens

    async def send_message(
        self,
        profile_id: str,
        message: str,
        session_id: Optional[str] = None,
    ) -> Dict:
        """
        Processes a chat message with intent routing:
        1. Classify intent into relevant category
        2. Get/create session
        3. Load only relevant student context
        4. Call Gemini with intent-routed prompt
        5. Save user & assistant messages
        6. Return response
        """
        # Intent classification
        intent = classify_intent(message)
        logger.info(f"Classified chat intent as '{intent}' for profile {profile_id}")

        # Get or create chat session
        session = self._chat_repo.get_or_create_session(profile_id, session_id)
        session_id = session["id"]

        # Load student profile
        profile = self._profile_repo.get_by_id(profile_id)
        if not profile:
            raise ValueError("Profile not found")

        skills = self._profile_repo.get_skills(profile_id)
        profile["skills"] = skills
        interests = self._profile_repo.get_interests(profile_id)
        profile["interests"] = interests

        # Load auxiliary context based on intent
        latest_analysis = self._analysis_repo.get_latest_analysis(profile_id)
        assessment_signals = self._profile_repo.get_assessment_answers(profile_id)
        resume_analysis = self._analysis_repo.get_latest_resume_analysis(profile_id)

        skill_gaps = []
        career_goal = profile.get("career_goal", "")
        if latest_analysis:
            skill_gaps = latest_analysis.get("skill_gaps") or []

        # Load conversation history (truncated)
        history = self._chat_repo.get_messages(session_id, profile_id, limit=20)
        conversation_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in history
        ]

        # Save user message first
        self._chat_repo.save_message(session_id, "user", message)

        # Call Gemini with intent-routed context
        is_fallback = False
        try:
            response_text = await self._ai.chat(
                message=message,
                profile=profile,
                career_goal=career_goal,
                skill_gaps=skill_gaps,
                conversation_history=conversation_history,
                latest_analysis=latest_analysis,
                assessment_signals=assessment_signals,
                resume_context=resume_analysis,
                intent=intent,
            )
        except Exception as e:
            logger.warning(
                f"Chat AI service unavailable for session {session_id} ({e}). "
                f"Engaging deterministic counselor fallback for intent '{intent}'."
            )
            is_fallback = True
            response_text = self._build_deterministic_chat_fallback(
                message=message,
                profile=profile,
                career_goal=career_goal,
                skill_gaps=skill_gaps,
                latest_analysis=latest_analysis,
                resume_analysis=resume_analysis,
                assessment_signals=assessment_signals,
                intent=intent,
            )

        # Save assistant response
        saved_msg = self._chat_repo.save_message(session_id, "assistant", response_text)

        return {
            "session_id": session_id,
            "id": saved_msg.get("id"),
            "role": "assistant",
            "content": response_text,
            "intent": intent,
            "error": False,
            "is_fallback": is_fallback,
        }

    def _build_deterministic_chat_fallback(
        self,
        message: str,
        profile: Dict,
        career_goal: str,
        skill_gaps: List,
        latest_analysis: Optional[Dict],
        resume_analysis: Optional[Dict] = None,
        assessment_signals: Optional[List] = None,
        intent: str = "other",
    ) -> str:
        """
        Generates a robust, intent-grounded deterministic response when Gemini API is unavailable.
        Maintains strict separation so queries like 'What is my CGPA?' receive exact answers.
        """
        lower_msg = message.lower().strip()
        branch = (profile.get("branch") or "Engineering").upper()
        semester = profile.get("semester") or 6
        cgpa = profile.get("cgpa")
        cgpa_str = f"{cgpa:.2f}" if cgpa is not None else "Not provided"
        name = profile.get("full_name") or "Student"
        selected_career = (
            (latest_analysis.get("selected_career") if latest_analysis else None)
            or profile.get("selected_career")
            or profile.get("target_career")
            or career_goal
            or "Technical Engineer"
        )

        skills = []
        for s in (profile.get("skills") or []):
            if isinstance(s, dict):
                skills.append(s.get("name") or s.get("skill_name") or str(s))
            else:
                skills.append(str(s))
        skill_str = ", ".join(skills[:5]) if skills else "None recorded yet"

        gaps = []
        for g in (skill_gaps or []):
            if isinstance(g, dict):
                gaps.append(g.get("skill_name") or g.get("name") or str(g))
            else:
                gaps.append(str(g))
        gap_str = ", ".join(gaps[:3]) if gaps else "Core Technical Fundamentals"

        footer = "\n\n*(CareerCompass Academic Advisory Engine)*"

        # 1. Intent: Personal Academic Profile
        if intent == "personal_profile":
            return (
                f"### 👤 Your Academic Profile Overview\n\n"
                f"- **Full Name:** {name}\n"
                f"- **Diploma Branch:** {branch}\n"
                f"- **Current Semester:** Semester {semester}\n"
                f"- **Current CGPA:** **{cgpa_str}**\n"
                f"- **Target Career:** {selected_career}\n"
                f"- **Recorded Skills:** {skill_str}\n"
                f"{footer}"
            )

        # 2. Intent: Resume
        if intent == "resume":
            score = resume_analysis.get("guidance_score") if resume_analysis else None
            score_text = f"{score}/100" if score is not None else "Not evaluated yet"
            strengths = resume_analysis.get("strengths", []) if resume_analysis else []
            missing = resume_analysis.get("missing_skills", []) if resume_analysis else []
            return (
                f"### 📄 Your Resume Analysis Overview\n\n"
                f"- **Career Readiness Score:** **{score_text}**\n"
                f"- **Key Strengths:** {', '.join(strengths[:3]) if strengths else 'Upload your resume to discover strengths.'}\n"
                f"- **Recommended Skills to Add:** {', '.join(missing[:3]) if missing else 'None detected at this stage.'}\n\n"
                f"To improve your resume score, visit the **Resume Review** tab to upload an updated PDF or DOCX draft."
                f"{footer}"
            )

        # 3. Intent: Assessment
        if intent == "assessment":
            signals_text = "No assessment answers submitted yet."
            if assessment_signals:
                signals_text = f"You have submitted {len(assessment_signals)} discovery responses."
            return (
                f"### 🧭 Your Career Assessment Summary\n\n"
                f"{signals_text}\n"
                f"- **Target Recommended Role:** {selected_career}\n"
                f"- **Core Domain Fit:** Aligned with {branch} and your work-style preferences.\n\n"
                f"You can review your detailed multi-signal compatibility scores on the **Career Analysis** page."
                f"{footer}"
            )

        # 4. Intent: Roadmap
        if intent == "roadmap":
            return (
                f"### 🗺️ Learning Roadmap for {selected_career}\n\n"
                f"Your active roadmap is structured into 4 sequential milestones focused on bridging **{gap_str}**.\n\n"
                f"1. **Step 1 (Foundations):** Solidify core branch concepts in {branch}.\n"
                f"2. **Step 2 (Core Competence):** Bridge target gap: **{gap_str}**.\n"
                f"3. **Step 3 (Hands-on Portfolio):** Build a practical application or prototype.\n"
                f"4. **Step 4 (Industry Readiness):** Finalize capstone and prepare technical interview questions.\n\n"
                f"Visit the **My Roadmap** page to mark completed steps and track your progress."
                f"{footer}"
            )

        # 5. Intent: Current Affairs
        if intent == "current_affairs":
            return (
                f"### 📰 Real-Time Information Notice\n\n"
                f"As an AI counselor focused on academic and career guidance, I do not have access to real-time live internet feeds for breaking current affairs or today's news.\n\n"
                f"For verified current technology updates and exam schedules, please check official portals (e.g. AICTE, State Board of Technical Education, and industry news platforms)."
                f"{footer}"
            )

        # 6. Intent: General Knowledge
        if intent == "general_knowledge":
            return (
                f"### 🌐 Academic Concept Assistance\n\n"
                f"Regarding your query: *'{message}'*\n\n"
                f"As CareerCompass AI, my primary focus is academic success, technical fundamentals, and career pathways for diploma engineers. "
                f"For broad factual inquiries, please refer to standard educational textbooks or encyclopedic references."
                f"{footer}"
            )

        # 7. Greetings
        if any(w in lower_msg for w in ("hello", "hi", "hey", "good morning", "good afternoon", "greetings")):
            return (
                f"Hello {name}! I am your CareerCompass AI Counselor.\n\n"
                f"Here is your current profile overview:\n"
                f"- **Academic Branch:** {branch} (Semester {semester}, CGPA: {cgpa_str})\n"
                f"- **Target Career:** {selected_career}\n"
                f"- **Priority Skill Focus:** {gap_str}\n\n"
                f"How can I assist your career journey today? You can ask me about:\n"
                f"1. 📋 **Campus Placements:** How to crack technical & aptitude interview rounds\n"
                f"2. 🎓 **Certifications:** Recommended industry certifications for {branch}\n"
                f"3. 💼 **Career Pathways:** Lateral entry B.Tech vs starting work after diploma\n"
                f"4. 🛠️ **Capstone Projects:** Practical final year project ideas tailored to {selected_career}"
                f"{footer}"
            )

        # 8. Campus Interview Preparation
        if any(w in lower_msg for w in ("interview", "campus", "prepare", "placement", "aptitude")):
            return (
                f"### 📋 Campus Interview Preparation Guide for {branch} Students ({selected_career})\n\n"
                f"To excel in diploma campus placements, focus on this 4-step preparation strategy:\n\n"
                f"1. **Aptitude & Logical Reasoning (Round 1 Qualifier):**\n"
                f"   - Practice quantitative aptitude (Percentages, Profit & Loss, Speed-Time-Distance).\n"
                f"   - Solve 15-20 reasoning puzzles daily on platforms like IndiaBIX.\n"
                f"   - Dedicate 30 minutes daily to technical MCQ practice in core subjects.\n\n"
                f"2. **Core Technical Competence ({branch}):**\n"
                f"   - Solidify core fundamentals: {skill_str}.\n"
                f"   - Bridge your target skill gaps: **{gap_str}**.\n"
                f"   - Be ready to write clean code or explain circuit diagrams/schematics on paper without an IDE.\n\n"
                f"3. **Diploma Final-Year Project Deep-Dive:**\n"
                f"   - Recruiters evaluate how well you understand your project.\n"
                f"   - Prepare to explain: Problem statement, system architecture, your exact individual contribution, challenges faced, and future enhancements.\n\n"
                f"4. **Technical HR & Behavioral Round (STAR Method):**\n"
                f"   - Frame your answers using **Situation, Task, Action, Result**.\n"
                f"   - Prepare answers for: *'Tell me about a technical challenge you resolved'* and *'Why do you want to work as a {selected_career}?'*."
                f"{footer}"
            )

        # 9. Lateral Entry B.Tech vs Job
        if any(w in lower_msg for w in ("lateral", "b.tech", "btech", "diploma vs", "higher studies", "start working", "job")):
            return (
                f"### 💼 Lateral Entry B.Tech vs Starting Work After Diploma\n\n"
                f"Deciding between lateral entry B.Tech (direct 2nd year via ECET/LEET) and an immediate job depends on your goals and academic standing (CGPA: {cgpa_str}):\n\n"
                f"#### Option 1: Lateral Entry B.Tech\n"
                f"- **Best suited for:** Students targeting Tier-1 tech/R&D roles, public sector units (PSUs) requiring a degree, or aspiring to do M.Tech/MS abroad.\n"
                f"- **Advantages:** Unlocks higher starting packages (typically 5-10 LPA vs 2.5-4 LPA for diploma freshers) and removes the career ceiling.\n\n"
                f"#### Option 2: Starting Work After Diploma (Junior Engineer / Apprentice)\n"
                f"- **Best suited for:** Students needing immediate financial independence or preferring practical shop-floor/production experience.\n"
                f"- **Advantages:** Early hands-on industry exposure and financial self-reliance.\n\n"
                f"**Counselor Recommendation:** For **{selected_career}**, holding a B.Tech provides significant long-term leverage for senior engineering roles."
                f"{footer}"
            )

        # Default General Career Guidance
        return (
            f"### 💡 Career Guidance for {selected_career} ({branch})\n\n"
            f"Regarding your query: *'{message}'*\n\n"
            f"As a Semester {semester} {branch} student aiming for **{selected_career}**:\n"
            f"- **Current Focus:** Focus on mastering **{gap_str}** while keeping your CGPA ({cgpa_str}) above 7.5 for campus eligibility.\n"
            f"- **Next Milestone:** Work through the practical milestones outlined in your role-specific roadmap.\n"
            f"- **Mentorship:** Feel free to ask about specific interview rounds, recommended certifications, or comparing technical pathways."
            f"{footer}"
        )

    def get_history(self, profile_id: str, session_id: str) -> List[Dict]:
        """Returns conversation history for a session."""
        return self._chat_repo.get_messages(session_id, profile_id)

    def list_sessions(self, profile_id: str) -> List[Dict]:
        return self._chat_repo.list_sessions(profile_id)
