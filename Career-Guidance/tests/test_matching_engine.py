"""
Unit tests for deterministic career matching engine.
Verifies scoring logic, weights, proficiency scaling, and edge case resilience.
"""
import pytest
from backend.services.matching_engine import (
    _branch_score,
    _skill_score,
    _interest_score,
    _career_goal_score,
    _cgpa_score,
    compute_career_matches,
)


def test_branch_score_exact_match():
    assert _branch_score("CSE", ["CSE", "IT"]) == 30.0
    assert _branch_score("MECHANICAL", ["MECHANICAL"]) == 30.0


def test_branch_score_related_match():
    # ECE is related to CSE/IT
    assert _branch_score("CSE", ["ECE"]) == 15.0
    # AUTOMOBILE is related to MECHANICAL
    assert _branch_score("AUTOMOBILE", ["MECHANICAL"]) == 15.0


def test_branch_score_incompatible():
    assert _branch_score("CIVIL", ["CSE", "IT"]) == 0.0


def test_branch_score_universal():
    assert _branch_score("CSE", []) == 5.0
    assert _branch_score(None, ["CSE"]) == 5.0


def test_skill_score_full_credit():
    student_skills = [
        {"skill_id": "sk-1", "proficiency": "advanced"}
    ]
    career_skills = [
        {"skill_id": "sk-1", "required_level": "intermediate", "weight": 1.0, "skills": {"name": "Python"}}
    ]
    score, matched, missing = _skill_score(student_skills, career_skills)
    assert score == 35.0
    assert "Python" in matched
    assert len(missing) == 0


def test_skill_score_partial_credit():
    student_skills = [
        {"skill_id": "sk-1", "proficiency": "beginner"}
    ]
    career_skills = [
        {"skill_id": "sk-1", "required_level": "advanced", "weight": 1.0, "skills": {"name": "Python"}}
    ]
    score, matched, missing = _skill_score(student_skills, career_skills)
    # beginner (1.0) / advanced (3.0) = 1/3 * 35.0 ~ 11.67
    assert 11.0 < score < 12.0
    # ratio < 0.5 so missing
    assert "Python" in missing


def test_skill_score_empty_skills():
    score, matched, missing = _skill_score([], [])
    assert score == 10.0
    assert matched == []
    assert missing == []


def test_interest_score():
    assert _interest_score(["frontend", "software"], "IT Software", "Frontend Developer") == 15.0
    assert _interest_score([], "IT Software", "Frontend Developer") == 5.0
    assert _interest_score(["Automobiles"], "Civil Construction", "Site Engineer") == 2.0


def test_career_goal_score():
    assert _career_goal_score("Full Stack Developer", "Full Stack Developer", "IT") == 10.0
    assert _career_goal_score(None, "Frontend Developer", "IT") == 3.0


def test_cgpa_score():
    assert _cgpa_score(8.5, 7.0) == 10.0
    assert _cgpa_score(6.8, 7.0) == 6.0   # within 0.5
    assert _cgpa_score(5.5, 7.0) == 0.0   # gap > 1.0
    assert _cgpa_score(None, 7.0) == 5.0


def test_compute_career_matches_ranking():
    profile = {
        "branch": "CSE",
        "cgpa": 8.0,
        "career_goal": "Software Engineer",
        "skills": [
            {"skill_id": "sk-py", "proficiency": "intermediate"},
            {"skill_id": "sk-sql", "proficiency": "beginner"},
        ],
        "interests": ["Coding", "Web Design"],
    }

    careers = [
        {
            "id": "car-1",
            "title": "Software Developer",
            "branches": ["CSE", "IT"],
            "industry": "IT",
            "min_cgpa": 7.0,
            "career_skills": [
                {"skill_id": "sk-py", "required_level": "intermediate", "weight": 1.5, "skills": {"name": "Python"}},
                {"skill_id": "sk-sql", "required_level": "beginner", "weight": 1.0, "skills": {"name": "SQL"}},
            ],
        },
        {
            "id": "car-2",
            "title": "Site Engineer",
            "branches": ["CIVIL"],
            "industry": "Construction",
            "min_cgpa": 6.0,
            "career_skills": [
                {"skill_id": "sk-survey", "required_level": "intermediate", "weight": 1.0, "skills": {"name": "Surveying"}},
            ],
        },
    ]

    matches = compute_career_matches(profile, careers, top_n=2)
    assert len(matches) == 2
    # Software Developer should rank first for CSE student
    assert matches[0]["career_id"] == "car-1"
    assert matches[0]["score"] > matches[1]["score"]
    assert "score_breakdown" in matches[0]
    assert 0 <= matches[0]["score"] <= 100
