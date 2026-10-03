"""
Test suite for Release Hardening & Policy Enforcement (B1-B10, Bugs, Release Safety).
Written first by TESTER to enforce failure on existing un-hardened code.
"""
import json
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).parent.parent

def test_anti_forecast_extended_forbidden_terms():
    forbidden_patterns = [
        (r'\b(h1|h2|h3)[^>]*>[^<]*\bhigh\s+risk\b', 'High risk as headline'),
        (r'#+\s+.*\bhigh\s+risk\b', 'High risk as markdown heading'),
        (r'\bradical\s+honesty\b', 'Radical honesty'),
        (r'\bquietly\s+consume\b', 'Quietly consume'),
        (r'\bauthoritative\s+empirical\s+snapshot\b', 'Authoritative empirical snapshot'),
        (r'\bfading\b', 'Fading'),
        (r'\bstabilizing\b', 'Stabilizing'),
        (r'\bstatistical\s+confidence\b', 'Statistical confidence'),
    ]

    scan_targets = [
        REPO_ROOT / 'ui' / 'templates',
        REPO_ROOT / 'ui' / 'static',
        REPO_ROOT / 'README.md',
        REPO_ROOT / 'LIMITATIONS.md',
    ]

    violations = []
    for target in scan_targets:
        files = [target] if target.is_file() else list(target.rglob('*'))
        for f in files:
            if not f.is_file() or f.suffix.lower() not in {'.html', '.js', '.md', '.txt'}:
                continue
            text = f.read_text(encoding='utf-8')
            for pattern, desc in forbidden_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    violations.append(f'{f.relative_to(REPO_ROOT)}: forbidden phrase "{desc}"')

    assert not violations, 'Violations of extended forbidden terms:\n' + '\n'.join(violations)


def test_b1_story_mode_claims_and_sources():
    story_html = (REPO_ROOT / 'ui' / 'templates' / 'story.html').read_text(encoding='utf-8')
    assert 'Why .si Domain Speculation Is High Risk' not in story_html
    assert 'radical honesty' not in story_html
    assert 'quietly consume' not in story_html
    assert 'Netcraft' in story_html
    assert 'Domain Name Wire' in story_html
    assert '52%' in story_html or 'about 52%' in story_html
    assert '2 of 35' in story_html


def test_b2_funnel_calibration_data_claim():
    funnel_html = (REPO_ROOT / 'ui' / 'templates' / 'funnel.html').read_text(encoding='utf-8')
    assert 'In calibration testing, registrar checkout pages reported' not in funnel_html
    assert 'disagreed' in funnel_html
    
    cal_html = (REPO_ROOT / 'ui' / 'templates' / 'calibration.html').read_text(encoding='utf-8')
    assert 'Statistical confidence' not in cal_html
    assert 'Agreement rate (small sample)' in cal_html


def test_b3_no_real_company_names_in_demo_fixtures():
    real_registrars = ['hostinger', 'domovanje']
    
    cal_file = REPO_ROOT / 'demo_data' / 'calibration.json'
    if cal_file.exists():
        cal_data = json.loads(cal_file.read_text(encoding='utf-8'))
        for entry in cal_data:
            r_name = entry.get('registrar_name', '').lower()
            for real in real_registrars:
                assert real not in r_name, f'Real company {real} found in calibration fixture: {entry}'

    conf_file = REPO_ROOT / 'demo_data' / 'registrar_confirmations.json'
    if conf_file.exists():
        conf_data = json.loads(conf_file.read_text(encoding='utf-8'))
        for domain, entry in conf_data.items():
            r_name = entry.get('registrar', '').lower()
            for real in real_registrars:
                assert real not in r_name, f'Real company {real} found in registrar confirmation fixture: {entry}'


def test_b4_currency_conversion_budget_lab():
    from si_scout.budget_math import calculate_budget_model
    res_usd = calculate_budget_model(budget=200, first_year=12.13, renewal=13.61, term_years=3, currency='USD', exchange_rate=1.0)
    assert res_usd['currency'] == 'USD'
    assert '$' in res_usd['summary_sentence']

    res_eur = calculate_budget_model(budget=200, first_year=11.23, renewal=12.60, term_years=3, currency='EUR', exchange_rate=1.08)
    assert res_eur['currency'] == 'EUR'
    assert '€' in res_eur['summary_sentence'] or 'EUR' in res_eur['summary_sentence']


def test_b5_heatmap_averages_caption_and_row_pzero():
    from si_scout.budget_math import generate_sensitivity_matrix
    matrix = generate_sensitivity_matrix(domain_count=5, term_years=3, carry_cost_with_tax=39.35)
    for row in matrix['matrix']:
        assert 'p_zero_pct' in row

    budget_html = (REPO_ROOT / 'ui' / 'templates' / 'budget.html').read_text(encoding='utf-8')
    assert 'Averages across many hypothetical portfolios. Most individual outcomes are a loss of the carry cost.' in budget_html


def test_b6_gate_thresholds_shared_config():
    from si_scout import config
    assert getattr(config, 'MIN_RATIONALE_WORDS', None) == 15
    from ui import gates
    assert gates.MIN_WORDS == 15

    gates_html = (REPO_ROOT / 'ui' / 'templates' / 'gates_sim.html').read_text(encoding='utf-8')
    assert '8 words' not in gates_html.lower()
    assert 'The tool never rates or recommends any name' not in gates_html
    assert 'The tool never recommends a name to buy' in gates_html


def test_b7_name_lab_disclaimers():
    name_lab_html = (REPO_ROOT / 'ui' / 'templates' / 'name_lab.html').read_text(encoding='utf-8')
    assert 'data-label="google"' not in name_lab_html
    assert "Not on this tool's small example blocklist. This is not a trademark search." in name_lab_html
    assert 'popular-site list not loaded' in name_lab_html or 'not bundled' in name_lab_html


def test_b8_name_lab_score_distinct():
    name_lab_html = (REPO_ROOT / 'ui' / 'templates' / 'name_lab.html').read_text(encoding='utf-8')
    assert 'Name Lab shape score, not the scanner score' in name_lab_html


def test_b9_demo_data_internal_consistency():
    findings_file = REPO_ROOT / 'demo_data' / 'findings_data.json'
    data = json.loads(findings_file.read_text(encoding='utf-8'))
    
    funnel = data['funnel']
    saturation = data['saturation_by_pattern']
    
    total_sat_checked = sum(row['checked'] for row in saturation)
    total_sat_registered = sum(row['registered'] for row in saturation)
    total_sat_not_in_reg = sum(row['not_in_registry'] for row in saturation)
    
    assert total_sat_checked == funnel['registry_checked']
    assert total_sat_not_in_reg == funnel['not_in_registry_404']
    assert total_sat_registered == (funnel['registry_checked'] - funnel['not_in_registry_404'])
    assert 'AgentForge' not in json.dumps(data)


def test_b10_overview_wording_demo():
    overview_html = (REPO_ROOT / 'ui' / 'templates' / 'overview.html').read_text(encoding='utf-8')
    assert 'Authoritative Empirical Snapshot' not in overview_html
    assert 'Demo snapshot (synthetic data)' in overview_html


def test_watch_no_stabilizing_fading():
    watch_html = (REPO_ROOT / 'ui' / 'templates' / 'watch.html').read_text(encoding='utf-8')
    assert 'Rush Velocity Assessment' not in watch_html
    assert 'STABILIZING' not in watch_html
    assert 'FADING' not in watch_html


def test_candidates_no_nan_and_domain_styled():
    from ui.data import UIDataManager
    mgr = UIDataManager(is_demo=True)
    df = mgr.get_candidates_df()
    assert not df.empty
    recs = df.to_dict(orient='records')
    for r in recs:
        assert r['domain']
        assert str(r['domain']) != 'nan'
    cand_html = (REPO_ROOT / 'ui' / 'templates' / 'candidates.html').read_text(encoding='utf-8')
    assert 'color: #fff' not in cand_html


def test_claims_register_exists_and_covers_story():
    cr_path = REPO_ROOT / 'CLAIMS_REGISTER.md'
    assert cr_path.exists()
    cr_text = cr_path.read_text(encoding='utf-8')
    assert 'Story Mode' in cr_text
    assert 'Netcraft' in cr_text
    assert 'Domain Name Wire' in cr_text
