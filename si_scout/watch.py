"""
Watch Mode Engine for SI Scout.
Tracks daily diffs, monitors quarantine / drop transitions, and records
daily time series snapshots of Register.si's public registration counters.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import sqlite3
from typing import Dict, List, Optional, Tuple
import requests
from si_scout.rdap import RDAPClient, RDAPStatus

logger = logging.getLogger(__name__)

@dataclass
class RegistryCounterSnapshot:
    snapshot_date: str
    total_domains: int
    domains_last_month: int
    domains_last_24h: int
    total_registrars: int
    recorded_utc: str

class WatchEngine:
    REGISTER_SI_URL = "https://www.register.si/"

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("scout.db")
        self._init_db()

    def _init_db(self):
        if str(self.db_path) == ":memory:":
            self.conn = sqlite3.connect(":memory:")
            conn = self.conn
        else:
            conn = sqlite3.connect(self.db_path)

        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registry_counters (
                    snapshot_date TEXT PRIMARY KEY,
                    total_domains INTEGER NOT NULL,
                    domains_last_month INTEGER NOT NULL,
                    domains_last_24h INTEGER NOT NULL,
                    total_registrars INTEGER NOT NULL,
                    recorded_utc TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watch_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    old_status TEXT,
                    new_status TEXT NOT NULL,
                    recorded_utc TEXT NOT NULL
                )
            """)
            conn.commit()
        if str(self.db_path) != ":memory:":
            conn.close()

    def _get_connection(self):
        if str(self.db_path) == ":memory:":
            return self.conn
        return sqlite3.connect(self.db_path)

    def parse_counters_from_html(self, html: str) -> Optional[RegistryCounterSnapshot]:
        """Parses Register.si homepage stats block."""
        try:
            stat_match = re.search(r'data-statistics.*?(?=</section>|</div>\s*</div>\s*</div>\s*</div>\s*</div>)', html, re.DOTALL)
            block = stat_match.group(0) if stat_match else html

            # Clean markup to text
            text = re.sub(r'<[^>]+>', ' ', block)
            text = ' '.join(text.split())

            def clean_num(s: str) -> int:
                clean = re.sub(r'[^\d]', '', s)
                return int(clean) if clean else 0

            # Match patterns like "233.469 .si domen"
            m_total = re.search(r'([\d\.,]+)\s*\.si domen', text, re.IGNORECASE)
            m_month = re.search(r'([\d\.,]+)\s*registriranih \.si domen v prej[^\s]+ mesecu', text, re.IGNORECASE)
            m_24h = re.search(r'([\d\.,]+)\s*registriranih \.si domen v zadnjih 24 urah', text, re.IGNORECASE)
            m_regs = re.search(r'([\d\.,]+)\s*registrarjev', text, re.IGNORECASE)

            total = clean_num(m_total.group(1)) if m_total else 0
            month = clean_num(m_month.group(1)) if m_month else 0
            day24 = clean_num(m_24h.group(1)) if m_24h else 0
            regs = clean_num(m_regs.group(1)) if m_regs else 0

            if total > 0 or day24 > 0:
                now_utc = datetime.now(timezone.utc)
                return RegistryCounterSnapshot(
                    snapshot_date=now_utc.strftime("%Y-%m-%d"),
                    total_domains=total,
                    domains_last_month=month,
                    domains_last_24h=day24,
                    total_registrars=regs,
                    recorded_utc=now_utc.isoformat()
                )
        except Exception as e:
            logger.error(f"Error parsing Register.si public statistics: {e}")
        return None

    def fetch_and_record_counters(self) -> Optional[RegistryCounterSnapshot]:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SIScout/1.0"}
        try:
            resp = requests.get(self.REGISTER_SI_URL, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                snapshot = self.parse_counters_from_html(resp.text)
                if snapshot:
                    self.save_counter_snapshot(snapshot)
                    return snapshot
        except Exception as e:
            logger.warning(f"Could not fetch public counters from {self.REGISTER_SI_URL}: {e}")
        return None

    def save_counter_snapshot(self, snapshot: RegistryCounterSnapshot):
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO registry_counters
                    (snapshot_date, total_domains, domains_last_month, domains_last_24h, total_registrars, recorded_utc)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    snapshot.snapshot_date,
                    snapshot.total_domains,
                    snapshot.domains_last_month,
                    snapshot.domains_last_24h,
                    snapshot.total_registrars,
                    snapshot.recorded_utc
                ))
        finally:
            if str(self.db_path) != ":memory:":
                conn.close()

    def get_counter_history(self) -> List[RegistryCounterSnapshot]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT snapshot_date, total_domains, domains_last_month, domains_last_24h, total_registrars, recorded_utc
                FROM registry_counters ORDER BY snapshot_date ASC
            """)
            rows = cursor.fetchall()
            return [
                RegistryCounterSnapshot(
                    snapshot_date=r[0],
                    total_domains=r[1],
                    domains_last_month=r[2],
                    domains_last_24h=r[3],
                    total_registrars=r[4],
                    recorded_utc=r[5]
                ) for r in rows
            ]
        finally:
            if str(self.db_path) != ":memory:":
                conn.close()

    def compute_status_diff(self, prev_statuses: Dict[str, str], current_statuses: Dict[str, str]) -> List[Dict]:
        diffs = []
        for domain, curr_status in current_statuses.items():
            old_status = prev_statuses.get(domain)
            if old_status and old_status != curr_status:
                diffs.append({
                    "domain": domain,
                    "old_status": old_status,
                    "new_status": curr_status
                })
        return diffs
