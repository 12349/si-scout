"""
CLI Interface and Orchestrator for SI Scout.
Coordinates all pipeline stages, enforces polite rate limits, prompts for human gates,
and generates reports and audit trails.
"""

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Dict, List, Optional

from si_scout.config import load_config, load_registrars, calculate_budget
from si_scout.generate import DomainGenerator, GeneratedCandidate
from si_scout.prefilter import DomainPreFilter
from si_scout.rdap import RDAPClient, RDAPStatus
from si_scout.twins import TwinAnalyzer
from si_scout.pricing import PricingEngine
from si_scout.score import ScoreEngine, CandidateEvaluation, CandidateTier
from si_scout.report import ReportGenerator
from si_scout.watch import WatchEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("SI-Scout")

def print_banner(budget_info: Dict):
    banner = f"""
================================================================================
                         SI SCOUT: .si RESEARCH TOOL
================================================================================
[MISSION] Screen & rank .si candidates under a strict USD 200 3-year budget cap.
[GROUND TRUTH] High score = passes screening heuristics. NOT a price forecast.
               End-user demand is unproven; small portfolio EV is negative.

[3-YEAR BUDGET MODEL]
  * Total Budget Cap:        ${budget_info['total_budget']:.2f} USD
  * Emergency Reserve (10%): ${budget_info['reserve_amount']:.2f} USD
  * Net Investable Budget:   ${budget_info['effective_budget']:.2f} USD
  * 3-Year Carry Cost/Name:  ${budget_info['carry_3yr_per_name']:.2f} USD (Year 1 + 2x Renewal)
  * Target Portfolio Size:   {budget_info['max_names']} names max (Leaves ${budget_info['remaining_cash']:.2f} cash reserve)
================================================================================
"""
    print(banner)

def run_watch_mode(db_path: Path):
    print("\n>>> RUNNING IN WATCH MODE (--watch) <<<")
    watch_engine = WatchEngine(db_path=db_path)
    
    print("[1/2] Fetching Register.si public statistics counters...")
    snapshot = watch_engine.fetch_and_record_counters()
    if snapshot:
        print(f"  * Total .si domains:        {snapshot.total_domains:,}")
        print(f"  * Domains last 24h:         {snapshot.domains_last_24h:,}")
        print(f"  * Domains previous month:   {snapshot.domains_last_month:,}")
        print(f"  * Accredited Registrars:    {snapshot.total_registrars}")
        if snapshot.domains_last_24h > 5000:
            print("  * RUSH STATUS: High activity (>5,000 in 24h).")
        else:
            print("  * RUSH STATUS: Subdued activity. Rush is stabilizing/fading.")
    else:
        print("  * Note: Could not fetch public counters (network or format change).")

    print("[2/2] Time-series history stored in scout.db.")

def run_pipeline(args):
    config = load_config()
    budget_info = config["budget"]
    print_banner(budget_info)

    if args.watch:
        run_watch_mode(Path(args.db_path))
        return

    # Stage 1: Candidate Generation
    print("[Stage 1/7] Generating candidate names...")
    generator = DomainGenerator(tld="si")
    extra_names = [n.strip() for n in args.extra.split(",") if n.strip()] if args.extra else None
    raw_candidates = generator.generate(extra_names=extra_names)
    print(f"  Generated {len(raw_candidates)} deduplicated and syntax-valid candidates.")

    # Stage 2: Offline Pre-Filter
    print("[Stage 2/7] Running offline heuristics & blocklist screening...")
    prefilter = DomainPreFilter(
        blocklist=config["blocklist"],
        reserved_domains=config["reserved_domains"]
    )
    
    screened_candidates: List[GeneratedCandidate] = []
    prefilter_scores = {}
    trademark_flags = {}

    for cand in raw_candidates:
        passed, reason, shape_score = prefilter.evaluate(cand.label)
        if passed:
            screened_candidates.append(cand)
            prefilter_scores[cand.label] = shape_score
        else:
            if "trademark" in reason.lower():
                trademark_flags[cand.label] = reason
            elif "reserved" in reason.lower():
                trademark_flags[cand.label] = reason

    print(f"  {len(screened_candidates)} candidates survived pre-filtering ({len(raw_candidates) - len(screened_candidates)} blocked or penalized).")

    # Limit by --top if requested
    limit = args.top if args.top and args.top > 0 else len(screened_candidates)
    candidates_to_check = screened_candidates[:limit]
    print(f"  Proceeding with top {len(candidates_to_check)} candidates for availability check.")

    # Stage 3: Authoritative RDAP Check
    print("[Stage 3/7] Querying Register.si authoritative RDAP (rate-limited <= 1 req/s)...")
    est_seconds = len(candidates_to_check) * 1.05
    est_minutes = est_seconds / 60.0
    print(f"  Estimated scan duration: ~{est_seconds:.0f} seconds ({est_minutes:.1f} minutes) at polite rate <= 1 req/s.")
    if args.dry_run:
        print("  [DRY-RUN MODE] Skipping live network queries; mocking availability.")
        rdap_client = None
    else:
        rdap_client = RDAPClient(
            db_path=Path(args.db_path),
            min_interval_seconds=1.05
        )

    rdap_results = {}
    for idx, cand in enumerate(candidates_to_check, 1):
        domain = cand.domain
        if args.dry_run:
            # Deterministic mock in dry run
            from si_scout.rdap import RDAPResult
            is_mock_available = (idx % 3 != 0)
            mock_status = RDAPStatus.AVAILABLE_CANDIDATE if is_mock_available else RDAPStatus.REGISTERED
            rdap_results[domain] = RDAPResult(
                domain=domain, label=cand.label, tld="si",
                status=mock_status, http_status_code=404 if is_mock_available else 200,
                raw_statuses=[], raw_json=None,
                checked_utc=datetime.now(timezone.utc).isoformat(),
                source="dry_run_mock"
            )
        else:
            res = rdap_client.check_domain(domain)
            rdap_results[domain] = res
            status_symbol = "[AVAIL]" if res.status == RDAPStatus.AVAILABLE_CANDIDATE else f"[{res.status.value}]"
            print(f"  ({idx}/{len(candidates_to_check)}) {domain:20s} -> {status_symbol}")

    # Stage 4: Twin Signals (.com and .ai)
    print("[Stage 4/7] Checking twin signals (.com and .ai)...")
    twin_results = {}
    if not args.dry_run and not args.skip_twins:
        twin_analyzer = TwinAnalyzer(db_path=Path(args.db_path))
        # Check twins for surviving available candidates
        availables = [c for c in candidates_to_check if rdap_results[c.domain].status == RDAPStatus.AVAILABLE_CANDIDATE]
        for c in availables[:30]:  # Limit twins to top 30 to stay fast and polite
            twin_res = twin_analyzer.evaluate_twins(c.label)
            twin_results[c.label] = twin_res
    else:
        print("  Skipping twin network queries (dry-run or skip-twins).")

    # Stage 5: Pricing
    print("[Stage 5/7] Calculating 1-year and 3-year carry costs per registrar...")
    pricing_engine = PricingEngine(registrars=config["registrars"])
    pricing_map = {}
    for cand in candidates_to_check:
        pricing_map[cand.domain] = pricing_engine.get_pricing_summary(cand.domain)

    # Load human rationales if provided
    human_rationales = {}
    if args.rationale_file:
        r_path = Path(args.rationale_file)
        if r_path.exists():
            with open(r_path, "r", encoding="utf-8") as f:
                human_rationales = json.load(f)

    # Load registrar confirmations (Gate 6 human checkout confirmations)
    registrar_confirmations = {}
    conf_path = Path("registrar_confirmations.json")
    if conf_path.exists():
        try:
            with open(conf_path, "r", encoding="utf-8") as f:
                registrar_confirmations = json.load(f)
        except Exception as e:
            print(f"  Warning: failed to load registrar confirmations from {conf_path}: {e}")

    # Stage 6: Scoring & Gating
    print("[Stage 6/7] Running Score v2 engine and non-negotiable gates...")
    score_engine = ScoreEngine()
    evaluations: List[CandidateEvaluation] = []

    for cand in candidates_to_check:
        domain = cand.domain
        rdap_res = rdap_results[domain]
        price_info = pricing_map[domain]
        cheapest_reg = price_info.get("cheapest_registrar") or {}
        is_stale = cheapest_reg.get("is_stale", False)

        has_tm = cand.label in trademark_flags
        tm_reason = trademark_flags.get(cand.label, "")

        tw = twin_results.get(cand.label)
        com_st = tw.com_status.value if tw else "UNKNOWN"
        ai_st = tw.ai_status.value if tw else "UNKNOWN"

        rat_data = human_rationales.get(cand.label)
        rationale = ""
        is_verified_human = False
        scarcity = 0.0
        usability = 0.0

        if isinstance(rat_data, dict):
            auth = str(rat_data.get("author", "")).strip().lower()
            self_written = bool(rat_data.get("self_written", False) or rat_data.get("verified_by_user", False))
            ts = rat_data.get("timestamp") or rat_data.get("created_utc")
            text = str(rat_data.get("rationale", "")).strip()
            words = text.split()

            if auth == "human" and self_written and ts and len(words) >= 15:
                rationale = text
                is_verified_human = True
                scarcity = float(rat_data.get("scarcity", 7.0))
                usability = float(rat_data.get("usability", 10.0))

        reg_conf = registrar_confirmations.get(cand.domain.lower()) or registrar_confirmations.get(f"{cand.label.lower()}.si")
        evaluation = score_engine.evaluate(
            label=cand.label,
            rdap_status=rdap_res.status,
            is_price_stale=is_stale,
            has_trademark_flag=has_tm,
            human_rationale=rationale,
            human_rationale_verified=is_verified_human,
            scarcity_manual=scarcity,
            usability_manual=usability,
            category=cand.category,
            com_status=com_st,
            ai_status=ai_st,
            trademark_reason=tm_reason,
            source_type=cand.source_type,
            registrar_confirmation=reg_conf
        )
        evaluations.append(evaluation)

    # Sort evaluations: BUY_CANDIDATE first, then MONITOR by score descending, then AVOID
    tier_order = {CandidateTier.BUY_CANDIDATE: 0, CandidateTier.MONITOR: 1, CandidateTier.AVOID: 2}
    evaluations.sort(key=lambda e: (tier_order[e.tier], -e.total_score))

    # Stage 7: Reporting
    print("[Stage 7/7] Generating results.csv and report.md...")
    report_gen = ReportGenerator(output_dir=Path(args.output_dir))
    md_file, csv_file = report_gen.generate_reports(evaluations, budget_info, pricing_map)

    # Summary
    buys = [e for e in evaluations if e.tier == CandidateTier.BUY_CANDIDATE]
    monitors = [e for e in evaluations if e.tier == CandidateTier.MONITOR]
    avoids = [e for e in evaluations if e.tier == CandidateTier.AVOID]

    print("\n======================= RUN SUMMARY =======================")
    print(f"Total Evaluated: {len(evaluations)}")
    print(f"  * Tier 1 (BUY_CANDIDATE): {len(buys)}")
    print(f"  * Tier 2 (MONITOR):       {len(monitors)}")
    print(f"  * Tier 3 (AVOID):         {len(avoids)}")
    print(f"\nArtifacts generated:")
    print(f"  - Markdown Report: {md_file.resolve()}")
    print(f"  - CSV Data:        {csv_file.resolve()}")

    if not buys:
        print("\n[NOTE] No candidates currently in BUY_CANDIDATE tier.")
        print("Reason: BUY_CANDIDATE strictly requires a human end-user rationale sentence:")
        print("  \"A [type of company] would pay [$X] because [reason]\"")
        print("To promote candidates, provide rationales via --rationale-file or pass them in.")

def main():
    parser = argparse.ArgumentParser(description="SI Scout: .si Domain Research & Screening Tool")
    parser.add_argument("--top", type=int, default=20, help="Number of pre-filtered candidates to check (default: 20)")
    parser.add_argument("--extra", type=str, default="", help="Comma-separated user custom domain names (e.g. 'agentic,siliconcore')")
    parser.add_argument("--dry-run", action="store_true", help="Run offline without making live network requests")
    parser.add_argument("--skip-twins", action="store_true", help="Skip .com/.ai twin queries to speed up execution")
    parser.add_argument("--watch", action="store_true", help="Run in daily watch mode to track public counters and status diffs")
    parser.add_argument("--rationale-file", type=str, default="", help="Path to JSON file containing human end-user rationales")
    parser.add_argument("--db-path", type=str, default="scout.db", help="Path to SQLite database cache (default: scout.db)")
    parser.add_argument("--output-dir", type=str, default=".", help="Output directory for results.csv and report.md (default: .)")

    args = parser.parse_args()
    run_pipeline(args)

if __name__ == "__main__":
    main()
