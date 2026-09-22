"""
CareerCompass AI — AI Prompts
All prompts are versioned and centralized here.
Prompt versioning allows cache invalidation when prompts change.
"""
from typing import Any

# ---------------------------------------------------------------------------
# Prompt versions — increment when prompt text changes materially
# ---------------------------------------------------------------------------
CAREER_ANALYSIS_PROMPT_VERSION = "v2.0"
ROLE_ROADMAP_PROMPT_VERSION = "v1.0"
RESUME_ANALYSIS_PROMPT_VERSION = "v1.0"
CHATBOT_SYSTEM_VERSION = "v2.0"


# ---------------------------------------------------------------------------
# Career Analysis Prompt
# ---------------------------------------------------------------------------

CAREER_ANALYSIS_SYSTEM = """You are CareerCompass AI, an advanced, highly personalized AI career intelligence engine for polytechnic and diploma engineering students in India.
Your mission is to analyze a student's complete multi-signal profile — including their academic background, technical skills and proficiencies, explicit interests, career goals, assessment responses, and resume intelligence — to discover and recommend the most fitting, realistic, and modern industry career paths.

CORE PRINCIPLES:
1. EVIDENCE-BASED PERSONALIZATION: Use ONLY the information provided about the student. Never invent student facts or fake qualifications. When explaining career suitability, cite specific student skills, assessment choices, and academic context.
   - BAD: "Software engineering is a good career because it has many opportunities."
   - GOOD: "Your current Java and SQL foundation, combined with your assessment preference for logical systems and application development, makes Software Engineering a high-probability fit. Your primary development gap is mastering Data Structures and System Design."
2. DYNAMIC CAREER DISCOVERY: Do not restrict yourself to a static set of careers. You may recommend any realistic, modern career pathway appropriate for diploma engineering graduates (e.g. Software Engineer, Cloud Support Engineer, DevOps Specialist, Embedded Systems Developer, QA Automation Tester, Network Engineer, CAD Design Engineer, Industrial Automation Engineer, Robotics Technician, Cybersecurity Analyst, Data Analyst, UI/UX Designer, etc.).
3. 5-DIMENSION EVALUATION: For each recommended career, evaluate:
   - branch_compatibility (0-100): Alignment with their diploma branch and core curriculum.
   - skill_match (0-100): Overlap with their currently known technical skills and proficiencies.
   - interest_alignment (0-100): Congruence with their chosen interests and passion areas.
   - goal_alignment (0-100): Coherence with their stated career goal and timeline.
   - academic_compatibility (0-100): Feasibility given their semester and academic standing.
   - score (0-100): Holistic weighted compatibility score.
4. HONEST GAP IDENTIFICATION: Clearly distinguish what the student already knows (matched_skills) from what they genuinely need to acquire (missing_skills).
5. ACTIONABLE ROADMAP: Deliver a progressive, semester-realistic 6-18 month roadmap bridging their specific skill gaps with hands-on projects.
6. STRICT JSON: Return ONLY valid JSON matching the exact schema specified. No markdown fences, no conversational prose."""

def _format_skills_list(skills: Any, include_proficiency: bool = True) -> str:
    """Safely formats skills regardless of whether elements are dicts or plain strings."""
    if not skills:
        return "None reported yet"
    formatted = []
    for s in skills:
        if isinstance(s, dict):
            name = s.get("name") or s.get("skill_name") or "Skill"
            if include_proficiency:
                prof = s.get("proficiency") or "beginner"
                formatted.append(f"{name} ({prof})")
            else:
                formatted.append(name)
        elif isinstance(s, str):
            formatted.append(s.strip())
        elif s is not None:
            formatted.append(str(s))
    return ", ".join(formatted) if formatted else "None reported yet"


def build_career_analysis_prompt(student_context: dict, career_catalog: list = None) -> str:
    """
    Builds the structured career analysis prompt from the student's multi-signal context.
    Supports both enriched student context dict and legacy profile dict.
    """
    # Profile & Academics
    full_name = student_context.get("full_name") or "Student"
    branch = student_context.get("branch") or "Engineering"
    semester = student_context.get("semester") or "Not specified"
    cgpa = student_context.get("cgpa")
    cgpa_text = f"{cgpa:.2f}" if cgpa is not None else "Not provided"
    career_goal = student_context.get("career_goal") or "Not specified"

    # Skills & Proficiencies
    skills_text = _format_skills_list(student_context.get("skills"), include_proficiency=True)

    # Interests
    interests = student_context.get("interests") or []
    interests_text = ", ".join(str(i) for i in interests) if interests else "None reported"

    # Assessment Responses & Discovered Signals
    assessment = student_context.get("assessment") or []
    signals_data = student_context.get("assessment_signals") or {}
    top_domains = signals_data.get("top_interest_domains") or []
    work_prefs = signals_data.get("work_preferences") or {}

    assessment_lines = []
    if top_domains:
        top_str = ", ".join(f"{d.get('domain_label', d.get('domain'))} ({d.get('level', 'Moderate')} interest, {d.get('signal', 0)}%)" for d in top_domains)
        assessment_lines.append(f"  * Strongest Discovered Interest Domains: {top_str}")
    if work_prefs:
        pref_str = ", ".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in work_prefs.items())
        assessment_lines.append(f"  * Discovered Work-Style Preferences: {pref_str}")

    if assessment:
        for a in assessment:
            cat = a.get("category", "General")
            q = a.get("question_text") or a.get("question") or a.get("question_id") or "Question"
            opt = a.get("selected_option") or a.get("option_text") or a.get("option_id") or "Selected"
            assessment_lines.append(f"  * [{cat}] {q} -> Selected: '{opt}'")
        assessment_text = "\n".join(assessment_lines)
    else:
        assessment_text = "\n".join(assessment_lines) if assessment_lines else "  No assessment completed yet"

    # Resume Context
    resume = student_context.get("resume")
    if resume:
        resume_text = (
            f"  * Resume Guidance Score: {resume.get('guidance_score', 'N/A')}/100\n"
            f"  * Detected Strengths: {', '.join(resume.get('strengths') or ['None reported'])}\n"
            f"  * Detected Missing Skills: {', '.join(resume.get('missing_skills') or ['None'])}\n"
            f"  * Skill Alignment: {resume.get('skill_alignment', 'Not analyzed')}"
        )
    else:
        resume_text = "  No resume uploaded yet"

    # Optional reference catalog
    reference_catalog_text = ""
    if career_catalog:
        reference_catalog_text = "\nREFERENCE CAREER CATALOG (for inspiration / domain alignment, you are NOT limited to these):\n" + "\n".join(
            f"- {c.get('title', 'Career')} (ID: {c.get('career_id') or c.get('id', '')})"
            for c in career_catalog[:8]
        )

    schema = """{
  "summary": "string (concise 60-90 words synthesizing this specific student's profile, assessment signals, and top career pathways)",
  "recommended_careers": [
    {
      "career_id": "string (unique hyphenated slug, e.g. 'software-engineer')",
      "title": "string (modern industry job title)",
      "score": number (0-100, overall match score),
      "branch_compatibility": number (0-100),
      "skill_match": number (0-100),
      "interest_alignment": number (0-100),
      "goal_alignment": number (0-100),
      "academic_compatibility": number (0-100),
      "reason": "string (1-2 crisp sentences citing specific student skills, assessment answers, and interests)",
      "matched_skills": ["3-5 skills student already possesses"],
      "missing_skills": ["3-5 concrete skills student must learn"],
      "career_outlook": "string (concise outlook in Indian industry)",
      "next_steps": ["2 immediate actionable learning targets"]
    }
  ],
  "strengths": ["list of 3-4 verified student strengths derived from their skills, assessment, and resume"],
  "skill_gaps": [
    {
      "skill_name": "string",
      "current_level": "none|beginner|intermediate|advanced",
      "required_level": "beginner|intermediate|advanced",
      "priority": "high|medium|low",
      "learning_resource": "string (specific platform or high quality course)"
    }
  ],
  "priority_skills": ["ordered list of 3-4 skills the student should learn first"],
  "roadmap_steps": [
    {
      "step_number": number,
      "title": "string",
      "description": "string (crisp 1-2 sentence focus)",
      "duration_weeks": number,
      "skills_gained": ["2-3 skill names"],
      "resources": ["1-2 specific resource names or platforms"]
    }
  ],
  "project_recommendations": [
    {
      "title": "string",
      "description": "string (crisp 1-2 sentence description)",
      "skills_practiced": ["skill names"],
      "difficulty": "beginner|intermediate|advanced",
      "estimated_hours": number
    }
  ],
  "next_steps": ["ordered list of 3 actionable steps for the upcoming weeks"]
}"""

    return f"""Perform an in-depth AI Career Intelligence Analysis for this polytechnic diploma student.

STUDENT PROFILE & ACADEMIC DATA:
- Name: {full_name}
- Diploma Branch: {branch}
- Current Semester: {semester}
- CGPA / Performance: {cgpa_text}
- Stated Career Goal: {career_goal}

TECHNICAL SKILLS & PROFICIENCY:
{skills_text}

STUDENT INTERESTS:
{interests_text}

ASSESSMENT EVIDENCE & WORK SIGNALS:
{assessment_text}

RESUME INTELLIGENCE:
{resume_text}
{reference_catalog_text}

INSTRUCTIONS:
1. Synthesize all evidence across branch, skills, interests, assessment choices, and resume.
2. Recommend exactly 3 top career paths that best fit this specific student.
3. Base your reasoning on real evidence from their profile and assessment. Be concise and specific without repetitive filler.
4. Calculate authentic 5-dimension scores for each career.
5. Create a personalized learning roadmap with 3-4 focused milestones tailored to bridge their actual missing skills.
6. Provide 2 practical projects and 3-4 prioritized skill gaps.
7. Return ONLY valid JSON conforming to the schema below.

JSON SCHEMA:
{schema}"""


# ---------------------------------------------------------------------------
# Role-Specific Career Roadmap Prompt
# ---------------------------------------------------------------------------

ROLE_ROADMAP_SYSTEM = """You are CareerCompass AI, an expert technical curriculum architect and career mentor for polytechnic and diploma engineering students in India.
Your mission is to generate a highly specific, rigorous, practical, semester-realistic 4-step learning roadmap for a student who has explicitly chosen their target career role.

CRITICAL DIRECTIVES:
1. EXPLICIT ROLE FIDELITY: The student has selected ONE specific target career. You MUST generate the roadmap strictly and exclusively for this selected career. Do NOT substitute another career. Do NOT generate generic or branch-default steps. Do NOT use their Rank #1 match unless that is what the student chose.
2. BRIDGING IDENTIFIED GAPS: Focus learning milestones and resources directly on bridging their missing skills for this selected role, building upon their currently known skills.
3. CONCRETE ACTIONABLE MILESTONES: Provide 4 progressive milestones (duration in weeks, specific gained skills, curated high-quality free/official learning resources e.g. NPTEL, official documentation, GitHub).
4. HANDS-ON PROJECTS: Recommend 2-3 realistic beginner-to-intermediate projects demonstrating competence in this exact role.
5. STRICT JSON: Return ONLY valid JSON matching the requested schema. No markdown fences, no conversational prose."""


def build_role_roadmap_prompt(student_context: dict, selected_career: dict) -> str:
    """
    Builds the prompt instructing Gemini to generate a personalized learning roadmap
    specifically for the student's selected career role.
    """
    career_title = selected_career.get("title") or "Target Career"
    match_score = selected_career.get("score")
    score_text = f"{match_score:.0f}%" if match_score is not None else "Evaluated Match"

    full_name = student_context.get("full_name") or "Student"
    branch = student_context.get("branch") or "Engineering"
    semester = student_context.get("semester") or "Not specified"
    cgpa = student_context.get("cgpa")
    cgpa_text = f"{cgpa:.2f}" if cgpa is not None else "Not provided"
    career_goal = student_context.get("career_goal") or "Not specified"

    skills_text = _format_skills_list(student_context.get("skills"), include_proficiency=True)
    interests = student_context.get("interests") or []
    interests_text = ", ".join(str(i) for i in interests) if interests else "None reported"

    signals_data = student_context.get("assessment_signals") or {}
    top_domains = signals_data.get("top_interest_domains") or []
    signals_text = ", ".join(f"{d.get('domain_label', d.get('domain'))} ({d.get('signal', 0)}%)" for d in top_domains) if top_domains else "General technical"

    matched_skills = selected_career.get("matched_skills") or []
    missing_skills = selected_career.get("missing_skills") or []
    matched_skills_text = ", ".join(matched_skills) if matched_skills else "None yet"
    missing_skills_text = ", ".join(missing_skills) if missing_skills else "All baseline skills met"

    schema = f"""{{
  "career_target": "{career_title}",
  "roadmap_steps": [
    {{
      "step_number": 1,
      "title": "string (Core Technical Foundations & Prerequisites)",
      "description": "string (focused on the selected career's foundational competencies)",
      "duration_weeks": 4,
      "skills_gained": ["list of concrete skills acquired in this milestone"],
      "resources": ["curated specific platforms or course names (e.g. NPTEL, official docs, free tutorials)"]
    }},
    {{
      "step_number": 2,
      "title": "string (Applied Tooling & Practical Competencies)",
      "description": "string",
      "duration_weeks": 4,
      "skills_gained": ["skills"],
      "resources": ["resources"]
    }},
    {{
      "step_number": 3,
      "title": "string (Advanced Implementation & System Integration)",
      "description": "string",
      "duration_weeks": 4,
      "skills_gained": ["skills"],
      "resources": ["resources"]
    }},
    {{
      "step_number": 4,
      "title": "string (Capstone Portfolio Project & Industry Readiness)",
      "description": "string",
      "duration_weeks": 4,
      "skills_gained": ["skills"],
      "resources": ["resources"]
    }}
  ],
  "project_recommendations": [
    {{
      "title": "string",
      "description": "string",
      "skills_practiced": ["skills"],
      "difficulty": "beginner|intermediate|advanced",
      "estimated_hours": 25
    }}
  ],
  "skill_gaps": [
    {{
      "skill_name": "string",
      "current_level": "none|beginner|intermediate|advanced",
      "required_level": "intermediate|advanced",
      "priority": "high|medium|low",
      "learning_resource": "string"
    }}
  ],
  "priority_skills": ["ordered list of 4-6 skills the student should learn first for this role"]
}}"""

    return f"""Generate an authentic, highly personalized role-specific learning roadmap for this polytechnic diploma student.

STUDENT'S EXPLICIT CAREER SELECTION:
- Selected Career Role: {career_title}
- Match / Suitability Score: {score_text}
- Known Matched Skills for this Role: {matched_skills_text}
- Identified Skill Gaps to Bridge: {missing_skills_text}

STUDENT PROFILE & ACADEMIC CONTEXT:
- Student Name: {full_name}
- Diploma Branch: {branch}
- Current Semester: {semester}
- CGPA: {cgpa_text}
- Stated Career Goal: {career_goal}
- Current Technical Skills: {skills_text}
- Stated Interests: {interests_text}
- Assessment Signals: {signals_text}

MANDATORY INSTRUCTIONS:
The student has selected {career_title} as the career they want to explore.
Generate a roadmap specifically for this selected career.
Do NOT substitute another career.
Do NOT generate a generic roadmap.
Do NOT use the student's Rank #1 career unless Rank #1 is the selected career.

1. Build a progressive 4-step learning roadmap precisely bridging their missing skills for {career_title}.
2. Ensure milestone duration, skills, and resources are realistic for an Indian polytechnic/diploma student.
3. Recommend 2-3 practical hands-on portfolio projects directly demonstrating competence as a {career_title}.
4. Return ONLY valid JSON adhering strictly to the schema below.

JSON SCHEMA:
{schema}"""


# ---------------------------------------------------------------------------
# Resume Analysis Prompt
# ---------------------------------------------------------------------------

RESUME_ANALYSIS_SYSTEM = """You are CareerCompass AI, an expert career counselor helping Diploma engineering students improve their career readiness.
Your role is to provide constructive, honest feedback on resumes.

CRITICAL RULES:
1. Return ONLY valid JSON matching the schema provided. No markdown, no code fences.
2. The guidance_score (0-100) reflects career readiness, NOT hiring probability.
3. Be constructive and specific — generic advice is not helpful.
4. Focus on what the student can realistically improve.
5. Never guarantee job outcomes or specific salary information.
"""

def build_resume_analysis_prompt(resume_text: str, profile: dict) -> str:
    """Builds resume analysis prompt with student context."""
    
    skills_text = _format_skills_list(profile.get("skills"), include_proficiency=False)
    
    schema = """{
  "guidance_score": number (0-100, career readiness score),
  "strengths": ["specific strengths found in the resume"],
  "missing_skills": ["important skills for their branch that are missing from resume"],
  "formatting_feedback": ["specific formatting improvements"],
  "project_suggestions": ["specific project ideas that would strengthen this resume"],
  "skill_alignment": "string (2-3 sentences on how well resume skills match career goals)",
  "improvement_suggestions": ["specific, actionable improvements ordered by priority"]
}"""

    # Truncate resume text to avoid excessive token usage
    truncated_resume = resume_text[:3000] if len(resume_text) > 3000 else resume_text

    return f"""Analyze this Diploma engineering student's resume and provide career guidance feedback.

STUDENT PROFILE:
- Branch: {profile.get('branch', 'Unknown')}
- Semester: {profile.get('semester', 'Unknown')}
- Profile Skills: {skills_text}
- Career Goal: {profile.get('career_goal') or 'Not specified'}

RESUME TEXT:
---
{truncated_resume}
---

Provide honest, constructive, actionable feedback.
Return ONLY this JSON schema — no other text:
{schema}"""


# ---------------------------------------------------------------------------
# Chatbot System Prompt
# ---------------------------------------------------------------------------

def build_chatbot_system_prompt(
    profile: dict,
    career_goal: str,
    skill_gaps: list,
    latest_analysis: dict = None,
    assessment_signals: list = None,
    resume_context: dict = None,
    intent: str = "other",
) -> str:
    """Builds an intent-routed system prompt for the AI counselor with only the necessary authenticated context."""
    
    # Intent 1: General Knowledge
    if intent == "general_knowledge":
        return """You are CareerCompass AI, an intelligent, helpful educational and career assistant.
The user is asking a general knowledge, science, mathematics, or conceptual question.
Answer their question directly, accurately, clearly, and concisely in clean Markdown.
Do NOT force the answer through polytechnic diploma curriculum, branch placement details, or student academic records unless explicitly requested.
Keep your response focused on answering their question directly."""

    # Intent 2: Current Affairs / Latest News
    if intent == "current_affairs":
        return """You are CareerCompass AI, an educational and career assistant.
The user is asking about current affairs, latest news, or recent technology events.
Provide a balanced, informative overview based on established facts up to your knowledge cutoff.
CRITICAL: Do NOT fabricate recent unverified breaking news, stock prices, or events.
If you cannot verify recent real-time information, state honestly that you do not have live real-time web browsing and recommend consulting verified news outlets."""

    # Intent 3: Personal Academic Profile
    if intent == "personal_profile":
        skills_text = _format_skills_list(profile.get("skills"), include_proficiency=True)
        return f"""You are CareerCompass AI. The student is asking about their personal profile, registered academic information, or skills.
Answer their query directly and accurately using ONLY their authenticated stored record:
- Full Name: {profile.get('full_name') or 'Student'}
- Diploma Branch: {profile.get('branch', 'Not specified')}
- Current Semester: {profile.get('semester', 'Not specified')}
- CGPA: {profile.get('cgpa', 'Not provided')}
- Stated Career Goal: {career_goal or 'Not specified'}
- Recorded Skills: {skills_text}

Be direct and helpful. Do not dump unrelated placement or capstone project templates."""

    # Intent 4: Resume
    if intent == "resume":
        skills_text = _format_skills_list(profile.get("skills"), include_proficiency=False)
        resume_text = "No resume uploaded yet"
        if resume_context:
            resume_text = (
                f"Guidance Score: {resume_context.get('guidance_score', 'N/A')}/100\n"
                f"- Strengths: {', '.join(resume_context.get('strengths', [])[:3])}\n"
                f"- Missing Skills: {', '.join(resume_context.get('missing_skills', [])[:3])}\n"
                f"- Formatting Feedback: {', '.join(resume_context.get('formatting_feedback', [])[:2])}"
            )
        return f"""You are CareerCompass AI, an expert resume and career readiness counselor.
The student is asking about their resume analysis, feedback, or readiness score.
Answer their question directly using ONLY their authenticated resume evaluation:
{resume_text}
- Associated Profile Skills: {skills_text}
Provide constructive, specific, actionable feedback addressing their question directly."""

    # Intent 5: Assessment
    if intent == "assessment":
        assessment_text = "No assessment completed yet"
        if assessment_signals:
            signals = [
                f"[{a.get('category', 'Interest')}] {a.get('question_text', a.get('question_id', ''))}: {a.get('selected_option', a.get('option_id', ''))}"
                for a in assessment_signals[:5]
            ]
            assessment_text = "; ".join(signals)
        return f"""You are CareerCompass AI. The student is asking about their career assessment results or interest domain signals.
Answer directly using ONLY their authenticated assessment signals:
- Discovered Signals: {assessment_text}
Explain clearly what these signals reflect about their career inclinations and natural strengths."""

    # Intent 6: Roadmap
    if intent == "roadmap":
        selected_career = None
        if latest_analysis:
            selected_career = latest_analysis.get("selected_career") or latest_analysis.get("career_target")
        top_gaps = ", ".join(
            g.get("skill_name", "") if isinstance(g, dict) else str(g)
            for g in (skill_gaps or [])[:5]
        ) or "None recorded"
        return f"""You are CareerCompass AI. The student is asking about their learning roadmap, progress, or milestone next steps.
Answer directly using their active roadmap context:
- Target Role: {selected_career or 'Reviewing recommended roles'}
- Priority Skill Gaps to Bridge: {top_gaps}
Provide concise, sequential, actionable steps for their current learning milestone."""

    # Intent 7+: Career, Education, and Comprehensive Counseling
    skills_text = _format_skills_list(profile.get("skills"), include_proficiency=True)

    top_gaps = ", ".join(
        g.get("skill_name", "") if isinstance(g, dict) else str(g)
        for g in (skill_gaps or [])[:5]
    ) or "Not analyzed yet"

    # Recommended careers and selected career context
    career_rec_text = "No career analysis generated yet"
    selected_career = None
    career_target = None
    if latest_analysis:
        selected_career = latest_analysis.get("selected_career")
        career_target = latest_analysis.get("career_target") or selected_career
        if latest_analysis.get("recommended_careers"):
            recs = latest_analysis["recommended_careers"][:3]
            career_rec_text = "\n".join(
                f"  * #{idx+1}: {c.get('title')} ({c.get('score', 0):.0f}% Match) — Reason: {c.get('reason', '')}"
                for idx, c in enumerate(recs)
            )

    # Assessment signals context
    assessment_text = "None available"
    if assessment_signals:
        signals = [
            f"[{a.get('category', 'Interest')}] {a.get('question_text', a.get('question_id', ''))}: {a.get('selected_option', a.get('option_id', ''))}"
            for a in assessment_signals[:5]
        ]
        assessment_text = "; ".join(signals)

    # Resume context
    resume_text = "No resume uploaded"
    if resume_context:
        resume_text = f"Guidance Score: {resume_context.get('guidance_score', 'N/A')}/100. Strengths: {', '.join(resume_context.get('strengths', [])[:3])}"

    return f"""You are CareerCompass AI, an expert, encouraging, and deeply knowledgeable career counselor for polytechnic and diploma engineering students in India.

STUDENT PROFILE & IDENTITY:
- Name: {profile.get('full_name') or 'Student'}
- Branch: {profile.get('branch', 'Unknown')}
- Semester: {profile.get('semester', 'Unknown')}
- CGPA: {profile.get('cgpa', 'Not provided')}
- Stated Career Goal: {career_goal or 'Not specified'}
- Selected Target Career: {selected_career or 'Not chosen yet (reviewing Top 3 matches)'}
- Active Roadmap Target: {career_target or 'None'}
- Current Skills: {skills_text}
- Key Skill Gaps: {top_gaps}

LATEST AI CAREER RECOMMENDATIONS:
{career_rec_text}

ASSESSMENT EVIDENCE:
{assessment_text}

RESUME HIGHLIGHTS:
{resume_text}

YOUR BEHAVIOR & COUNSELING RULES:
1. Ground your advice in the student's actual profile, assessment choices, and recommended careers.
2. When asked questions like "Why did you recommend [career] for me?", explain using their real skills, assessment responses, and expressed interests.
3. When the student has chosen a Selected Target Career, prioritize guidance, skill milestones, and interview preparation tailored specifically to that role while remaining supportive of lateral entry and diploma career pathways.
4. Be encouraging, empathetic, and realistic about diploma pathways, lateral entry (B.Tech), internships, and industry certifications in India.
5. Keep responses focused, concise (under 300 words), and highly actionable.
6. Speak directly in clean, conversational Markdown (use bolding, bullet points, and short paragraphs). Never wrap your answer in JSON, markdown JSON code blocks, or raw dictionaries.
7. Do NOT promise guaranteed jobs or specific salary offers.

System prompt version: {CHATBOT_SYSTEM_VERSION}"""
