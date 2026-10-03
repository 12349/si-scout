"""
Polite Re-Check Controller for SI Scout UI.
Enforces Rule 6:
- Max 25 names per click
- Routes through existing RDAPClient with <=1 req/sec rate limiter and SQLite cache
- Never makes unthrottled calls
"""

from typing import Dict, List, Optional
from pathlib import Path
from si_scout.rdap import RDAPClient, RDAPResult

MAX_RECHECK_PER_CLICK = 25

def perform_recheck_batch(domains: List[str],
                          rdap_client: Optional[RDAPClient] = None,
                          db_path: Optional[Path] = None,
                          max_allowed: int = MAX_RECHECK_PER_CLICK) -> List[Dict]:
    if len(domains) > max_allowed:
        raise ValueError(f"Batch re-check is limited to a maximum of {max_allowed} names per request (received {len(domains)}).")

    client = rdap_client or RDAPClient(db_path=db_path or Path("scout.db"), min_interval_seconds=1.05)
    results = []

    for domain in domains:
        clean = domain.strip().lower()
        if not clean:
            continue
        # Force refresh through registry client
        res: RDAPResult = client.check_domain(clean, force_refresh=True)
        results.append({
            "domain": clean,
            "status": res.status.value,
            "http_status_code": res.http_status_code,
            "checked_utc": res.checked_utc,
            "raw_statuses": res.raw_statuses
        })

    return results
