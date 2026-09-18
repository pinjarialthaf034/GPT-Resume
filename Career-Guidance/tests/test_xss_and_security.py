"""
Unit and regression tests for Frontend XSS defenses and input sanitization.
Verifies character encoding for malicious injection vectors:
- <script>alert(1)</script>
- <img src=x onerror=alert(1)>
- "><script>alert(1)</script>
Also statically verifies that frontend HTML templates escape dynamic interpolated variables.
"""
import re
from pathlib import Path
import pytest


def escape_html(text):
    """Python implementation of the frontend js/api.js escapeHtml utility."""
    if text is None:
        return ""
    html_map = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
    }
    return re.sub(r'[&<>"\']', lambda m: html_map[m.group(0)], str(text))


def test_escape_script_tag_injection():
    malicious = "<script>alert(1)</script>"
    escaped = escape_html(malicious)
    assert "<script>" not in escaped
    assert "</script>" not in escaped
    assert escaped == "&lt;script&gt;alert(1)&lt;/script&gt;"


def test_escape_img_onerror_injection():
    malicious = "<img src=x onerror=alert(1)>"
    escaped = escape_html(malicious)
    assert "<img" not in escaped
    assert escaped == "&lt;img src=x onerror=alert(1)&gt;"


def test_escape_attribute_breakout_injection():
    malicious = '"><script>alert(1)</script>'
    escaped = escape_html(malicious)
    assert '"><script>' not in escaped
    assert escaped == "&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;"


def test_escape_html_handles_null_and_numbers():
    assert escape_html(None) == ""
    assert escape_html(123) == "123"
    assert escape_html(85.5) == "85.5"


def test_results_html_escapes_dynamic_variables():
    results_path = Path("frontend/results.html")
    content = results_path.read_text(encoding="utf-8")
    
    # Must use escapeHtml on critical dynamic values
    assert "escapeHtml(c.title)" in content
    assert "escapeHtml(c.reason)" in content
    assert "escapeHtml(s)" in content
    assert "escapeHtml(g.skill_name)" in content


def test_admin_html_escapes_dynamic_variables():
    admin_path = Path("frontend/admin.html")
    content = admin_path.read_text(encoding="utf-8")
    
    assert "escapeHtml(c.title)" in content
    assert "escapeHtml(s.name)" in content


def test_roadmap_html_escapes_dynamic_variables():
    roadmap_path = Path("frontend/roadmap.html")
    content = roadmap_path.read_text(encoding="utf-8")
    
    assert "escapeHtml(step.title)" in content
    assert "escapeHtml(step.description)" in content


def test_explorer_html_escapes_dynamic_variables():
    explorer_path = Path("frontend/explorer.html")
    content = explorer_path.read_text(encoding="utf-8")
    
    assert "escapeHtml(c.title)" in content
    assert "escapeHtml(p.title)" in content
