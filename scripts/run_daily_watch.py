"""
Daily Watch Runner for SI Scout.
Runs daily via Task Scheduler or cron:
- Captures Register.si public statistics counters
- Queries watchlist domains from watchlist.yaml (or watchlist.example.yaml)
- Queries top earliest-expiring domains (max 100 lookups/day, <= 1 req/s)
- Logs observed transitions to watch_log.csv and scout.db
"""

import csv
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sqlite3
import sys
import time
from typing import Dict, List, Optional
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from si_scout.rdap import RDAPClient, RDAPStatus
from si_scout.watch import WatchEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DailyWatch")

MAX_DAILY_LOOKUPS = 100

def load_watchlist_config(repo_root: Path) -> List[Dict[str, str]]:
    """Loads domain entries from watchlist.yaml, falling back to watchlist.example.yaml."""
    cfg_path = repo_root / "watchlist.yaml"
    if not cfg_path.exists():
        cfg_path = repo_root / "watchlist.example.yaml"
    if not cfg_path.exists():
        return []
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            items = data.get("domains", [])
            return [{"domain": str(item.get("domain", "")).strip().lower(), "notes": str(item.get("notes", ""))} for item in items if item.get("domain")]
    except Exception as e:
        logger.warning(f"Could not parse watchlist config ({cfg_path}): {e}")
        return []

def init_db(db_path: Path):
    """Ensures necessary sqlite tables exist so the script runs cleanly on fresh checkouts."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS watchlist (
            domain TEXT PRIMARY KEY,
            frequency TEXT DEFAULT 'daily',
            added_utc TEXT,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS registry_cache (
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
        CREATE TABLE IF NOT EXISTS registry_counters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT UNIQUE,
            total_domains INTEGER,
            domains_last_month INTEGER,
            domains_last_24h INTEGER,
            total_registrars INTEGER,
            recorded_utc TEXT
        );
        CREATE TABLE IF NOT EXISTS watch_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT,
            old_status TEXT,
            new_status TEXT,
            recorded_utc TEXT
        );
    """)
    conn.commit()
    conn.close()

def init_watch_log(log_path: Path):
    if not log_path.exists():
        with open(log_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_utc", "domain", "old_status", "new_status", "http_status", "raw_rdap_status", "event_type", "notes", "source"])

def run_daily_watch(repo_root: Optional[Path] = None, is_demo: bool = False, db_path: Optional[Path] = None, log_path: Optional[Path] = None):
    root = repo_root or REPO_ROOT
    is_demo = is_demo or ("--demo" in sys.argv)
    
    scout_db = db_path or (root / "demo_data" / "scout.db" if is_demo else root / "scout.db")
    watch_log = log_path or (root / "demo_data" / "watch_log.csv" if is_demo else root / "watch_log.csv")

    init_db(scout_db)
    init_watch_log(watch_log)
    logger.info(f"Starting Daily Watch Run (Demo={is_demo})...")

    # 1. Fetch public counters snapshot
    watch_engine = WatchEngine(db_path=scout_db)
    if not is_demo:
        snapshot = watch_engine.fetch_and_record_counters()
        if snapshot:
            logger.info(f"Recorded Register.si counters: {snapshot.total_domains} total, {snapshot.domains_last_24h} in 24h.")
        else:
            logger.warning("Could not fetch Register.si public counters.")

    # 2. Gather Watch Targets
    conn = sqlite3.connect(scout_db)
    cur = conn.cursor()

    # Target Group A: From YAML config
    cfg_targets = load_watchlist_config(root)
    watchlist_domains = [item["domain"] for item in cfg_targets]
    target_notes_map = {item["domain"]: item["notes"] for item in cfg_targets}

    # Also include any domains from sqlite watchlist table
    try:
        cur.execute("SELECT domain, notes FROM watchlist")
        for row in cur.fetchall():
            d = row[0].strip().lower()
            if d not in watchlist_domains:
                watchlist_domains.append(d)
                target_notes_map[d] = row[1] or ""
    except Exception:
        pass

    # Target Group B: Earliest-expiring registered names
    expiring_targets = []
    exp_csv = root / ("demo_data/expiring_soon.csv" if is_demo else "expiring_soon.csv")
    if exp_csv.exists():
        try:
            import pandas as pd
            df_exp = pd.read_csv(exp_csv)
            if "domain" in df_exp.columns:
                expiring_targets = df_exp["domain"].head(50).tolist()
        except Exception as e:
            logger.warning(f"Could not read expiring_soon.csv: {e}")

    # Deduplicate and cap
    all_targets = []
    for d in watchlist_domains + expiring_targets:
        if d and d not in all_targets:
            all_targets.append(d)
    all_targets = all_targets[:MAX_DAILY_LOOKUPS]

    logger.info(f"Targeting {len(all_targets)} domains ({len(watchlist_domains)} watchlist + {len(expiring_targets)} expiring soon).")

    # 3. Execute Lookups
    log_entries = []
    if is_demo:
        # Offline synthetic execution
        for idx, domain in enumerate(all_targets, 1):
            cur.execute("SELECT rdap_status FROM registry_cache WHERE domain = ?", (domain,))
            prev_row = cur.fetchone()
            old_status = prev_row[0] if prev_row else "UNKNOWN"
            new_status = old_status if old_status != "UNKNOWN" else "AVAILABLE_CANDIDATE"
            lookup_utc = datetime.now(timezone.utc).isoformat()
            raw_rdap_status = "synthetic_fixture"
            event_type = "DEMO_CHECK"
            notes = target_notes_map.get(domain, "Demo scheduled watch")
            log_entries.append([
                lookup_utc, domain, old_status, new_status, 404, raw_rdap_status, event_type, notes, "run_daily_watch.py"
            ])
            logger.info(f"[DEMO {idx:2d}/{len(all_targets)}] {domain:20s}: {old_status} -> {new_status}")
    else:
        rdap_client = RDAPClient(db_path=scout_db, min_interval_seconds=1.05)
        for idx, domain in enumerate(all_targets, 1):
            cur.execute("SELECT rdap_status FROM registry_cache WHERE domain = ?", (domain,))
            prev_row = cur.fetchone()
            old_status = prev_row[0] if prev_row else "UNKNOWN"

            res = rdap_client.check_domain(domain, force_refresh=True)
            lookup_utc = datetime.now(timezone.utc).isoformat()
            new_status = res.status.value

            raw_statuses = list(res.raw_statuses) if res.raw_statuses else []
            if res.http_status_code == 404:
                raw_rdap_status = "not_found"
            elif raw_statuses:
                raw_rdap_status = "; ".join(raw_statuses)
            else:
                raw_rdap_status = "none"

            event_type = "STATUS_CHANGE" if old_status != new_status else "ROUTINE_CHECK"
            notes = target_notes_map.get(domain, "Daily automated monitor")

            log_entries.append([
                lookup_utc, domain, old_status, new_status, res.http_status_code, raw_rdap_status, event_type, notes, "run_daily_watch.py"
            ])
            logger.info(f"[{idx:2d}/{len(all_targets)}] {domain:20s}: {old_status} -> {new_status} ({res.http_status_code}, raw: {raw_rdap_status})")

    # 4. Append to watch_log.csv
    if log_entries:
        with open(watch_log, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(log_entries)
        logger.info(f"Appended {len(log_entries)} rows to {watch_log}.")

    conn.close()
    return log_entries

def main():
    run_daily_watch()

if __name__ == "__main__":
    main()
