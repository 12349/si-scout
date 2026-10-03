"""
Authoritative RDAP Client for .si Registry (Register.si).
- Complies strictly with IANA RDAP bootstrap
- Rate limited to <= 1 request/second (polite registry citizen)
- Exponential backoff on 429 and 5xx errors
- SQLite caching for idempotency, instant resume, and audit trail
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import logging
from pathlib import Path
import random
import sqlite3
import time
from typing import Dict, List, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

class RDAPStatus(str, Enum):
    AVAILABLE_CANDIDATE = "AVAILABLE_CANDIDATE"
    REGISTERED = "REGISTERED"
    QUARANTINE_PENDING_DELETE = "QUARANTINE/PENDING_DELETE"
    RESERVED = "RESERVED"
    UNCERTAIN = "UNCERTAIN"

@dataclass
class RDAPResult:
    domain: str
    label: str
    tld: str
    status: RDAPStatus
    http_status_code: int
    raw_statuses: List[str]
    raw_json: Optional[Dict]
    checked_utc: str
    source: str
    notes: str = ""

class RDAPClient:
    DEFAULT_RDAP_BASE = "https://rdap.register.si/domain/"

    def __init__(self,
                 db_path: Optional[Path] = None,
                 rdap_base: str = DEFAULT_RDAP_BASE,
                 min_interval_seconds: float = 1.05,
                 max_retries: int = 3,
                 initial_backoff: float = 1.5,
                 timeout: float = 10.0):
        self.db_path = db_path or Path("scout.db")
        self.rdap_base = rdap_base
        self.min_interval = min_interval_seconds
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.timeout = timeout
        self.last_request_time = 0.0
        self.live_queries_count = 0
        self.max_live_queries = 2000
        from si_scout.config import load_reserved_domains
        try:
            self.reserved_domains = load_reserved_domains()
        except Exception:
            self.reserved_domains = {}
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registry_cache (
                    domain TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    tld TEXT NOT NULL,
                    rdap_status TEXT NOT NULL,
                    http_status_code INTEGER NOT NULL,
                    raw_statuses_json TEXT,
                    raw_rdap_json TEXT,
                    checked_utc TEXT NOT NULL,
                    source TEXT NOT NULL,
                    notes TEXT
                )
            """)
            conn.commit()

    def _rate_limit(self):
        """Ensures at least min_interval seconds between outbound requests."""
        if self.min_interval <= 0:
            return
        now = time.perf_counter()
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.perf_counter()

    def _get_from_cache(self, domain: str) -> Optional[RDAPResult]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT label, tld, rdap_status, http_status_code, raw_statuses_json, raw_rdap_json, checked_utc, source, notes
                FROM registry_cache WHERE domain = ?
            """, (domain.lower(),))
            row = cursor.fetchone()
            if row:
                label, tld, status_str, status_code, raw_stat_json, raw_json_str, checked_utc, source, notes = row
                raw_statuses = json.loads(raw_stat_json) if raw_stat_json else []
                raw_json = json.loads(raw_json_str) if raw_json_str else None
                return RDAPResult(
                    domain=domain.lower(),
                    label=label,
                    tld=tld,
                    status=RDAPStatus(status_str),
                    http_status_code=status_code,
                    raw_statuses=raw_statuses,
                    raw_json=raw_json,
                    checked_utc=checked_utc,
                    source=source,
                    notes=notes or "Cached"
                )
        return None

    def _save_to_cache(self, result: RDAPResult):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO registry_cache 
                (domain, label, tld, rdap_status, http_status_code, raw_statuses_json, raw_rdap_json, checked_utc, source, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.domain,
                result.label,
                result.tld,
                result.status.value,
                result.http_status_code,
                json.dumps(result.raw_statuses),
                json.dumps(result.raw_json) if result.raw_json else None,
                result.checked_utc,
                result.source,
                result.notes
            ))
            conn.commit()

    def check_domain(self, domain: str, force_refresh: bool = False) -> RDAPResult:
        domain = domain.lower().strip()
        parts = domain.rsplit(".", 1)
        label = parts[0]
        tld = parts[1] if len(parts) > 1 else "si"

        if not force_refresh:
            cached = self._get_from_cache(domain)
            if cached:
                return cached

        url = f"{self.rdap_base}{domain}"
        backoff = self.initial_backoff
        checked_utc = datetime.now(timezone.utc).isoformat()
        source = self.rdap_base

        headers = {
            "User-Agent": "SIScout/1.0 (Polite Research Bot; +https://register.si)",
            "Accept": "application/rdap+json, application/json"
        }

        for attempt in range(self.max_retries + 1):
            if self.live_queries_count >= self.max_live_queries:
                raise RuntimeError(f"Total live-query cap of {self.max_live_queries} registry lookups reached. Halting scan per user rule.")
            self._rate_limit()
            self.live_queries_count += 1
            try:
                resp = requests.get(url, headers=headers, timeout=self.timeout)
                status_code = resp.status_code

                if status_code == 200:
                    try:
                        data = resp.json()
                    except Exception:
                        result = RDAPResult(
                            domain=domain, label=label, tld=tld,
                            status=RDAPStatus.UNCERTAIN,
                            http_status_code=status_code,
                            raw_statuses=[], raw_json=None,
                            checked_utc=checked_utc, source=source,
                            notes="Malformed JSON response from registry"
                        )
                        self._save_to_cache(result)
                        return result

                    raw_statuses = [s.lower() for s in data.get("status", [])]
                    
                    # Status evaluation
                    is_quarantine = any("pendingdelete" in s.replace(" ", "").lower() or "quarantine" in s.lower() for s in raw_statuses)
                    is_reserved = any("reserved" in s.lower() for s in raw_statuses)

                    if is_quarantine:
                        status = RDAPStatus.QUARANTINE_PENDING_DELETE
                    elif is_reserved:
                        status = RDAPStatus.RESERVED
                    else:
                        status = RDAPStatus.REGISTERED

                    result = RDAPResult(
                        domain=domain, label=label, tld=tld,
                        status=status,
                        http_status_code=status_code,
                        raw_statuses=raw_statuses,
                        raw_json=data,
                        checked_utc=checked_utc,
                        source=source,
                        notes="Authoritative registry query"
                    )
                    self._save_to_cache(result)
                    return result

                elif status_code == 404:
                    # 404 in RDAP implies object does not exist in registry database
                    # BUT check if name is in official Register.si reserved list (RDAP 404 != registrable)
                    if domain in self.reserved_domains or label in self.reserved_domains:
                        reason = self.reserved_domains.get(domain) or self.reserved_domains.get(label)
                        result = RDAPResult(
                            domain=domain, label=label, tld=tld,
                            status=RDAPStatus.RESERVED,
                            http_status_code=404,
                            raw_statuses=["reserved"],
                            raw_json=None,
                            checked_utc=checked_utc,
                            source=source,
                            notes=f"Registry RDAP 404 but official reserved name: {reason}"
                        )
                    else:
                        result = RDAPResult(
                            domain=domain, label=label, tld=tld,
                            status=RDAPStatus.AVAILABLE_CANDIDATE,
                            http_status_code=404,
                            raw_statuses=[],
                            raw_json=None,
                            checked_utc=checked_utc,
                            source=source,
                            notes="Registry RDAP 404 Not Found"
                        )
                    self._save_to_cache(result)
                    return result

                elif status_code in (429, 500, 502, 503, 504):
                    if attempt < self.max_retries:
                        sleep_time = backoff + random.uniform(0.1, 0.5)
                        logger.warning(f"RDAP {status_code} for {domain}. Backing off {sleep_time:.2f}s...")
                        time.sleep(sleep_time)
                        backoff *= 2.0
                        continue
                    else:
                        result = RDAPResult(
                            domain=domain, label=label, tld=tld,
                            status=RDAPStatus.UNCERTAIN,
                            http_status_code=status_code,
                            raw_statuses=[], raw_json=None,
                            checked_utc=checked_utc, source=source,
                            notes=f"Registry error {status_code} after {self.max_retries} retries"
                        )
                        self._save_to_cache(result)
                        return result
                else:
                    result = RDAPResult(
                        domain=domain, label=label, tld=tld,
                        status=RDAPStatus.UNCERTAIN,
                        http_status_code=status_code,
                        raw_statuses=[], raw_json=None,
                        checked_utc=checked_utc, source=source,
                        notes=f"Unexpected HTTP status {status_code}"
                    )
                    self._save_to_cache(result)
                    return result

            except requests.exceptions.Timeout:
                if attempt < self.max_retries:
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                result = RDAPResult(
                    domain=domain, label=label, tld=tld,
                    status=RDAPStatus.UNCERTAIN,
                    http_status_code=0,
                    raw_statuses=[], raw_json=None,
                    checked_utc=checked_utc, source=source,
                    notes="Network timeout to registry RDAP"
                )
                self._save_to_cache(result)
                return result
            except requests.exceptions.RequestException as e:
                result = RDAPResult(
                    domain=domain, label=label, tld=tld,
                    status=RDAPStatus.UNCERTAIN,
                    http_status_code=0,
                    raw_statuses=[], raw_json=None,
                    checked_utc=checked_utc, source=source,
                    notes=f"Network error: {str(e)}"
                )
                self._save_to_cache(result)
                return result

        return RDAPResult(
            domain=domain, label=label, tld=tld,
            status=RDAPStatus.UNCERTAIN,
            http_status_code=0,
            raw_statuses=[], raw_json=None,
            checked_utc=checked_utc, source=source,
            notes="Exceeded retries without definitive status"
        )
