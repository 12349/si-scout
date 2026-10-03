import pytest
from si_scout.score import ScoreEngine, CandidateEvaluation, CandidateTier
from si_scout.rdap import RDAPStatus

def test_score_gating_requires_human_sentence():
    engine = ScoreEngine()
    
    # All automated criteria excellent, but human rationale is empty
    evaluation = engine.evaluate(
        label="neuroagent",
        rdap_status=RDAPStatus.AVAILABLE_CANDIDATE,
        is_price_stale=False,
        has_trademark_flag=False,
        human_rationale="",
        human_rationale_verified=False,
        category="intelligence_agents",
        com_status="ACTIVE_SITE",
        ai_status="PARKED_OR_FOR_SALE"
    )

    # Must NOT be BUY_CANDIDATE without human sentence
    assert evaluation.tier != CandidateTier.BUY_CANDIDATE
    assert evaluation.tier == CandidateTier.MONITOR
    assert "human end-user sentence" in evaluation.gate_failures[0].lower()

from datetime import datetime, timezone, timedelta

def test_score_gating_passes_with_verified_human_sentence_and_gate_6():
    engine = ScoreEngine()
    
    # Valid human confirmation at registrar checkout (fresh timestamp)
    valid_conf = {
        "author": "human",
        "registrar": "Hostinger",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "result": "available"
    }

    evaluation = engine.evaluate(
        label="neuroagent",
        rdap_status=RDAPStatus.AVAILABLE_CANDIDATE,
        is_price_stale=False,
        has_trademark_flag=False,
        human_rationale="A neural AI laboratory would pay $500 because it directly describes cognitive agent software.",
        human_rationale_verified=True,
        scarcity_manual=8.0,
        usability_manual=12.0,
        category="intelligence_agents",
        com_status="ACTIVE_SITE",
        ai_status="PARKED_OR_FOR_SALE",
        registrar_confirmation=valid_conf
    )

    assert evaluation.tier == CandidateTier.BUY_CANDIDATE
    assert len(evaluation.gate_failures) == 0
    assert evaluation.total_score >= 65

def test_regression_cli_path_unverified_rationale_never_buy_candidate():
    """Phase A Step 3 Regression Test: CLI Path."""
    engine = ScoreEngine()

    # Has rationale text, but human_rationale_verified is False (e.g. unverified, agent-written, or source unknown)
    evaluation = engine.evaluate(
        label="neuroagent",
        rdap_status=RDAPStatus.AVAILABLE_CANDIDATE,
        is_price_stale=False,
        has_trademark_flag=False,
        human_rationale="A neural AI laboratory would pay $500 because it directly describes cognitive agent software.",
        human_rationale_verified=False,
        scarcity_manual=8.0,
        usability_manual=12.0,
        category="intelligence_agents",
        com_status="ACTIVE_SITE",
        ai_status="PARKED_OR_FOR_SALE"
    )

    # Must strictly be prevented from entering BUY_CANDIDATE
    assert evaluation.tier != CandidateTier.BUY_CANDIDATE
    assert evaluation.tier == CandidateTier.MONITOR
    assert any("source unknown" in f.lower() or "unverified" in f.lower() for f in evaluation.gate_failures)

def test_score_gating_blocks_trademark_and_stale_price():
    engine = ScoreEngine()

    # Trademark collision
    eval_tm = engine.evaluate(
        label="google",
        rdap_status=RDAPStatus.AVAILABLE_CANDIDATE,
        is_price_stale=False,
        has_trademark_flag=True,
        human_rationale="Great brand",
        human_rationale_verified=True,
        category="intelligence"
    )
    assert eval_tm.tier == CandidateTier.AVOID
    assert any("trademark" in f.lower() for f in eval_tm.gate_failures)

    # Stale price
    eval_stale = engine.evaluate(
        label="neuroagent",
        rdap_status=RDAPStatus.AVAILABLE_CANDIDATE,
        is_price_stale=True,
        has_trademark_flag=False,
        human_rationale="A lab would buy it",
        human_rationale_verified=True,
        category="intelligence"
    )
    assert eval_stale.tier != CandidateTier.BUY_CANDIDATE
    assert any("price" in f.lower() for f in eval_stale.gate_failures)

def test_gate_6_strictly_enforced_in_score_engine():
    """Proves that ScoreEngine and CLI can NEVER assign BUY_CANDIDATE unless Gate 6 passed."""
    engine = ScoreEngine()
    kwargs = dict(
        label="modelcraft",
        rdap_status=RDAPStatus.AVAILABLE_CANDIDATE,
        is_price_stale=False,
        has_trademark_flag=False,
        human_rationale="An AI fine-tuning workshop would pay $500 for this domain because it directly targets modelcraft engineering.",
        human_rationale_verified=True,
        scarcity_manual=8.0,
        usability_manual=12.0,
        category="core_tech",
        com_status="ACTIVE_SITE",
        ai_status="PARKED_OR_FOR_SALE"
    )

    # Case 1: Missing Gate 6 confirmation
    eval_no_gate6 = engine.evaluate(**kwargs, registrar_confirmation=None)
    assert eval_no_gate6.tier != CandidateTier.BUY_CANDIDATE
    assert eval_no_gate6.tier == CandidateTier.MONITOR
    assert any("gate 6" in f.lower() for f in eval_no_gate6.gate_failures)

    # Case 2: Registrar reported 'already taken' (checkout conflict scenario)
    eval_taken = engine.evaluate(**kwargs, registrar_confirmation={
        "author": "human",
        "registrar": "Hostinger",
        "checked_utc": "UNKNOWN",
        "result": "already taken"
    })
    assert eval_taken.tier != CandidateTier.BUY_CANDIDATE
    assert eval_taken.tier == CandidateTier.MONITOR
    assert any("already taken" in f.lower() for f in eval_taken.gate_failures)

    # Case 3: Registrar reported 'registry busy / could not confirm'
    eval_busy = engine.evaluate(**kwargs, registrar_confirmation={
        "author": "human",
        "registrar": "Hostinger",
        "checked_utc": "2026-10-01T21:00:00Z",
        "result": "registry busy / could not confirm"
    })
    assert eval_busy.tier != CandidateTier.BUY_CANDIDATE
    assert eval_busy.tier == CandidateTier.MONITOR
    assert any("registry busy" in f.lower() for f in eval_busy.gate_failures)

    # Case 4: Attempt time is UNKNOWN
    eval_unknown_ts = engine.evaluate(**kwargs, registrar_confirmation={
        "author": "human",
        "registrar": "Hostinger",
        "checked_utc": "UNKNOWN",
        "result": "available"
    })
    assert eval_unknown_ts.tier != CandidateTier.BUY_CANDIDATE
    assert any("cannot be unknown" in f.lower() or "missing" in f.lower() for f in eval_unknown_ts.gate_failures)

    # Case 5: Automated / non-human author
    eval_bot = engine.evaluate(**kwargs, registrar_confirmation={
        "author": "crawler_bot",
        "registrar": "Hostinger",
        "checked_utc": "2026-10-01T21:00:00Z",
        "result": "available"
    })
    assert eval_bot.tier != CandidateTier.BUY_CANDIDATE
    assert any("must be 'human'" in f.lower() for f in eval_bot.gate_failures)

    # Case 6: Human confirmed available at registrar checkout -> BUY_CANDIDATE PASSES
    eval_pass = engine.evaluate(**kwargs, registrar_confirmation={
        "author": "human",
        "registrar": "Hostinger",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "result": "available"
    })
    assert eval_pass.tier == CandidateTier.BUY_CANDIDATE
    assert len(eval_pass.gate_failures) == 0

    # Case 7: Expired confirmation (>60 minutes old) -> FAILS Gate 6
    expired_time = (datetime.now(timezone.utc) - timedelta(minutes=65)).isoformat()
    eval_expired = engine.evaluate(**kwargs, registrar_confirmation={
        "author": "human",
        "registrar": "Hostinger",
        "checked_utc": expired_time,
        "result": "available"
    })
    assert eval_expired.tier != CandidateTier.BUY_CANDIDATE
    assert eval_expired.tier == CandidateTier.MONITOR
    assert any("confirmation expired: re-confirm at checkout" in f.lower() for f in eval_expired.gate_failures)

def test_results_csv_and_report_md_never_show_buy_candidate_without_gate_6(tmp_path):
    """Proves results.csv and report.md never output BUY_CANDIDATE unless Gate 6 passed."""
    from si_scout.report import ReportGenerator
    import csv

    engine = ScoreEngine()
    rep_gen = ReportGenerator(output_dir=tmp_path)

    # Domain with valid human rationale and 404 status, but NO Gate 6 confirmation
    eval_without_gate6 = engine.evaluate(
        label="cloudneuro",
        rdap_status=RDAPStatus.AVAILABLE_CANDIDATE,
        is_price_stale=False,
        has_trademark_flag=False,
        human_rationale="A machine learning infrastructure team would pay $500 for this clean short domain.",
        human_rationale_verified=True,
        scarcity_manual=8.0,
        usability_manual=12.0,
        category="core_tech",
        registrar_confirmation=None
    )

    budget_info = {
        "total_budget": 200.0,
        "reserve_amount": 20.0,
        "effective_budget": 180.0,
        "carry_3yr_per_name": 39.35,
        "max_names": 4
    }
    pricing_map = {
        "cloudneuro.si": {
            "cheapest_registrar": {"name": "Dynadot", "year1_usd": 12.13, "carry_3yr": 39.35},
            "buy_link": "https://www.dynadot.com/domain/search.html?domain=cloudneuro.si"
        }
    }

    md_file, csv_file = rep_gen.generate_reports([eval_without_gate6], budget_info, pricing_map)

    # Verify results.csv
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        for row in reader:
            assert row["tier"] != "BUY_CANDIDATE"
            assert row["tier"] == "MONITOR"
            assert "Gate 6" in row["gate_failures"]

    # Verify report.md
    md_content = md_file.read_text(encoding="utf-8")
    assert "Tier 1: BUY_CANDIDATE (0 names)" in md_content
    assert "No candidates currently meet all strict BUY_CANDIDATE gates" in md_content
    assert "cloudneuro.si" not in md_content.split("## 4. Tier 2: MONITOR")[0]
