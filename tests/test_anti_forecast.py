import re
import pytest
from pathlib import Path
from si_scout.report import ReportGenerator
from si_scout.score import CandidateEvaluation, CandidateTier, ScoreBreakdown
from si_scout.rdap import RDAPStatus

BANNED_HYPE_PATTERNS = [
    r"\bwill appreciate\b",
    r"\bguaranteed\b",
    r"\bguarantee\b",
    r"\bhigh roi\b",
    r"\brisk[- ]free\b",
    r"\bpredict(?:ed)? appreciation\b",
    r"\b100x return\b",
    r"\bsure thing\b",
    r"\bpassive income\b"
]

def test_anti_forecast_regression(tmp_path):
    report_gen = ReportGenerator(output_dir=tmp_path)
    
    # Create sample evaluations
    breakdown = ScoreBreakdown(
        shape_brandability=20.0,
        pronounceability_typing=12.0,
        semantic_fit_si_ai=20.0,
        twin_signals=5.0,
        scarcity_manual=5.0,
        usability_manual=10.0,
        penalties=0.0,
        total_score=72.0,
        rationale_notes=["Passed all screening"]
    )
    
    sample_eval = CandidateEvaluation(
        label="neurocore",
        domain="neurocore.si",
        tier=CandidateTier.BUY_CANDIDATE,
        total_score=72.0,
        breakdown=breakdown,
        human_rationale="A neural silicon lab would pay $600 because it names core accelerator models.",
        gate_failures=[],
        rdap_status=RDAPStatus.AVAILABLE_CANDIDATE
    )

    budget_info = {
        "total_budget": 200.0,
        "reserve_amount": 20.0,
        "effective_budget": 180.0,
        "carry_3yr_per_name": 39.35,
        "max_names": 4
    }

    pricing_map = {
        "neurocore.si": {
            "cheapest_registrar": {
                "name": "Dynadot",
                "year1_usd": 12.13,
                "carry_3yr": 39.35,
                "is_stale": False,
                "as_of": "2026-09-30T00:00:00Z"
            },
            "buy_link": "https://www.dynadot.com/domain/search.html?domain=neurocore.si"
        }
    }

    report_md_path, results_csv_path = report_gen.generate_reports([sample_eval], budget_info, pricing_map)

    report_text = report_md_path.read_text(encoding="utf-8").lower()

    # Assert that no banned hype words appear in the report
    for pattern in BANNED_HYPE_PATTERNS:
        match = re.search(pattern, report_text, re.IGNORECASE)
        assert match is None, f"Report contained banned forecast language: '{match.group(0)}'"

    # Must contain explicit disclaimer
    assert "illustrative" in report_text
    assert "not a forecast" in report_text


def test_docs_anti_forecast():
    """Verify that documentation files do not contain banned forecast/hype language."""
    repo_root = Path(__file__).resolve().parent.parent
    docs_to_check = [
        repo_root / "README.md",
        repo_root / "LIMITATIONS.md",
        repo_root / "RESPONSIBLE_USE.md",
        repo_root / "DISCLAIMER",
        repo_root / "CONTRIBUTING.md",
        repo_root / "SECURITY.md",
    ]
    forbidden_patterns = [
        r"\bwill appreciate\b",
        r"\bhigh potential\b",
        r"\bundervalued\b",
        r"\bgem\b",
        r"\bnext \.ai\b",
        r"\b100x\b",
        r"\brisk[- ]free\b",
        r"\bpassive income\b",
        r"\bsure thing\b",
        r"\bguaranteed profit\b",
        r"\bhigh roi\b"
    ]
    violations = []
    for doc in docs_to_check:
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8", errors="ignore").lower()
        for p in forbidden_patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                violations.append(f"{doc.name}: Found forbidden hype phrase '{match.group(0)}'")

    assert len(violations) == 0, f"Found anti-forecast violations in documentation:\n" + "\n".join(violations)

