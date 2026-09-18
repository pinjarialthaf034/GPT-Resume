"""
CareerCompass AI — Deterministic Career Matching Engine
Phase 7: This engine computes career match scores WITHOUT calling Gemini.
Gemini is only called AFTER this engine produces the ranked list.

Scoring dimensions:
  - Branch compatibility     (30 points)
  - Skill compatibility      (35 points)
  - Interest compatibility   (15 points)
  - Career goal alignment    (10 points)
  - CGPA alignment           (10 points)
  Total: 100 points
"""
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Proficiency score map
PROFICIENCY_SCORES = {
    "beginner": 1.0,
    "intermediate": 2.0,
    "advanced": 3.0,
}

# Required level score map
REQUIRED_LEVEL_SCORES = {
    "beginner": 1.0,
    "intermediate": 2.0,
    "advanced": 3.0,
}


def _branch_score(student_branch: Optional[str], career_branches: Optional[List[str]]) -> float:
    """
    Returns 0-30 based on branch compatibility.
    30: exact match
    15: related branch
    5: any branch career
    0: incompatible
    """
    if not career_branches:
        return 5.0  # Universal career — some points for everyone
    
    if not student_branch:
        return 5.0  # Unknown branch — small default
    
    branch_upper = student_branch.upper()
    
    # Check exact match
    if branch_upper in [b.upper() for b in career_branches]:
        return 30.0
    
    # Check related branches
    related = {
        "CSE":        ["IT", "ECE"],
        "IT":         ["CSE", "ECE"],
        "ECE":        ["EEE", "IT", "CSE"],
        "EEE":        ["ECE", "MECHANICAL"],
        "MECHANICAL": ["AUTOMOBILE", "EEE"],
        "CIVIL":      [],
        "AUTOMOBILE": ["MECHANICAL"],
    }
    
    related_for_student = related.get(branch_upper, [])
    career_branches_upper = [b.upper() for b in career_branches]
    
    if any(r in career_branches_upper for r in related_for_student):
        return 15.0
    
    return 0.0


def _skill_score(
    student_skills: List[Dict],
    career_skills: List[Dict],
) -> Tuple[float, List[str], List[str]]:
    """
    Returns (score 0-35, matched_skill_names, missing_skill_names).
    Considers proficiency levels.
    """
    if not career_skills:
        return (10.0, [], [])  # Career has no specific skill requirements
    
    # Build student skill map: skill_id -> proficiency_score
    student_map: Dict[str, float] = {}
    for ss in student_skills:
        skill_id = ss.get("skill_id") or (ss.get("skills") or {}).get("id")
        prof = ss.get("proficiency", "beginner").lower()
        if skill_id:
            student_map[skill_id] = PROFICIENCY_SCORES.get(prof, 1.0)
    
    matched_names: List[str] = []
    missing_names: List[str] = []
    total_weight = 0.0
    earned_score = 0.0
    
    for cs in career_skills:
        skill_id = cs.get("skill_id")
        skill_name = (cs.get("skills") or {}).get("name", "Unknown Skill")
        required_level = cs.get("required_level", "beginner").lower()
        weight = float(cs.get("weight", 1.0))
        required_score = REQUIRED_LEVEL_SCORES.get(required_level, 1.0)
        
        total_weight += weight
        
        if skill_id in student_map:
            student_prof_score = student_map[skill_id]
            # Partial credit: (student_prof / required_level) capped at 1.0
            match_ratio = min(student_prof_score / required_score, 1.0)
            earned_score += match_ratio * weight
            if match_ratio >= 0.5:
                matched_names.append(skill_name)
            else:
                missing_names.append(skill_name)
        else:
            missing_names.append(skill_name)
    
    if total_weight == 0:
        return (10.0, [], [])
    
    raw_ratio = earned_score / total_weight
    final_score = raw_ratio * 35.0
    
    return (final_score, matched_names, missing_names)


def _interest_score(
    student_interests: List[str],
    career_industry: Optional[str],
    career_title: str,
) -> float:
    """Returns 0-15 based on interest overlap."""
    if not student_interests:
        return 5.0  # Small default
    
    if not career_industry:
        return 5.0
    
    interests_lower = [i.lower() for i in student_interests]
    career_text = f"{career_title} {career_industry}".lower()
    
    matches = sum(1 for interest in interests_lower if interest in career_text)
    
    if matches == 0:
        return 2.0
    if matches == 1:
        return 8.0
    return 15.0  # Multiple interest matches


def _career_goal_score(
    career_goal: Optional[str],
    career_title: str,
    career_industry: Optional[str],
) -> float:
    """Returns 0-10 based on career goal alignment."""
    if not career_goal:
        return 3.0
    
    goal_lower = career_goal.lower()
    career_text = f"{career_title} {career_industry or ''}".lower()
    
    # Simple keyword overlap
    goal_words = set(goal_lower.split())
    career_words = set(career_text.split())
    overlap = goal_words & career_words
    
    if len(overlap) == 0:
        return 1.0
    if len(overlap) == 1:
        return 5.0
    return 10.0


def _cgpa_score(cgpa: Optional[float], min_cgpa: Optional[float]) -> float:
    """Returns 0-10 based on CGPA meeting career minimums."""
    if min_cgpa is None:
        return 7.0  # No CGPA requirement
    if cgpa is None:
        return 5.0  # Unknown CGPA
    
    if cgpa >= min_cgpa:
        return 10.0
    
    # Partial score
    gap = min_cgpa - cgpa
    if gap <= 0.5:
        return 6.0
    if gap <= 1.0:
        return 3.0
    return 0.0


def _extract_assessment_career_weights(profile: Dict) -> Dict[str, float]:
    """Extracts aggregated career weights from assessment signals or raw answers."""
    signals = profile.get("assessment_signals")
    if isinstance(signals, dict) and "career_weights" in signals:
        return {k: float(v) for k, v in signals["career_weights"].items()}
    
    # Check if raw assessment list is provided
    raw_assessment = profile.get("assessment") or []
    career_weights: Dict[str, float] = {}
    for a in raw_assessment:
        cw = a.get("career_weight")
        if isinstance(cw, dict):
            for car, pts in cw.items():
                try:
                    career_weights[car] = career_weights.get(car, 0.0) + float(pts)
                except (ValueError, TypeError):
                    pass
    return career_weights


def _assessment_career_score(career_title: str, career_weights: Dict[str, float], max_weight: float) -> float:
    """Returns 0-20 based on student assessment signals for this career."""
    if not career_weights or max_weight <= 0:
        return 0.0
    weight = career_weights.get(career_title, 0.0)
    return min(20.0, (weight / max_weight) * 20.0)


def compute_career_matches(
    profile: Dict,
    careers_with_skills: List[Dict],
    top_n: int = 5,
) -> List[Dict]:
    """
    Main entry point: scores all careers against student profile.
    Returns top_n careers sorted by total score, descending.
    
    Args:
        profile: Student profile dict with branch, cgpa, career_goal, assessment
        careers_with_skills: All careers with their skill requirements
        top_n: Number of top careers to return
    
    Returns:
        List of career match dicts with score and breakdown
    """
    student_branch = profile.get("branch")
    student_cgpa = profile.get("cgpa")
    career_goal = profile.get("career_goal")
    student_skills = profile.get("skills") or []
    student_interests = profile.get("interests") or []

    # Extract assessment weights if available
    assessment_weights = _extract_assessment_career_weights(profile)
    max_assessment_weight = max(assessment_weights.values()) if assessment_weights and max(assessment_weights.values()) > 0 else 0.0
    has_assessment = max_assessment_weight > 0

    results = []

    for career in careers_with_skills:
        career_id = career.get("id")
        career_title = career.get("title", "Unknown")
        career_branches = career.get("branches") or []
        career_skills = career.get("career_skills") or []
        career_industry = career.get("industry")
        min_cgpa = career.get("min_cgpa")

        # Compute individual dimension scores
        branch_s = _branch_score(student_branch, career_branches)
        skill_s, matched_skills, missing_skills = _skill_score(student_skills, career_skills)
        interest_s = _interest_score(student_interests, career_industry, career_title)
        goal_s = _career_goal_score(career_goal, career_title, career_industry)
        cgpa_s = _cgpa_score(student_cgpa, min_cgpa)

        if has_assessment:
            # Scaled 6-dimension scoring with assessment (total 100 points)
            assessment_s = _assessment_career_score(career_title, assessment_weights, max_assessment_weight)
            branch_scaled = branch_s * (25.0 / 30.0)
            skill_scaled = skill_s * (25.0 / 35.0)
            interest_scaled = interest_s * (15.0 / 15.0)
            goal_scaled = goal_s * (10.0 / 10.0)
            cgpa_scaled = cgpa_s * (5.0 / 10.0)
            total = branch_scaled + skill_scaled + interest_scaled + goal_scaled + cgpa_scaled + assessment_s

            results.append({
                "career_id": career_id,
                "title": career_title,
                "score": round(total, 2),
                "score_breakdown": {
                    "branch": round(branch_scaled, 2),
                    "skills": round(skill_scaled, 2),
                    "interests": round(interest_scaled, 2),
                    "career_goal": round(goal_scaled, 2),
                    "cgpa": round(cgpa_scaled, 2),
                    "assessment": round(assessment_s, 2),
                },
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
            })
        else:
            # Standard 5-dimension baseline scoring (total 100 points)
            total = branch_s + skill_s + interest_s + goal_s + cgpa_s
            results.append({
                "career_id": career_id,
                "title": career_title,
                "score": round(total, 2),
                "score_breakdown": {
                    "branch": round(branch_s, 2),
                    "skills": round(skill_s, 2),
                    "interests": round(interest_s, 2),
                    "career_goal": round(goal_s, 2),
                    "cgpa": round(cgpa_s, 2),
                },
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
            })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    return results[:top_n]


# ---------------------------------------------------------------------------
# Deterministic Fallback Roadmap & Project Catalog
# Derived directly from reference careers, required skills, and seed data
# ---------------------------------------------------------------------------

CAREER_PROJECT_CATALOG: Dict[str, List[Dict]] = {
    "Software Developer": [
        {
            "title": "Weather API Integration",
            "description": "Fetch data from a public weather API using Python or Node.js and persist queries.",
            "skills_practiced": ["Python", "SQL", "Git"],
            "difficulty": "intermediate",
            "estimated_hours": 15,
        },
        {
            "title": "Student Record Management CLI",
            "description": "Object-oriented program implementing data structures, CRUD operations, and persistent file/database storage.",
            "skills_practiced": ["Java", "C++", "SQL"],
            "difficulty": "beginner",
            "estimated_hours": 20,
        },
    ],
    "Frontend Developer": [
        {
            "title": "Personal Portfolio Website",
            "description": "Build a responsive polytechnic portfolio showcasing projects using modern HTML5, CSS3, and JavaScript.",
            "skills_practiced": ["HTML/CSS", "JavaScript", "Git"],
            "difficulty": "beginner",
            "estimated_hours": 20,
        },
        {
            "title": "Interactive Task Dashboard",
            "description": "Component-driven single page application with dynamic filtering, local persistence, and responsive UI.",
            "skills_practiced": ["JavaScript", "React.js", "HTML/CSS"],
            "difficulty": "intermediate",
            "estimated_hours": 25,
        },
    ],
    "Backend Developer": [
        {
            "title": "Weather API Integration",
            "description": "Fetch and cache data from public REST APIs using server-side Python or Node.js.",
            "skills_practiced": ["Python", "Node.js", "SQL"],
            "difficulty": "intermediate",
            "estimated_hours": 15,
        },
        {
            "title": "RESTful Microservice with Authentication",
            "description": "Containerized backend API with JWT authentication, relational schema migrations, and unit tests.",
            "skills_practiced": ["Python", "SQL", "Docker"],
            "difficulty": "intermediate",
            "estimated_hours": 30,
        },
    ],
    "Full Stack Developer": [
        {
            "title": "Personal Portfolio Website",
            "description": "Build a responsive portfolio using HTML, CSS, and modern frontend techniques.",
            "skills_practiced": ["HTML/CSS", "JavaScript"],
            "difficulty": "beginner",
            "estimated_hours": 20,
        },
        {
            "title": "Full Stack Task & Project Manager",
            "description": "End-to-end web application with React frontend, Node/Python REST API backend, and SQL database.",
            "skills_practiced": ["JavaScript", "React.js", "Node.js", "SQL"],
            "difficulty": "intermediate",
            "estimated_hours": 35,
        },
    ],
    "Data Analyst": [
        {
            "title": "Exploratory Data Analysis Dashboard",
            "description": "Analyze multi-variable public datasets, extract business metrics, and generate visual summary reports.",
            "skills_practiced": ["Python", "SQL", "Data Analysis"],
            "difficulty": "intermediate",
            "estimated_hours": 25,
        },
    ],
    "Cybersecurity Analyst": [
        {
            "title": "Network Packet & Port Vulnerability Scanner",
            "description": "Script automated checks for open ports, common network service vulnerabilities, and security logging.",
            "skills_practiced": ["Networking", "Cybersecurity", "Linux", "Python"],
            "difficulty": "intermediate",
            "estimated_hours": 30,
        },
    ],
    "Embedded Systems Engineer": [
        {
            "title": "Automated Plant Waterer",
            "description": "Use a microcontroller and moisture/temperature sensors to automate watering with threshold alerts.",
            "skills_practiced": ["C", "Microcontrollers", "Circuit Design"],
            "difficulty": "intermediate",
            "estimated_hours": 25,
        },
    ],
    "VLSI Design Engineer": [
        {
            "title": "CMOS Digital Clock & Logic Simulator",
            "description": "Design and simulate combinational and sequential logic circuits using hardware description tools.",
            "skills_practiced": ["VLSI Design", "Circuit Design", "MATLAB"],
            "difficulty": "intermediate",
            "estimated_hours": 30,
        },
    ],
    "Mechanical Design Engineer": [
        {
            "title": "3D Gear Assembly",
            "description": "Design a functional spur and helical gear assembly in SolidWorks with motion simulation.",
            "skills_practiced": ["AutoCAD (Mech)", "SolidWorks", "Manufacturing Tech"],
            "difficulty": "intermediate",
            "estimated_hours": 30,
        },
    ],
    "Automobile Design Engineer": [
        {
            "title": "Vehicle Suspension & Chassis Assembly",
            "description": "Model double-wishbone suspension linkage and stress analysis under dynamic road loads.",
            "skills_practiced": ["SolidWorks", "Vehicle Dynamics", "ANSYS"],
            "difficulty": "intermediate",
            "estimated_hours": 35,
        },
    ],
    "EV Engineer": [
        {
            "title": "Battery Pack State-of-Charge Monitor",
            "description": "Develop sensor circuit and microcontroller firmware to track lithium-ion voltage and temperature.",
            "skills_practiced": ["Electric Vehicles (EV)", "Circuit Design", "Microcontrollers"],
            "difficulty": "intermediate",
            "estimated_hours": 30,
        },
    ],
    "Electrical Design Engineer": [
        {
            "title": "Industrial Solar Power Distribution Panel",
            "description": "Design single-line diagram and circuit protection schemes for commercial solar inverter setup.",
            "skills_practiced": ["Circuit Design", "PCB Design", "MATLAB"],
            "difficulty": "intermediate",
            "estimated_hours": 25,
        },
    ],
    "Structural Engineer": [
        {
            "title": "Reinforced Concrete Building Frame Analysis",
            "description": "Calculate dead/live loads, bending moments, and structural reinforcement for a multi-storey diploma building.",
            "skills_practiced": ["Structural Analysis", "Concrete Tech", "AutoCAD (Civil)"],
            "difficulty": "intermediate",
            "estimated_hours": 30,
        },
    ],
    "Site Engineer": [
        {
            "title": "Site Quantity Survey & Concrete Estimation",
            "description": "Prepare bar bending schedule and material cost estimates from standard civil engineering blueprints.",
            "skills_practiced": ["Estimation & Costing", "Surveying", "AutoCAD (Civil)"],
            "difficulty": "beginner",
            "estimated_hours": 25,
        },
    ],
    "HVAC Engineer": [
        {
            "title": "Commercial Duct Sizing & Cooling Load Calculation",
            "description": "Compute thermal transfer through walls, window solar heat gain, and design air duct layout.",
            "skills_practiced": ["Thermodynamics", "Fluid Mechanics", "AutoCAD (Mech)"],
            "difficulty": "intermediate",
            "estimated_hours": 25,
        },
    ],
    "Manufacturing Engineer": [
        {
            "title": "CNC Machining Process Plan & Fixture Design",
            "description": "Draft operations sheet, G-code toolpaths, and holding fixtures for precision milled components.",
            "skills_practiced": ["Manufacturing Tech", "AutoCAD (Mech)", "SolidWorks"],
            "difficulty": "intermediate",
            "estimated_hours": 25,
        },
    ],
}


def _get_curated_resource_for_skill(skill_name: str) -> str:
    """Returns curated learning platforms or official documentation for a skill."""
    skill_lower = skill_name.lower()
    if "python" in skill_lower:
        return "Python Official Documentation & NPTEL Programming in Python"
    if "java" in skill_lower:
        return "Oracle Java Tutorials & NPTEL Programming in Java"
    if "c++" in skill_lower or "cpp" in skill_lower:
        return "learncpp.com & NPTEL Data Structures in C++"
    if "c" == skill_lower or "c programming" in skill_lower:
        return "NPTEL Problem Solving through Programming in C"
    if "react" in skill_lower:
        return "React.dev Official Interactive Tutorials"
    if "node" in skill_lower:
        return "Node.js Official Documentation & MDN Server Guides"
    if "sql" in skill_lower:
        return "PostgreSQL Official Documentation & SQLZoo Practice"
    if "git" in skill_lower:
        return "Pro Git Book (git-scm.com/book) & GitHub Skills"
    if "docker" in skill_lower:
        return "Docker Official Documentation (docs.docker.com/get-started)"
    if "solidworks" in skill_lower:
        return "SolidWorks Student Tutorials & NPTEL Computer Aided Design"
    if "cad" in skill_lower:
        return "Autodesk Design Academy & Diploma Machine Drawing Curriculum"
    if "ansys" in skill_lower:
        return "Ansys Innovation Courses & Finite Element Analysis Guides"
    if "circuit" in skill_lower or "pcb" in skill_lower:
        return "AllAboutCircuits & KiCad PCB Design Tutorial Series"
    if "microcontroller" in skill_lower:
        return "Arduino / ESP-IDF Documentation & NPTEL Microcontrollers"
    if "vlsi" in skill_lower:
        return "NPTEL CMOS Digital VLSI Design"
    if "matlab" in skill_lower:
        return "MathWorks MATLAB Onramp & Signal Processing Toolbox"
    if "surveying" in skill_lower:
        return "NPTEL Surveying by IIT Roorkee & Field Manuals"
    if "concrete" in skill_lower or "structural" in skill_lower:
        return "Bureau of Indian Standards (IS 456) & NPTEL Structural Engineering"
    if "ev" in skill_lower or "electric vehicle" in skill_lower:
        return "NPTEL Electric Vehicles & SAE India Student Resources"
    if "network" in skill_lower:
        return "Cisco Networking Basics & NPTEL Computer Networks"
    if "cyber" in skill_lower:
        return "Cybrary / TryHackMe & NIST Cybersecurity Framework Guides"
    return "NPTEL Polytechnic & Diploma Curriculum Resources"


def generate_fallback_roadmap(
    target_career: Optional[Dict] = None,
    student_context: Optional[Dict] = None,
    career_catalog: Optional[List[Dict]] = None,
    career_projects: Optional[List[Dict]] = None,
    top_career: Optional[Dict] = None,
) -> Dict:
    """
    Generates a deterministic, structured learning roadmap based on the target career's
    required skills, missing skills, and real project data.
    
    Produces 4 sequential milestones:
      Step 1: Core Fundamentals & Prerequisite Foundations (Weeks 1-4)
      Step 2: Applied Tooling & Practical Competencies (Weeks 5-8)
      Step 3: Advanced Implementation & Engineering Workflows (Weeks 9-12)
      Step 4: Capstone Portfolio Project & Industry Readiness (Weeks 13-16)

    Compatible with CareerAnalysisAIResponse and roadmap.html.
    """
    effective_target = target_career or top_career or {}
    student_context = student_context or {}
    career_title = effective_target.get("title", "Target Engineering Role")
    branch = student_context.get("branch") or "Diploma Engineering"
    missing_skills = list(effective_target.get("missing_skills") or [])
    matched_skills = list(effective_target.get("matched_skills") or [])
    all_target_skills = matched_skills + missing_skills

    # 1. Distribute skills across milestones
    # Step 1: Foundational missing skills (or branch fundamentals)
    # Step 2: Intermediate missing skills
    # Step 3: Advanced implementation skills
    # Step 4: Capstone synthesis
    step1_skills: List[str] = []
    step2_skills: List[str] = []
    step3_skills: List[str] = []
    step4_skills: List[str] = []

    if missing_skills:
        n = len(missing_skills)
        if n == 1:
            step1_skills = [missing_skills[0]]
            step2_skills = [missing_skills[0]]
            step3_skills = matched_skills[:2] if matched_skills else [missing_skills[0]]
            step4_skills = [f"{career_title} Capstone Integration"]
        elif n == 2:
            step1_skills = [missing_skills[0]]
            step2_skills = [missing_skills[1]]
            step3_skills = missing_skills
            step4_skills = [f"{career_title} Capstone Integration"]
        elif n == 3:
            step1_skills = [missing_skills[0]]
            step2_skills = [missing_skills[1]]
            step3_skills = [missing_skills[2]]
            step4_skills = missing_skills[:2]
        else:
            # 4 or more
            step1_skills = missing_skills[:1]
            step2_skills = missing_skills[1:3]
            step3_skills = missing_skills[3:]
            step4_skills = missing_skills[:3]
    else:
        # Student matched all baseline skills
        step1_skills = matched_skills[:2] if matched_skills else [f"{branch} Core Principles"]
        step2_skills = matched_skills[2:4] if len(matched_skills) > 2 else matched_skills
        step3_skills = [f"Advanced {career_title} Practices"]
        step4_skills = [f"Industry Production Deployment"]

    # 2. Curate resources for each step
    def _resources_for(skills: List[str]) -> List[str]:
        res = []
        for s in skills:
            r = _get_curated_resource_for_skill(s)
            if r not in res:
                res.append(r)
        if not res:
            res.append(f"NPTEL & State Board Technical Education Syllabi for {branch}")
        return res[:3]

    step1_res = _resources_for(step1_skills)
    step2_res = _resources_for(step2_skills)
    step3_res = _resources_for(step3_skills)
    step4_res = [
        "GitHub Portfolio Best Practices & Technical Documentation",
        f"Diploma Polytechnic Placement & Industry Interview Preparation ({branch})"
    ]

    # 3. Assemble the 4 sequenced roadmap steps
    s1_names = ", ".join(step1_skills) if step1_skills else "Core concepts"
    s2_names = ", ".join(step2_skills) if step2_skills else "Applied tools"
    s3_names = ", ".join(step3_skills) if step3_skills else "System architecture"

    roadmap_steps = [
        {
            "step_number": 1,
            "title": "Core Technical Foundations & Prerequisites",
            "description": f"Master the fundamental syntax, theoretical principles, and core competencies required for {career_title}, focusing on {s1_names}.",
            "duration_weeks": 4,
            "skills_gained": step1_skills,
            "resources": step1_res,
        },
        {
            "step_number": 2,
            "title": "Applied Tooling & Practical Competencies",
            "description": f"Apply essential industry tooling, libraries, and workflows to solve practical exercises in {s2_names}.",
            "duration_weeks": 4,
            "skills_gained": step2_skills,
            "resources": step2_res,
        },
        {
            "step_number": 3,
            "title": "Advanced Implementation & System Integration",
            "description": f"Deepen competence in production standards, error handling, performance optimization, and architectural integration ({s3_names}).",
            "duration_weeks": 4,
            "skills_gained": step3_skills,
            "resources": step3_res,
        },
        {
            "step_number": 4,
            "title": "Capstone Portfolio Project & Industry Readiness",
            "description": f"Synthesize all acquired skills into a complete end-to-end project demonstrating qualifying readiness for entry-level {career_title} roles.",
            "duration_weeks": 4,
            "skills_gained": step4_skills or [career_title],
            "resources": step4_res,
        },
    ]

    # 4. Resolve beginner-friendly projects from database catalog or fallback catalog
    projects: List[Dict] = []
    if career_projects:
        projects = list(career_projects)
    elif career_title in CAREER_PROJECT_CATALOG:
        projects = CAREER_PROJECT_CATALOG[career_title]
    else:
        # Fallback to branch-aligned project
        projects = [
            {
                "title": f"{career_title} Practical Portfolio Project",
                "description": f"Build a comprehensive, demonstrable project integrating {s1_names} and {s2_names}.",
                "skills_practiced": all_target_skills[:4] or [branch],
                "difficulty": "intermediate",
                "estimated_hours": 25,
            }
        ]

    # 5. Build detailed skill gaps items
    skill_gaps = []
    for idx, s in enumerate(missing_skills):
        skill_gaps.append({
            "skill_name": s,
            "current_level": "none",
            "required_level": "intermediate" if idx > 0 else "advanced",
            "priority": "high" if idx < 2 else "medium",
            "learning_resource": _get_curated_resource_for_skill(s),
        })

    return {
        "career_target": career_title,
        "roadmap_steps": roadmap_steps,
        "project_recommendations": projects,
        "skill_gaps": skill_gaps,
        "priority_skills": missing_skills[:4] if missing_skills else matched_skills[:4],
    }


