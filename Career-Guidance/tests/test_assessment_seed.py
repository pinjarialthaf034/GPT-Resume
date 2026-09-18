"""
Unit tests to verify expanded assessment seed coverage in database/seed_data.sql.
Verifies 10 questions across multiple diploma engineering disciplines and valid career weights.
"""
import re
from pathlib import Path
import json
import pytest


def test_assessment_seed_contains_10_questions():
    seed_path = Path("database/seed_data.sql")
    content = seed_path.read_text(encoding="utf-8")

    # Match INSERT INTO assessment_questions (question_text, category, ...)
    matches = re.findall(
        r"INSERT INTO assessment_questions\s*\([^)]+\)\s*VALUES\s*\('([^']+)',\s*'([^']+)'",
        content,
        re.IGNORECASE,
    )
    assert len(matches) >= 10, f"Expected at least 10 questions, found {len(matches)}"

    categories = {cat for _, cat in matches}
    expected_categories = {"Logic", "Hardware", "Environment", "Analytics", "Mechanical", "Civil", "Electrical", "Automotive", "Security", "Design"}
    for cat in expected_categories:
        assert cat in categories, f"Category '{cat}' missing from assessment questions"


def test_assessment_options_reference_valid_careers():
    seed_path = Path("database/seed_data.sql")
    content = seed_path.read_text(encoding="utf-8")

    # Extract all careers inserted in seed_data.sql
    career_matches = re.findall(
        r"INSERT INTO careers\s*\([^)]+\)\s*VALUES\s*\('([^']+)'",
        content,
        re.IGNORECASE,
    )
    seeded_career_titles = set(career_matches)
    assert len(seeded_career_titles) >= 15, "Expected at least 15 seeded career titles"

    # Extract option weights: (qX, '...', '{career_weight}'...)
    option_matches = re.findall(
        r"\(\s*q\d+,\s*'[^']+',\s*'({[^}]*})'",
        content,
        re.IGNORECASE,
    )
    assert len(option_matches) >= 30, f"Expected at least 30 options, found {len(option_matches)}"

    for weight_json in option_matches:
        weights = json.loads(weight_json)
        assert isinstance(weights, dict)
        for career_name, weight_val in weights.items():
            assert career_name in seeded_career_titles, f"Career '{career_name}' in assessment weights is not a seeded career!"
            assert isinstance(weight_val, (int, float))
            assert weight_val > 0
