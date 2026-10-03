"""
Twin Signal Analyzer (.com and .ai) for SI Scout.
Evaluates the existence, active status, or parking of the matching .com and .ai domains.
Recorded as context, not proof.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import logging
from pathlib import Path
import re
import socket
import sqlite3
from typing import Dict, Optional, Tuple
import time
import requests

logger = logging.getLogger(__name__)

PARKING_KEYWORDS = [
    "for sale", "buy this domain", "parked", "domain broker",
    "hugedomains", "sedo", "dan.com", "godaddy.com/domainsearch",
    "domain parking", "inquire about this domain", "is available for purchase",
    "afternic", "bodis", "domainnamesales", "domain holder"
]

class TwinStatus(str, Enum):
    UNREGISTERED = "UNREGISTERED"
    ACTIVE_SITE = "ACTIVE_SITE"
    PARKED_OR_FOR_SALE = "PARKED_OR_FOR_SALE"
    UNKNOWN = "UNKNOWN"

@dataclass
class TwinResult:
    label: str
    com_status: TwinStatus
    com_details: str
    ai_status: TwinStatus
    ai_details: str
    checked_utc: str

class TwinAnalyzer:
    def __init__(self, db_path: Optional[Path] = None, timeout: float = 3.5, min_interval_per_host: float = 1.05):
        self.db_path = db_path or Path("scout.db")
        self.timeout = timeout
        self.min_interval = min_interval_per_host
        self.last_host_time = {}
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS twin_signals (
                    label TEXT PRIMARY KEY,
                    com_status TEXT NOT NULL,
                    com_details TEXT,
                    ai_status TEXT NOT NULL,
                    ai_details TEXT,
                    checked_utc TEXT NOT NULL
                )
            """)
            conn.commit()

    def _get_from_cache(self, label: str) -> Optional[TwinResult]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT com_status, com_details, ai_status, ai_details, checked_utc
                FROM twin_signals WHERE label = ?
            """, (label.lower(),))
            row = cursor.fetchone()
            if row:
                return TwinResult(
                    label=label.lower(),
                    com_status=TwinStatus(row[0]),
                    com_details=row[1] or "",
                    ai_status=TwinStatus(row[2]),
                    ai_details=row[3] or "",
                    checked_utc=row[4]
                )
        return None

    def _save_to_cache(self, result: TwinResult):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO twin_signals 
                (label, com_status, com_details, ai_status, ai_details, checked_utc)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                result.label,
                result.com_status.value,
                result.com_details,
                result.ai_status.value,
                result.ai_details,
                result.checked_utc
            ))
            conn.commit()

    def check_twin(self, domain: str) -> Tuple[TwinStatus, str]:
        """Resolves DNS and probes HTTP to classify status."""
        try:
            ip = socket.gethostbyname(domain)
        except (socket.gaierror, OSError):
            return TwinStatus.UNREGISTERED, "DNS NXDOMAIN"
        except Exception as e:
            return TwinStatus.UNKNOWN, f"DNS error: {str(e)}"

        # If DNS resolved, inspect web response with per-host rate limiting
        now = time.perf_counter()
        last = self.last_host_time.get(domain, 0.0)
        if now - last < self.min_interval:
            time.sleep(self.min_interval - (now - last))
        self.last_host_time[domain] = time.perf_counter()

        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            url = f"http://{domain}"
            resp = requests.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
            text_lower = resp.text.lower()[:15000]

            for kw in PARKING_KEYWORDS:
                if kw in text_lower:
                    return TwinStatus.PARKED_OR_FOR_SALE, f"Detected parking phrase: '{kw}'"

            if resp.status_code == 200:
                title_match = re.search(r'<title[^>]*>(.*?)</title>', resp.text, re.IGNORECASE | re.DOTALL)
                title = title_match.group(1).strip()[:80] if title_match else "Active Site"
                return TwinStatus.ACTIVE_SITE, f"HTTP 200: {title}"

            return TwinStatus.ACTIVE_SITE, f"HTTP {resp.status_code}"

        except requests.exceptions.Timeout:
            return TwinStatus.UNKNOWN, "HTTP connection timed out"
        except Exception as e:
            # Resolved IP exists, but HTTP refused or unreachable
            return TwinStatus.ACTIVE_SITE, f"DNS resolved ({ip}), HTTP unreachable"

    def evaluate_twins(self, label: str, force_refresh: bool = False) -> TwinResult:
        label = label.lower().strip()
        if not force_refresh:
            cached = self._get_from_cache(label)
            if cached:
                return cached

        checked_utc = datetime.now(timezone.utc).isoformat()
        com_status, com_details = self.check_twin(f"{label}.com")
        ai_status, ai_details = self.check_twin(f"{label}.ai")

        result = TwinResult(
            label=label,
            com_status=com_status,
            com_details=com_details,
            ai_status=ai_status,
            ai_details=ai_details,
            checked_utc=checked_utc
        )
        self._save_to_cache(result)
        return result
