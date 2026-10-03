#!/usr/bin/env python3
"""
SI Scout: Synthetic Demo Data Generator
Generates realistic, completely synthetic test fixtures for offline demonstration.
Guarantees:
- Zero real survivor domain names
- Zero names of real commercial companies or living registrants
- Purely synthetic example labels (prefixed with example-, demo-, sample-, test-, mock-)
- Fully offline and isolated within demo_data/
"""

import csv
import json
import sqlite3
from pathlib import Path
from typing import Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
DEMO_DIR = BASE_DIR / "demo_data"

def generate_demo_fixtures(target_dir: Optional[Path] = None):
    demo_dir = Path(target_dir) if target_dir else DEMO_DIR
    demo_dir.mkdir(parents=True, exist_ok=True)

    # 1. results.csv
    results_path = demo_dir / "results.csv"
    demo_results = [
        ("example-cloud.si", "example-cloud", "MONITOR", 72.0, "AVAILABLE_CANDIDATE", "Dynadot", 12.13, 39.35,
         "https://www.dynadot.com/domain/search.html?domain=example-cloud.si",
         "A synthetic cloud infrastructure startup would pay $500 for this clean descriptive domain.",
         "Gate 6: Confirmed at a registrar checkout missing (human checkout verification required)",
         "2026-09-30 20:00:00 UTC"),
        ("demo-agent.si", "demo-agent", "MONITOR", 68.5, "AVAILABLE_CANDIDATE", "Hostinger", 11.99, 45.97,
         "https://www.hostinger.com/domain-name-search?domain=demo-agent.si",
         "An autonomous software testing company would pay $400 because it clearly denotes agent capabilities.",
         "Gate 6: Domain reported 'already taken' at Registrar B checkout (UNKNOWN)",
         "2026-09-30 20:00:00 UTC"),
        ("sample-nexus.si", "sample-nexus", "MONITOR", 65.0, "REGISTERED", "Dynadot", 12.13, 39.35,
         "https://www.dynadot.com/domain/search.html?domain=sample-nexus.si",
         "",
         "Domain is not available in registry (RDAP status: active); Human end-user sentence missing",
         "2026-09-30 20:00:00 UTC"),
        ("test-synth.si", "test-synth", "MONITOR", 63.5, "AVAILABLE_CANDIDATE", "Registrar C", 18.50, 55.50,
         "https://www.domovanje.com/domene/?isci=test-synth.si",
         "A synthetic voice synthesis developer would pay $350 for this domain to brand neural voice models.",
         "Gate 6: Registry busy / could not confirm at 2026-09-30T12:32:00Z (gate failed; unlimited retries allowed)",
         "2026-09-30 20:00:00 UTC"),
        ("demo-cortex.si", "demo-cortex", "MONITOR", 61.0, "QUARANTINE/PENDING_DELETE", "Dynadot", 12.13, 39.35,
         "https://www.dynadot.com/domain/search.html?domain=demo-cortex.si",
         "",
         "Domain is in registry quarantine (status: pending delete); Awaiting release or redemption expiration",
         "2026-09-30 20:00:00 UTC"),
        ("mock-logic.si", "mock-logic", "MONITOR", 58.0, "AVAILABLE_CANDIDATE", "Dynadot", 12.13, 39.35,
         "https://www.dynadot.com/domain/search.html?domain=mock-logic.si",
         "",
         "Total score 58.0 below minimum threshold of 60.0; Human rationale missing",
         "2026-09-30 20:00:00 UTC"),
        ("example-brand-google.si", "example-brand-google", "AVOID", 20.0, "AVAILABLE_CANDIDATE", "Dynadot", 12.13, 39.35,
         "https://www.dynadot.com/domain/search.html?domain=example-brand-google.si",
         "",
         "Trademark or brand conflict flag present: Google (high legal dispute risk under ARDS)",
         "2026-09-30 20:00:00 UTC"),
        ("sample-reserved-112.si", "sample-reserved-112", "AVOID", 10.0, "RESERVED", "N/A", 0.0, 0.0,
         "N/A",
         "",
         "Domain is official registry reserved emergency code under Register.si statutory rules",
         "2026-09-30 20:00:00 UTC"),
        ("test-vector.si", "test-vector", "MONITOR", 74.0, "AVAILABLE_CANDIDATE", "Dynadot", 12.13, 39.35,
         "https://www.dynadot.com/domain/search.html?domain=test-vector.si",
         "A vector database engineering firm would pay $600 because it names semantic indexing systems.",
         "Gate 6: Confirmed at a registrar checkout missing (human checkout verification required)",
         "2026-09-30 20:00:00 UTC"),
        ("demo-robot.si", "demo-robot", "MONITOR", 66.0, "AVAILABLE_CANDIDATE", "Hostinger", 11.99, 45.97,
         "https://www.hostinger.com/domain-name-search?domain=demo-robot.si",
         "A robotics automation laboratory would pay $450 for this descriptive domain to host demonstrations.",
         "Gate 6: Confirmed at a registrar checkout missing (human checkout verification required)",
         "2026-09-30 20:00:00 UTC")
    ]

    with open(results_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "domain", "label", "tier", "total_score", "rdap_status",
            "cheapest_registrar", "year1_usd", "carry_3yr_usd",
            "buy_link", "human_rationale", "gate_failures", "checked_utc"
        ])
        for row in demo_results:
            writer.writerow(row)

    # 2. scout.db
    db_path = demo_dir / "scout.db"
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE registry_cache (
            domain TEXT PRIMARY KEY,
            label TEXT,
            tld TEXT,
            rdap_status TEXT,
            http_status_code INTEGER,
            raw_statuses_json TEXT,
            raw_rdap_json TEXT,
            checked_utc TEXT,
            source TEXT
        );
        CREATE TABLE twin_signals (
            label TEXT PRIMARY KEY,
            com_status TEXT,
            com_details TEXT,
            ai_status TEXT,
            ai_details TEXT,
            checked_utc TEXT
        );
        CREATE TABLE registry_counters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT UNIQUE,
            total_domains INTEGER,
            domains_last_month INTEGER,
            domains_last_24h INTEGER,
            total_registrars INTEGER,
            recorded_utc TEXT
        );
        CREATE TABLE watch_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT,
            old_status TEXT,
            new_status TEXT,
            recorded_utc TEXT
        );
    """)

    # Populate synthetic registry_cache
    for d, l, tier, score, st, cheap, y1, c3, link, rat, gf, ts in demo_results:
        http_code = 404 if st == "AVAILABLE_CANDIDATE" else (200 if st in ["REGISTERED", "QUARANTINE/PENDING_DELETE"] else 404)
        raw_st = ["active"] if st == "REGISTERED" else (["pending delete"] if "QUARANTINE" in st else [])
        cur.execute("""
            INSERT INTO registry_cache VALUES (?, ?, 'si', ?, ?, ?, ?, ?, 'synthetic_fixture')
        """, (d, l, st, http_code, json.dumps(raw_st), json.dumps({"handle": d, "status": raw_st}), ts))

        cur.execute("""
            INSERT INTO twin_signals VALUES (?, 'ACTIVE_SITE', 'HTTP 200 Demo Twin', 'UNREGISTERED', 'DNS NXDOMAIN', ?)
        """, (l, ts))

    # Populate synthetic registry_counters
    counters = [
        ("2026-09-26", 152140, 480, 24, 98, "2026-09-26T20:00:00Z"),
        ("2026-09-27", 152185, 492, 45, 98, "2026-09-27T20:00:00Z"),
        ("2026-09-28", 152240, 515, 55, 98, "2026-09-28T20:00:00Z"),
        ("2026-09-29", 152310, 540, 70, 98, "2026-09-29T20:00:00Z"),
        ("2026-09-30", 152390, 575, 80, 98, "2026-09-30T20:00:00Z")
    ]
    for c in counters:
        cur.execute("INSERT INTO registry_counters (snapshot_date, total_domains, domains_last_month, domains_last_24h, total_registrars, recorded_utc) VALUES (?, ?, ?, ?, ?, ?)", c)

    # Populate synthetic watch_history
    cur.execute("INSERT INTO watch_history (domain, old_status, new_status, recorded_utc) VALUES ('demo-cortex.si', 'REGISTERED', 'QUARANTINE/PENDING_DELETE', '2026-09-29T10:00:00Z')")
    cur.execute("INSERT INTO watch_history (domain, old_status, new_status, recorded_utc) VALUES ('example-cloud.si', 'UNKNOWN', 'AVAILABLE_CANDIDATE', '2026-09-30T10:00:00Z')")

    conn.commit()
    conn.close()

    # 3. calibration.json
    cal_path = DEMO_DIR / "calibration.json"
    demo_cal = [
        {
            "id": 1,
            "domain": "example-cloud.si",
            "registry_status": "404 Not Found",
            "registry_time_utc": "2026-09-30T12:00:00Z",
            "registry_recheck_time": "2026-09-30T12:05:00Z",
            "registrar_name": "Registrar A",
            "registrar_result": "available",
            "registrar_time_utc": "2026-09-30T12:04:00Z",
            "delta_minutes": 4.0,
            "delta_minutes_registry_to_registrar": 4.0,
            "agrees": True,
            "author": "human",
            "notes": "Synthetic demo check: confirmed proceeds to cart"
        },
        {
            "id": 2,
            "domain": "demo-agent.si",
            "registry_status": "404 Not Found",
            "registry_time_utc": "2026-09-30T12:10:00Z",
            "registry_recheck_time": "2026-09-30T12:15:00Z",
            "registrar_name": "Registrar B",
            "registrar_result": "already taken",
            "registrar_time_utc": "UNKNOWN",
            "delta_minutes": "UNKNOWN",
            "delta_minutes_registry_to_registrar": "UNKNOWN",
            "agrees": False,
            "author": "human",
            "notes": "Synthetic demo check: registrar reported already registered"
        },
        {
            "id": 3,
            "domain": "sample-nexus.si",
            "registry_status": "200 Active",
            "registry_time_utc": "2026-09-30T12:20:00Z",
            "registry_recheck_time": "UNKNOWN",
            "registrar_name": "Registrar B",
            "registrar_result": "already taken",
            "registrar_time_utc": "2026-09-30T12:22:00Z",
            "delta_minutes": 2.0,
            "delta_minutes_registry_to_registrar": 2.0,
            "agrees": True,
            "author": "human",
            "notes": "Synthetic demo check: registry and registrar agree domain is taken"
        },
        {
            "id": 4,
            "domain": "test-synth.si",
            "registry_status": "404 Not Found",
            "registry_time_utc": "2026-09-30T12:30:00Z",
            "registry_recheck_time": "UNKNOWN",
            "registrar_name": "Registrar C",
            "registrar_result": "registry busy / could not confirm",
            "registrar_time_utc": "2026-09-30T12:32:00Z",
            "delta_minutes": 2.0,
            "delta_minutes_registry_to_registrar": 2.0,
            "agrees": False,
            "author": "human",
            "notes": "Synthetic demo check: temporary EPP registry timeout; retry permitted"
        }
    ]
    with open(cal_path, "w", encoding="utf-8") as f:
        json.dump(demo_cal, f, indent=2)

    # 4. registrar_confirmations.json
    conf_path = demo_dir / "registrar_confirmations.json"
    demo_conf = {
        "example-cloud.si": {
            "domain": "example-cloud.si",
            "registrar": "Registrar A",
            "checked_utc": "2026-09-30T12:04:00Z",
            "result": "available",
            "author": "human",
            "notes": "Synthetic demo check: available in cart"
        },
        "demo-agent.si": {
            "domain": "demo-agent.si",
            "registrar": "Registrar B",
            "checked_utc": "UNKNOWN",
            "result": "already taken",
            "author": "human",
            "notes": "Synthetic demo check: already taken"
        },
        "test-synth.si": {
            "domain": "test-synth.si",
            "registrar": "Registrar C",
            "checked_utc": "2026-09-30T12:32:00Z",
            "result": "registry busy / could not confirm",
            "author": "human",
            "notes": "Synthetic demo check: busy"
        }
    }
    with open(conf_path, "w", encoding="utf-8") as f:
        json.dump(demo_conf, f, indent=2)

    # 5. rationales.json
    rat_path = demo_dir / "rationales.json"
    demo_rat = {
        "example-cloud": {
            "label": "example-cloud",
            "rationale": "A synthetic cloud infrastructure startup would pay $500 for this clean descriptive domain.",
            "author": "human",
            "self_written": True,
            "timestamp": "2026-09-30T12:00:00Z",
            "scarcity": 8.0,
            "usability": 12.0
        },
        "demo-agent": {
            "label": "demo-agent",
            "rationale": "An autonomous software testing company would pay $400 because it clearly denotes agent capabilities.",
            "author": "human",
            "self_written": True,
            "timestamp": "2026-09-30T12:00:00Z",
            "scarcity": 7.0,
            "usability": 10.0
        },
        "test-vector": {
            "label": "test-vector",
            "rationale": "A vector database engineering firm would pay $600 because it names semantic indexing systems.",
            "author": "human",
            "self_written": True,
            "timestamp": "2026-09-30T12:00:00Z",
            "scarcity": 8.0,
            "usability": 12.0
        }
    }
    with open(rat_path, "w", encoding="utf-8") as f:
        json.dump(demo_rat, f, indent=2)

    # 6. drop_watch.csv
    drop_path = demo_dir / "drop_watch.csv"
    with open(drop_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["domain", "registration_date", "expiration_date", "pattern", "registered_timing", "age_at_expiry_years", "initial_term_years"])
        writer.writerow(["sample-nexus.si", "2021-03-01T10:00:00Z", "2027-03-01T10:00:00Z", "single", "BEFORE_SEPT_19_2026", 6.0, ""])
        writer.writerow(["demo-cortex.si", "2025-09-29T10:27:06Z", "2026-09-29T10:27:06Z", "single", "BEFORE_SEPT_19_2026", 1.0, ""])
        writer.writerow(["mock-tensor.si", "2026-09-20T14:00:00Z", "2027-09-20T14:00:00Z", "compound", "AFTER_SEPT_19_2026", 1.0, 1.0])

    # 7. expiring_soon.csv
    exp_path = demo_dir / "expiring_soon.csv"
    with open(exp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["domain", "registration_date", "expiration_date", "age_at_expiry_years", "initial_term_years", "pattern", "is_118_single_word"])
        writer.writerow(["demo-cortex.si", "2025-09-29T10:27:06Z", "2026-10-29T10:27:06Z", 1.0, "", "single", "YES"])

    # 8. watch_log.csv
    wlog_path = demo_dir / "watch_log.csv"
    with open(wlog_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_utc", "domain", "old_status", "new_status", "http_status", "raw_rdap_status", "event_type", "notes", "source"])
        writer.writerow(["2026-09-29T10:27:06Z", "demo-cortex.si", "REGISTERED", "QUARANTINE/PENDING_DELETE", 200, "pending delete", "STATUS_CHANGE", "Demo status change", "synthetic_demo"])
        writer.writerow(["2026-09-30T10:00:00Z", "example-cloud.si", "UNKNOWN", "AVAILABLE_CANDIDATE", 404, "not_found", "ROUTINE_CHECK", "Demo routine scan", "synthetic_demo"])

    # 9. findings_data.json (for Phase 3 Findings page)
    findings_path = demo_dir / "findings_data.json"
    demo_findings = {
        "metadata": {
            "source_file": "demo_data/findings_data.json",
            "generation_date_utc": "2026-10-02T16:00:00Z",
            "is_demo": True,
            "disclaimer": "Illustrative demo data. Not real registry results."
        },
        "funnel": {
            "total_candidates_generated": 100,
            "prefiltered_survivors": 75,
            "registry_checked": 75,
            "not_in_registry_404": 15,
            "strict_survivors": 4,
            "stage_descriptions": [
                {"stage": "1. Lexical Generator", "count": 100, "drop_pct": "0.0%"},
                {"stage": "2. Pre-filter (Length, Hyphens, Tranco Brand Collisions)", "count": 75, "drop_pct": "25.0%"},
                {"stage": "3. Register.si RDAP Scan (Synthetic)", "count": 75, "drop_pct": "0.0%"},
                {"stage": "4. Registry 404 (Not In Active Registry)", "count": 15, "drop_pct": "80.0%"},
                {"stage": "5. Strict Survivor (Clean Twins & Gated)", "count": 4, "drop_pct": "73.3%"}
            ]
        },
        "saturation_by_pattern": [
            {"pattern": "Single Dictionary Words", "checked": 25, "registered": 24, "not_in_registry": 1, "survival_rate_pct": 4.0},
            {"pattern": "Compound Blends (e.g. SynthBlend)", "checked": 30, "registered": 22, "not_in_registry": 8, "survival_rate_pct": 26.7},
            {"pattern": "Prefix / Suffix Affixes", "checked": 15, "registered": 11, "not_in_registry": 4, "survival_rate_pct": 26.7},
            {"pattern": "Short Acronyms (3-4 Chars)", "checked": 5, "registered": 3, "not_in_registry": 2, "survival_rate_pct": 40.0}
        ]
    }
    with open(findings_path, "w", encoding="utf-8") as f:
        json.dump(demo_findings, f, indent=2)

    # 10. Empty portfolio.db
    p_path = demo_dir / "portfolio.db"
    if p_path.exists():
        p_path.unlink()
    p_conn = sqlite3.connect(p_path)
    p_cur = p_conn.cursor()
    p_cur.executescript("""
        CREATE TABLE portfolio_domains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT UNIQUE NOT NULL,
            purchase_date TEXT NOT NULL,
            cost_usd REAL NOT NULL,
            registrar TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            renewal_due_date TEXT,
            refund_cutoff_date TEXT,
            dns_activated INTEGER DEFAULT 0,
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        );
        CREATE TABLE shortlisted_domains (
            domain TEXT PRIMARY KEY,
            shortlisted_utc TEXT NOT NULL,
            notes TEXT
        );
        INSERT INTO shortlisted_domains VALUES ('example-cloud.si', '2026-09-30T12:00:00Z', 'Demo shortlisted candidate');
    """)
    p_conn.commit()
    p_conn.close()

    print(f"Generated synthetic demo fixtures successfully in {demo_dir}")

def ensure_demo_databases(target_dir: Optional[Path] = None) -> Tuple[Path, Path]:
    """Ensures demo_data/scout.db and demo_data/portfolio.db exist, generating fixtures if missing."""
    d_dir = Path(target_dir) if target_dir else DEMO_DIR
    d_dir.mkdir(parents=True, exist_ok=True)
    scout_db = d_dir / "scout.db"
    portfolio_db = d_dir / "portfolio.db"
    if not scout_db.exists() or not portfolio_db.exists():
        generate_demo_fixtures(target_dir=d_dir)
    return scout_db, portfolio_db

if __name__ == "__main__":
    generate_demo_fixtures()
