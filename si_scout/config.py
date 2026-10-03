"""
Configuration, Budget Model, and Registrar Settings for SI Scout.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

DEFAULT_TOTAL_BUDGET = 200.00
DEFAULT_RESERVE_PCT = 0.10
MAX_PRICE_AGE_DAYS = 7
MIN_RATIONALE_WORDS = 15
MAX_CHECK_AGE_MINUTES = 60
MAX_CONFIRMATION_AGE_MINUTES = 60

@dataclass
class RegistrarInfo:
    id: str
    name: str
    year1_usd: float
    renewal_usd: float
    as_of: str
    checkout_url_template: str
    currency: str
    notes: str
    is_stale: bool
    carry_3yr: float

    def get_checkout_url(self, domain: str) -> str:
        return self.checkout_url_template.format(domain=domain)

def check_price_freshness(as_of_iso: Optional[str], max_days: int = MAX_PRICE_AGE_DAYS) -> bool:
    """Returns True if the timestamp is less than max_days old."""
    if not as_of_iso:
        return False
    try:
        dt = datetime.fromisoformat(as_of_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age = now - dt
        return age.total_seconds() <= max_days * 86400
    except Exception:
        return False

def calculate_budget(total_budget: float = DEFAULT_TOTAL_BUDGET,
                     reserve_pct: float = DEFAULT_RESERVE_PCT,
                     carry_3yr: float = 39.35) -> Dict[str, Any]:
    """
    Budget Model:
    carry_3yr = year1_price + 2 * renewal_price
    max_names = floor((total_budget - reserve) / carry_3yr)
    """
    reserve_amount = round(total_budget * reserve_pct, 2)
    effective_budget = round(total_budget - reserve_amount, 2)
    max_names = math.floor(effective_budget / carry_3yr) if carry_3yr > 0 else 0
    total_committed = round(max_names * carry_3yr, 2)
    remaining_cash = round(effective_budget - total_committed, 2)

    return {
        "total_budget": total_budget,
        "reserve_pct": reserve_pct,
        "reserve_amount": reserve_amount,
        "effective_budget": effective_budget,
        "carry_3yr_per_name": carry_3yr,
        "max_names": max_names,
        "total_committed": total_committed,
        "remaining_cash": remaining_cash
    }

def load_registrars(path: Optional[Path] = None) -> Dict[str, RegistrarInfo]:
    if path is None:
        path = Path(__file__).parent / "registrars.yaml"
    
    if not path.exists():
        raise FileNotFoundError(f"Registrars file not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    registrars_dict = {}
    for reg_id, reg_data in data.get("registrars", {}).items():
        year1 = float(reg_data.get("year1_usd", 0.0))
        renewal = float(reg_data.get("renewal_usd", 0.0))
        as_of = str(reg_data.get("as_of", ""))
        carry_3yr = round(year1 + (2 * renewal), 2)
        is_stale = not check_price_freshness(as_of)

        registrars_dict[reg_id] = RegistrarInfo(
            id=reg_id,
            name=reg_data.get("name", reg_id),
            year1_usd=year1,
            renewal_usd=renewal,
            as_of=as_of,
            checkout_url_template=reg_data.get("checkout_url_template", ""),
            currency=reg_data.get("currency", "USD"),
            notes=reg_data.get("notes", ""),
            is_stale=is_stale,
            carry_3yr=carry_3yr
        )
    return registrars_dict

def get_cheapest_registrar(registrars: Dict[str, RegistrarInfo], allow_stale: bool = False) -> Optional[RegistrarInfo]:
    """Selects the registrar with lowest 3-year carry cost. Excludes stale unless allow_stale=True."""
    valid = [r for r in registrars.values() if not r.is_stale or allow_stale]
    if not valid:
        return None
    return min(valid, key=lambda r: r.carry_3yr)

def load_blocklist(path: Optional[Path] = None) -> Dict[str, List[str]]:
    if path is None:
        path = Path(__file__).parent / "blocklist.yaml"
    if not path.exists():
        return {"brands": [], "public_figures_and_entities": [], "slovenian_and_governmental": []}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {
        "brands": [b.lower() for b in data.get("brands", [])],
        "public_figures_and_entities": [p.lower() for p in data.get("public_figures_and_entities", [])],
        "slovenian_and_governmental": [g.lower() for g in data.get("slovenian_and_governmental", [])]
    }

def load_reserved_domains(path: Optional[Path] = None) -> Dict[str, str]:
    if path is None:
        path = Path(__file__).parent / "reserved_domains.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("reserved_domains", []) if isinstance(data, dict) else data
    return {item["domain"].lower(): item["reason"] for item in items}

def load_config() -> Dict[str, Any]:
    registrars = load_registrars()
    cheapest = get_cheapest_registrar(registrars)
    carry_3yr = cheapest.carry_3yr if cheapest else 39.35
    budget = calculate_budget(carry_3yr=carry_3yr)
    blocklist = load_blocklist()
    reserved = load_reserved_domains()

    return {
        "registrars": registrars,
        "cheapest_registrar": cheapest,
        "budget": budget,
        "blocklist": blocklist,
        "reserved_domains": reserved
    }
