"""
Tests for the Adaptive Career Discovery Assessment Engine.
Verifies:
1. Phase 1 broad discovery progression.
2. Phase 2 intermediate interest mapping calculation.
3. Phase 3 adaptive branching according to student signals.
4. Neutrality of "I am not sure yet" options.
5. Deterministic session state and next-question resolution.
6. Assessment submission and persistence of assessment_signals.
7. Matching engine ranking influenced by assessment signals without breaking non-assessment workflows.
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.deps import get_service_supabase
from backend.services.matching_engine import compute_career_matches
from backend.repositories.profile_repo import ProfileRepository

client = TestClient(app)


def test_matching_engine_with_assessment_signals():
    """Confirms assessment signals positively influence matching engine scores."""
    profile = {
        "branch": "MECHANICAL",
        "cgpa": 8.0,
        "career_goal": "Tech Careers",
        "skills": [],
        "interests": ["Coding"],
        "assessment_signals": {
            "career_weights": {
                "Software Developer": 10.0,
                "Frontend Developer": 8.0,
            }
        }
    }

    careers = [
        {
            "id": "car-sde",
            "title": "Software Developer",
            "branches": ["CSE", "IT"],
            "industry": "IT",
            "min_cgpa": 7.0,
            "career_skills": [],
        },
        {
            "id": "car-site",
            "title": "Site Engineer",
            "branches": ["CIVIL"],
            "industry": "Construction",
            "min_cgpa": 6.0,
            "career_skills": [],
        },
    ]

    matches = compute_career_matches(profile, careers, top_n=2)
    assert len(matches) == 2
    # Software Developer should score higher due to strong assessment signal even for Mechanical student
    assert matches[0]["title"] == "Software Developer"
    assert "assessment" in matches[0]["score_breakdown"]
    assert matches[0]["score_breakdown"]["assessment"] == 20.0


def test_neutrality_of_unsure_answers():
    """Selecting 'I am not sure yet' should produce 0 domain and career points."""
    mock_db = MagicMock()
    repo = ProfileRepository(mock_db)

    # Mock questions
    mock_db.table().select().order().execute.return_value.data = [
        {
            "id": "q1",
            "question_text": "Sample Question",
            "category": "Logic",
            "phase": "broad",
            "domain": "software",
            "order_num": 1,
            "assessment_options": [
                {"id": "opt-software", "option_text": "Software", "career_weight": {"Software Developer": 3}, "domain_weight": {"software": 10}},
                {"id": "opt-unsure", "option_text": "🤷 I am not sure yet", "career_weight": {}, "domain_weight": {}}
            ]
        }
    ]

    signals = repo.calculate_assessment_signals([{"question_id": "q1", "option_id": "opt-unsure"}])
    # Scores should be 0 across domains
    assert all(d["raw_score"] == 0 for d in signals["all_domain_signals"])
    assert signals["career_weights"] == {}


def test_adaptive_branching_software_vs_hardware():
    """Branching adapts question selection based on dominant interest domain."""
    mock_db = MagicMock()
    repo = ProfileRepository(mock_db)

    mock_db.table().select().order().execute.return_value.data = [
        # 2 Broad questions
        {"id": "q1", "question_text": "Q1", "phase": "broad", "domain": "software", "order_num": 1, "assessment_options": [
            {"id": "opt-sw1", "career_weight": {"Software Developer": 3}, "domain_weight": {"software": 10}}
        ]},
        {"id": "q2", "question_text": "Q2", "phase": "broad", "domain": "software", "order_num": 2, "assessment_options": [
            {"id": "opt-sw2", "career_weight": {"Software Developer": 3}, "domain_weight": {"software": 10}}
        ]},
        # Deep dive questions
        {"id": "q-deep-sw", "question_text": "Deep Software Q", "phase": "deep_dive", "domain": "software", "order_num": 6, "assessment_options": []},
        {"id": "q-deep-elec", "question_text": "Deep Elec Q", "phase": "deep_dive", "domain": "electronics_embedded", "order_num": 7, "assessment_options": []},
    ]

    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    try:
        # Submit broad answers indicating strong software preference
        res = client.post("/api/profile/assessment/next", json={
            "answers": [
                {"question_id": "q1", "option_id": "opt-sw1"},
                {"question_id": "q2", "option_id": "opt-sw2"},
            ]
        })
        assert res.status_code == 200
        data = res.json()["data"]
        # Immediately after broad phase completes -> Transition phase
        assert data["phase"] == "transition"
        assert len(data["top_domains"]) > 0
        assert data["top_domains"][0]["domain"] == "software"

        # Next request with an acknowledged deep dive transition
        res2 = client.post("/api/profile/assessment/next", json={
            "answers": [
                {"question_id": "q1", "option_id": "opt-sw1"},
                {"question_id": "q2", "option_id": "opt-sw2"},
                # Student took first deep dive answer
                {"question_id": "dummy", "option_id": "dummy-opt"}
            ]
        })
        assert res2.status_code == 200
        data2 = res2.json()["data"]
        # Should pick software deep dive question first!
        assert data2["phase"] == "deep_dive"
        assert data2["question"]["domain"] == "software"
    finally:
        app.dependency_overrides.clear()


def test_repeated_unsure_answers_progression():
    """Confirms student choosing 'Not sure yet' repeatedly progresses safely without crashing."""
    mock_db = MagicMock()
    mock_db.table().select().order().execute.return_value.data = [
        {"id": "q1", "question_text": "Q1", "phase": "broad", "domain": "software", "order_num": 1, "assessment_options": [{"id": "opt-u1", "option_text": "🤷 I am not sure yet"}]},
        {"id": "q2", "question_text": "Q2", "phase": "broad", "domain": "software", "order_num": 2, "assessment_options": [{"id": "opt-u2", "option_text": "🤷 I am not sure yet"}]},
        {"id": "q3", "question_text": "Q3", "phase": "deep_dive", "domain": "software", "order_num": 6, "assessment_options": []},
    ]

    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    try:
        res = client.post("/api/profile/assessment/next", json={
            "answers": [
                {"question_id": "q1", "option_id": "opt-u1"},
                {"question_id": "q2", "option_id": "opt-u2"},
            ]
        })
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["phase"] == "transition"
        # Progresses without crashing, all signals neutral
        for dom in data["top_domains"]:
            assert dom["signal"] == 0.0
    finally:
        app.dependency_overrides.clear()


def test_branching_determinism():
    """Confirms that identical answers always produce identical next question."""
    mock_db = MagicMock()
    mock_db.table().select().order().execute.return_value.data = [
        {"id": "q1", "question_text": "Q1", "phase": "broad", "domain": "software", "order_num": 1, "assessment_options": [{"id": "opt-1", "career_weight": {"Software Developer": 2}, "domain_weight": {"software": 5}}]},
        {"id": "q2", "question_text": "Q2", "phase": "broad", "domain": "software", "order_num": 2, "assessment_options": []},
    ]

    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    try:
        answers = [{"question_id": "q1", "option_id": "opt-1"}]
        res1 = client.post("/api/profile/assessment/next", json={"answers": answers})
        res2 = client.post("/api/profile/assessment/next", json={"answers": answers})
        assert res1.json()["data"]["question"]["id"] == res2.json()["data"]["question"]["id"]
    finally:
        app.dependency_overrides.clear()


def test_question_1_covers_all_major_domains_without_career_labels():
    """Confirms Question 1 contains activities representing all domains without career labels."""
    from pathlib import Path
    import re

    seed_content = Path("database/seed_data.sql").read_text(encoding="utf-8")
    # Match Q1 block including options
    q1_match = re.search(r"Imagine your college gives you a free project.+?\(q1, '🤷 I am not sure yet'", seed_content, re.DOTALL)
    assert q1_match is not None, "Question 1 not found in seed_data.sql"
    q1_block = q1_match.group(0)

    # Must contain options covering major activities
    assert "Create something people can use on a phone or computer" in q1_block
    assert "Look at information and discover useful patterns" in q1_block
    assert "Make a computer system safer and harder to misuse" in q1_block
    assert "Build something using sensors, wires, or electronic parts" in q1_block
    assert "Improve how a machine, vehicle, or physical product works" in q1_block
    assert "Design or improve a building, space, or physical structure" in q1_block
    assert "Find a way to make a process faster or more automatic" in q1_block
    assert "I am not sure yet" in q1_block

    # Confirm student sees activities, NOT career labels
    forbidden_labels = ["Software Development", "Data Analytics", "Cybersecurity Analyst", "Embedded Systems", "Mechanical Engineering"]
    for label in forbidden_labels:
        assert f"'{label}'" not in q1_block, f"Forbidden career label '{label}' found in Q1 option text!"


def test_fresh_assessment_returns_question_1_immediately():
    """With empty answers, /assessment/next must immediately return Question 1."""
    mock_db = MagicMock()
    mock_db.table().select().order().execute.return_value.data = [
        {"id": "q1", "question_text": "Imagine your college gives you a free project...", "phase": "broad", "domain": "software", "order_num": 1, "assessment_options": []},
        {"id": "q2", "question_text": "Q2", "phase": "broad", "domain": "electronics_embedded", "order_num": 2, "assessment_options": []},
    ]

    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    try:
        res = client.post("/api/profile/assessment/next", json={"answers": []})
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["phase"] == "broad"
        assert data["current_step"] == 1
        assert data["question"]["id"] == "q1"
        assert "Imagine your college gives you a free project" in data["question"]["question_text"]
    finally:
        app.dependency_overrides.clear()


def test_transition_screen_is_neutral_and_spoil_free():
    """Transition screen after Phase 1 must NOT reveal domain names to the student."""
    mock_db = MagicMock()
    mock_db.table().select().order().execute.return_value.data = [
        {"id": f"q{i}", "question_text": f"Q{i}", "phase": "broad", "domain": "software", "order_num": i, "assessment_options": [
            {"id": f"opt-{i}", "career_weight": {"Software Developer": 3}, "domain_weight": {"software": 10}}
        ]} for i in range(1, 6)
    ]

    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    try:
        answers = [{"question_id": f"q{i}", "option_id": f"opt-{i}"} for i in range(1, 6)]
        res = client.post("/api/profile/assessment/next", json={"answers": answers, "transition_acknowledged": False})
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["phase"] == "transition"
        # Message must be neutral and encouraging without spoiling domains
        msg = data["encouragement_message"]
        assert "Nice! We're getting a better picture" in msg
        assert "clues" in msg
        for domain in ["Software", "Data", "Cybersecurity", "Mechanical", "Civil", "Electrical"]:
            assert domain not in msg, f"Domain name '{domain}' leaked in transition encouragement message!"
    finally:
        app.dependency_overrides.clear()


def test_software_vs_mechanical_students_receive_different_deep_dives():
    """Two students with different answers receive distinct adaptive questions."""
    mock_db = MagicMock()
    mock_db.table().select().order().execute.return_value.data = [
        # Broad Qs
        {"id": "q1", "question_text": "Q1", "phase": "broad", "domain": "software", "order_num": 1, "assessment_options": [
            {"id": "opt-sw", "career_weight": {"Software Developer": 3}, "domain_weight": {"software": 10}},
            {"id": "opt-mech", "career_weight": {"Mechanical Design Engineer": 3}, "domain_weight": {"mechanical_design": 10}},
        ]},
        # Deep Dive Software Q
        {"id": "q-deep-sw", "question_text": "Deep Software", "phase": "deep_dive", "domain": "software", "order_num": 6, "assessment_options": []},
        # Deep Dive Mech Q
        {"id": "q-deep-mech", "question_text": "Deep Mech", "phase": "deep_dive", "domain": "mechanical_design", "order_num": 7, "assessment_options": []},
    ]

    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    try:
        # Student A chooses Software
        res_a = client.post("/api/profile/assessment/next", json={
            "answers": [{"question_id": "q1", "option_id": "opt-sw"}],
            "transition_acknowledged": True,
        })
        # Student B chooses Mechanical
        res_b = client.post("/api/profile/assessment/next", json={
            "answers": [{"question_id": "q1", "option_id": "opt-mech"}],
            "transition_acknowledged": True,
        })

        assert res_a.json()["data"]["question"]["id"] == "q-deep-sw"
        assert res_b.json()["data"]["question"]["id"] == "q-deep-mech"
        assert res_a.json()["data"]["question"]["id"] != res_b.json()["data"]["question"]["id"]
    finally:
        app.dependency_overrides.clear()


def test_assessment_completes_in_exactly_10_questions():
    """Submitting 10 answers signals completion with is_complete=True."""
    mock_db = MagicMock()
    mock_db.table().select().order().execute.return_value.data = [
        {"id": f"q{i}", "question_text": f"Q{i}", "phase": "broad" if i <= 5 else "deep_dive", "domain": "software", "order_num": i, "assessment_options": []}
        for i in range(1, 16)
    ]

    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    try:
        ten_answers = [{"question_id": f"q{i}", "option_id": f"opt-{i}"} for i in range(1, 11)]
        res = client.post("/api/profile/assessment/next", json={"answers": ten_answers, "transition_acknowledged": True})
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["is_complete"] is True
        assert data["phase"] == "complete"
        assert data["progress_percent"] == 100.0
    finally:
        app.dependency_overrides.clear()


def test_no_gemini_called_during_assessment_progression():
    """Confirms no Gemini API calls are made during questionnaire progression."""
    from unittest.mock import patch
    from backend.ai.gemini_provider import GeminiProvider

    mock_db = MagicMock()
    mock_db.table().select().order().execute.return_value.data = [
        {"id": "q1", "question_text": "Q1", "phase": "broad", "domain": "software", "order_num": 1, "assessment_options": []}
    ]

    app.dependency_overrides[get_service_supabase] = lambda: mock_db
    try:
        with patch.object(GeminiProvider, "_call_with_retry") as mock_gemini:
            res = client.post("/api/profile/assessment/next", json={"answers": []})
            assert res.status_code == 200
            assert mock_gemini.call_count == 0
    finally:
        app.dependency_overrides.clear()

