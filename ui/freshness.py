"""
Freshness Evaluation and Alert Logic for SI Scout UI.
Enforces Loud Red Banners if:
1. Registrar prices are older than 7 days
2. Domain availability check is older than 24 hours
3. Latest scan is older than 24 hours

In demo mode (is_demo=True):
Timestamps are fixed synthetic fixtures. Staleness warnings are suppressed
and the banner clearly displays 'Demo data timestamps are fixed'.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

MAX_PRICE_AGE_DAYS = 7
MAX_SCAN_AGE_HOURS = 24
MAX_CHECK_AGE_HOURS = 24
MAX_READY_CHECK_AGE_MINUTES = 60

def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        clean = dt_str.strip().replace(" UTC", "+00:00").replace("Z", "+00:00")
        if " " in clean and "+" not in clean:
            # Format like '2026-09-30 19:20:18+00:00'
            clean = clean.replace(" ", "T") + "+00:00"
        return datetime.fromisoformat(clean)
    except Exception:
        return None

def evaluate_freshness(scan_time_iso: Optional[str] = None,
                       check_time_iso: Optional[str] = None,
                       price_time_iso: Optional[str] = None,
                       is_demo: bool = False) -> Dict:
    if is_demo:
        return {
            "is_all_fresh": True,
            "warnings": [],
            "price_fresh": True,
            "scan_fresh": True,
            "check_fresh": True,
            "check_fresh_60m": True,
            "check_age_minutes": None,
            "is_demo": True,
            "demo_notice": "Demo data timestamps are fixed"
        }

    now = datetime.now(timezone.utc)
    warnings: List[str] = []

    # 1. Price freshness check (>7 days)
    price_dt = parse_iso_datetime(price_time_iso)
    if not price_dt:
        warnings.append("Registrar price data has no verified timestamp.")
    else:
        price_age_days = (now - price_dt).total_seconds() / 86400.0
        if price_age_days > MAX_PRICE_AGE_DAYS:
            warnings.append(f"Registrar prices are older than 7 days ({price_age_days:.1f} days old). Prices are STALE.")

    # 2. Latest scan age check (>24 hours)
    scan_dt = parse_iso_datetime(scan_time_iso)
    if not scan_dt:
        warnings.append("No recorded scan found. Please run a scan to refresh data.")
    else:
        scan_age_hours = (now - scan_dt).total_seconds() / 3600.0
        if scan_age_hours > MAX_SCAN_AGE_HOURS:
            warnings.append(f"Last scan is older than 24 hours ({scan_age_hours:.1f} hours old). Re-scan recommended.")

    # 3. Individual candidate check age (>60 minutes for readiness; >24 hours for scan staleness)
    check_age_minutes: Optional[float] = None
    check_fresh_60m = True
    if check_time_iso:
        check_dt = parse_iso_datetime(check_time_iso)
        if not check_dt:
            warnings.append("Domain availability check has no verified timestamp.")
            check_fresh_60m = False
        else:
            check_age_minutes = (now - check_dt).total_seconds() / 60.0
            if check_age_minutes > MAX_READY_CHECK_AGE_MINUTES:
                check_fresh_60m = False
                warnings.append(f"Availability check is older than 60 minutes ({int(check_age_minutes)} min old). Re-check required before buying.")
            elif check_age_minutes < 0:
                check_age_minutes = 0.0

    return {
        "is_all_fresh": len(warnings) == 0,
        "warnings": warnings,
        "price_fresh": not any("registrar prices" in w.lower() for w in warnings),
        "scan_fresh": not any("last scan" in w.lower() for w in warnings),
        "check_fresh": check_fresh_60m,
        "check_fresh_60m": check_fresh_60m,
        "check_age_minutes": round(check_age_minutes, 1) if check_age_minutes is not None else None,
        "is_demo": False,
        "demo_notice": None
    }
