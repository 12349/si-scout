"""
Human Rationale Gate & Buy-Readiness Evaluator for SI Scout.
Strictly enforces Phase A and Rule 3:
- Rationales require at least 15 words
- Stored with author="human", timestamp, and self_written=True
- Requires confirmation tickbox: "I wrote this myself"
- Never auto-fills or suggests text
- Any legacy, string-only, or missing-author rationale is treated as "source unknown: please rewrite"
  and CANNOT count toward the gate.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from si_scout.config import MIN_RATIONALE_WORDS, MAX_CHECK_AGE_MINUTES, MAX_PRICE_AGE_DAYS, MAX_CONFIRMATION_AGE_MINUTES

MIN_WORDS = MIN_RATIONALE_WORDS

def validate_human_rationale(entry: Any,
                             verified_checkbox: bool = False,
                             author: str = "human",
                             timestamp: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validates a human rationale entry.
    Accepts either:
    - a raw text string alongside explicit flags (from UI form submission)
    - a dictionary entry from rationales.json
    """
    if isinstance(entry, dict):
        text = str(entry.get("rationale", "")).strip()
        auth = str(entry.get("author", "")).strip().lower()
        self_written = bool(entry.get("self_written", False) or entry.get("verified_by_user", False))
        ts = entry.get("timestamp") or entry.get("created_utc")
    elif isinstance(entry, str):
        text = entry.strip()
        auth = author.strip().lower() if author else "unknown"
        self_written = bool(verified_checkbox)
        ts = timestamp or datetime.now(timezone.utc).isoformat()
    else:
        return False, "source unknown: please rewrite"

    if not text:
        return False, "Rationale is empty. You must explain who would pay 10x and why."

    if auth != "human" or not self_written or not ts:
        return False, "source unknown: please rewrite"

    words = text.split()
    if len(words) < MIN_WORDS:
        return False, f"Rationale must contain at least {MIN_WORDS} words (currently {len(words)} words)."

    return True, "Valid human rationale."

def validate_registrar_confirmation(entry: Any, now_utc: Optional[datetime] = None) -> Tuple[bool, str]:
    """
    Validates Gate 6: "Confirmed at a registrar checkout."
    Required fields:
    - author: strictly "human"
    - registrar: non-empty registrar name
    - checked_utc: valid ISO timestamp
    - result: one of ["available", "taken", "already taken", "premium", "error", "registry busy / could not confirm"]
    
    Only 'available' with author='human' passes Gate 6.
    'registry busy / could not confirm' fails the gate, shows attempt time, and allows unlimited retries.
    """
    if not isinstance(entry, dict):
        return False, "Gate 6: Missing or invalid registrar checkout confirmation"

    auth = str(entry.get("author", "")).strip().lower()
    reg = str(entry.get("registrar", "")).strip()
    ts = str(entry.get("checked_utc", "")).strip()
    res = str(entry.get("result", "")).strip().lower()

    if auth != "human":
        return False, "Gate 6: Author must be 'human' (never automated or scraped)"

    if not reg:
        return False, "Gate 6: Registrar name is required"

    if res == "registry busy / could not confirm":
        return False, f"Gate 6: Registry busy / could not confirm at {ts} (gate failed; unlimited retries allowed)"

    if res in ["taken", "already taken"]:
        return False, f"Gate 6: Domain reported '{res}' at {reg} checkout ({ts})"

    if res == "premium":
        return False, f"Gate 6: Domain reported as premium pricing at {reg} checkout ({ts})"

    if res == "error":
        return False, f"Gate 6: Registrar checkout error at {reg} ({ts})"

    if not ts or str(ts).strip().upper() == "UNKNOWN":
        return False, "Gate 6: Attempt timestamp is required (cannot be UNKNOWN)"

    # Validate that ts is a valid real UTC time and enforce 60-minute expiration
    try:
        clean_ts = str(ts).replace("Z", "+00:00")
        attempt_dt = datetime.fromisoformat(clean_ts)
        if attempt_dt.tzinfo is None:
            attempt_dt = attempt_dt.replace(tzinfo=timezone.utc)
    except Exception:
        return False, f"Gate 6: Invalid attempt timestamp format '{ts}' (must be a real UTC time)"

    curr_dt = now_utc if now_utc is not None else datetime.now(timezone.utc)
    if curr_dt.tzinfo is None:
        curr_dt = curr_dt.replace(tzinfo=timezone.utc)

    elapsed_minutes = (curr_dt - attempt_dt).total_seconds() / 60.0
    if elapsed_minutes > 60.0:
        return False, "Confirmation expired: re-confirm at checkout."

    if res == "available":
        return True, f"Confirmed available at {reg} checkout ({ts})"

    return False, f"Gate 6: Unrecognized registrar checkout result '{res}'"

def get_registrar_confirmation_remaining_minutes(entry: Optional[Dict], now_utc: Optional[datetime] = None) -> Optional[float]:
    """Returns minutes remaining before the registrar confirmation expires (60 min window), or <= 0 if expired."""
    if not entry or not isinstance(entry, dict):
        return None
    ts = str(entry.get("checked_utc", "")).strip()
    if not ts or ts.upper() == "UNKNOWN":
        return None
    try:
        clean_ts = ts.replace("Z", "+00:00")
        attempt_dt = datetime.fromisoformat(clean_ts)
        if attempt_dt.tzinfo is None:
            attempt_dt = attempt_dt.replace(tzinfo=timezone.utc)
        curr = now_utc if now_utc is not None else datetime.now(timezone.utc)
        if curr.tzinfo is None:
            curr = curr.replace(tzinfo=timezone.utc)
        elapsed_minutes = (curr - attempt_dt).total_seconds() / 60.0
        remaining = 60.0 - elapsed_minutes
        return round(remaining, 1)
    except Exception:
        return None

def check_buy_readiness(rdap_status: str,
                        is_price_stale: bool,
                        is_scan_stale: bool,
                        is_check_stale: bool,
                        has_trademark_flag: bool,
                        human_rationale_valid: bool,
                        within_budget: bool,
                        registrar_confirmation: Optional[Dict] = None,
                        check_age_minutes: Optional[float] = None,
                        now_utc: Optional[datetime] = None) -> Dict:
    """Evaluates the live gate checklist for buying a domain candidate."""
    blocking_reasons: List[str] = []

    if rdap_status != "AVAILABLE_CANDIDATE":
        blocking_reasons.append(f"Domain is not available in registry (Status: {rdap_status})")

    if is_price_stale:
        blocking_reasons.append("Registrar price data is stale (>7 days old)")

    if is_check_stale or is_scan_stale:
        age_str = f"{int(check_age_minutes)} min old" if check_age_minutes is not None else ">60 min old"
        blocking_reasons.append(f"Availability check is older than 60 minutes ({age_str}; re-check required)")

    if has_trademark_flag:
        blocking_reasons.append("Potential trademark conflict risk flagged")

    if not human_rationale_valid:
        blocking_reasons.append("Human end-user rationale missing, unverified, or source unknown (>=15 words + author:human required)")

    if not within_budget:
        blocking_reasons.append("Portfolio cost exceeds USD 200 budget ceiling")

    # Gate 6: Confirmed at a registrar checkout
    gate_6_pass = False
    if not registrar_confirmation:
        blocking_reasons.append("Gate 6: Confirmed at a registrar checkout missing (human checkout verification required)")
    else:
        is_valid_conf, conf_msg = validate_registrar_confirmation(registrar_confirmation, now_utc=now_utc)
        if not is_valid_conf:
            blocking_reasons.append(conf_msg)
        else:
            gate_6_pass = True

    return {
        "is_ready": len(blocking_reasons) == 0,
        "blocking_reasons": blocking_reasons,
        "gates": {
            "available_now": rdap_status == "AVAILABLE_CANDIDATE",
            "price_fresh": not is_price_stale,
            "check_fresh": not (is_check_stale or is_scan_stale),
            "no_trademark": not has_trademark_flag,
            "human_rationale": human_rationale_valid,
            "fits_budget": within_budget,
            "registrar_confirmed": gate_6_pass
        }
    }
