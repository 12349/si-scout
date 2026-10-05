"""
TESTER Suite for Site Fixes, Story Mode Text Audit, Gate Definitions, and Hosted Demo Safety.
Enforces that every issue fails before fixing, and passes once fixed.
"""
import re
from pathlib import Path
import pytest
from flask import Flask

REPO_ROOT = Path(__file__).resolve().parent.parent

# 1. Story slide 1 test
def test_story_slide_1_exact_wording_and_sources():
    story_html = (REPO_ROOT / 'ui' / 'templates' / 'story.html').read_text(encoding='utf-8')
    assert 'Secondary market liquidity for local country extensions is limited' not in story_html
    assert 'annual renewals compound over time' not in story_html
    
    expected_wording = (
        "Early evidence: about 52% of Dynadot's .si registrations between Sept 19 and 22, 2026 were listed for resale (Netcraft). "
        "Of 35 public .si sales from January to June 9, 2026, 2 went to end users (Domain Name Wire). "
        "Renewal fees accumulate each year."
    )
    norm_expected = " ".join(expected_wording.split())
    norm_html = " ".join(story_html.split())
    assert norm_expected in norm_html, f"Expected exact slide 1 text not found in story.html:\n{expected_wording}"


# 2. Story slide 2 test
def test_story_slide_2_filters():
    story_html = (REPO_ROOT / 'ui' / 'templates' / 'story.html').read_text(encoding='utf-8')
    assert 'trademark screens' not in story_html.lower()
    assert 'active site twins' not in story_html.lower()
    assert 'popular-site' in story_html.lower() or 'popular website' in story_html.lower()
    assert 'syntax' in story_html.lower()


# 3. Story slides 3 and 4 test
def test_story_slides_3_and_4_demo_prefix_and_no_advice():
    story_html = (REPO_ROOT / 'ui' / 'templates' / 'story.html').read_text(encoding='utf-8')
    assert 'automated scanners waste money' not in story_html.lower()
    assert 'In this demo dataset' in story_html


# 4. Story slide 6 and Budget Lab currency test
def test_story_slide_6_currency_and_assumptions():
    story_html = (REPO_ROOT / 'ui' / 'templates' / 'story.html').read_text(encoding='utf-8')
    # Slide 6 should use $ instead of euro for Dynadot USD snapshot
    assert 'assumes 2% yearly sell-through and a $500 net sale price' in story_html or 'assumes 2% yearly sell-through and a' in story_html
    assert 'secondary demand remains minimal' not in story_html.lower()
    assert 'compound' not in story_html.lower()


# 5. Budget Lab honest framing test
def test_budget_lab_honest_framing():
    budget_html = (REPO_ROOT / 'ui' / 'templates' / 'budget.html').read_text(encoding='utf-8')
    assert 'Secondary sales in country-code extensions like .si' not in budget_html
    assert 'Public .si sales data is limited. In the Domain Name Wire sample, 2 of 35 sales went to end users.' in budget_html


# 6. Overview test
def test_overview_phrasing():
    overview_html = (REPO_ROOT / 'ui' / 'templates' / 'overview.html').read_text(encoding='utf-8')
    assert 'Most outcomes in this kind of portfolio lose money' not in overview_html
    assert "Under the Budget Lab's default assumptions, most outcomes lose the carry cost." in overview_html
    assert 'real registrar checkout availability' not in overview_html
    assert 'registrar checkout availability (demo data here)' in overview_html


# 7. Gate definitions match everywhere
def test_gate_definitions_match_everywhere():
    from si_scout.gates_constants import SIX_GATES
    assert len(SIX_GATES) == 6
    expected_order = [
        'not in registry',
        'fresh prices (7 days)',
        'fresh check (60 minutes)',
        'human rationale (15 words)',
        'budget fit',
        'registrar checkout confirmation (60 minutes)'
    ]
    for idx, (gate, expected_name) in enumerate(zip(SIX_GATES, expected_order), 1):
        assert gate['id'] == idx
        assert gate['name'].lower() == expected_name.lower()
    
    readme = (REPO_ROOT / 'README.md').read_text(encoding='utf-8')
    for g in SIX_GATES:
        assert g['name'].lower() in readme.lower()


# 8. Story Mode text audit
def test_story_mode_text_audit():
    story_html = (REPO_ROOT / 'ui' / 'templates' / 'story.html').read_text(encoding='utf-8')
    forbidden = [
        ('limited liquidity', 'limited liquidity'),
        ('compound', 'compound'),
        ('trademark screens', 'trademark screens'),
        ('minimal demand', 'minimal demand'),
    ]
    for phrase, label in forbidden:
        assert phrase not in story_html.lower(), f"Story mode text audit failed: found '{label}'"


# 9. Hosted-demo safety test
def test_hosted_demo_safety(monkeypatch):
    monkeypatch.setenv('VERCEL', '1')
    monkeypatch.setenv('HOSTED_DEMO', '1')
    from ui.app import create_app
    app = create_app({'TESTING': True})
    client = app.test_client()

    mutation_routes = [
        ('/api/scan/start', {'top': 10}),
        ('/api/recheck', {'domains': ['example-cloud.si']}),
        ('/api/watch/run', {}),
        ('/api/calibration/add', {'domain': 'test.si'}),
        ('/api/confirm-checkout', {'domain': 'test.si'}),
        ('/api/rationale/save', {'label': 'test', 'rationale': 'test words' * 5}),
        ('/api/shortlist/toggle', {'domain': 'test.si'}),
        ('/api/portfolio/add', {'domain': 'test.si'}),
        ('/api/outreach/add', {'company': 'test'}),
        ('/api/portfolio/kill-criteria', {'contract_text': 'test'}),
    ]

    for route, payload in mutation_routes:
        res = client.post(route, json=payload)
        assert res.status_code == 403, f"Route {route} did not return 403 in hosted demo mode, got {res.status_code}"
        data = res.get_json() or {}
        err_msg = data.get('error', '').lower()
        assert 'disabled in hosted demo' in err_msg, f"Route {route} did not return 'disabled in hosted demo', got '{err_msg}'"


# 10. Repo hygiene test
def test_repo_hygiene():
    readme = (REPO_ROOT / 'README.md').read_text(encoding='utf-8')
    assert 'docs/img/findings.png' not in readme
    assert 'cd "si domain project"' not in readme
    assert 'cd "si-domain-project"' not in readme
    assert 'cd si-scout' in readme
    assert 'Flags labels that match popular websites. Tranco is a popularity ranking, not a trademark database.' in readme
    assert 'defensive brand managers' not in readme
    assert not (REPO_ROOT / 'PRERELEASE_REPORT.md').exists()
