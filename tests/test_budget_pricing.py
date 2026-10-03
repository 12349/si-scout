import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from si_scout.config import load_config, load_registrars, calculate_budget, check_price_freshness, RegistrarInfo

def test_budget_math():
    # Carry 3yr = year1 + 2 * renewal
    year1 = 12.13
    renewal = 13.61
    carry_3yr = year1 + (2 * renewal)
    assert round(carry_3yr, 2) == 39.35

    budget_info = calculate_budget(total_budget=200.0, reserve_pct=0.10, carry_3yr=carry_3yr)
    assert budget_info["total_budget"] == 200.0
    assert budget_info["reserve_amount"] == 20.0
    assert budget_info["effective_budget"] == 180.0
    # floor(180.0 / 39.35) = 4
    assert budget_info["max_names"] == 4
    assert budget_info["remaining_cash"] == pytest.approx(180.0 - (4 * 39.35), 0.01)

def test_price_freshness():
    now = datetime.now(timezone.utc)
    fresh_date = (now - timedelta(days=2)).isoformat()
    stale_date = (now - timedelta(days=8)).isoformat()

    assert check_price_freshness(fresh_date, max_days=7) is True
    assert check_price_freshness(stale_date, max_days=7) is False
    assert check_price_freshness("invalid-date", max_days=7) is False
    assert check_price_freshness(None, max_days=7) is False

def test_registrars_loading(tmp_path):
    yaml_content = """
registrars:
  dynadot:
    name: "Dynadot"
    year1_usd: 12.13
    renewal_usd: 13.61
    as_of: "2026-09-30T00:00:00Z"
    checkout_url_template: "https://www.dynadot.com/domain/search.html?domain={domain}"
    currency: "USD"
  hostinger:
    name: "Hostinger"
    year1_usd: 11.99
    renewal_usd: 16.99
    as_of: "2026-09-20T00:00:00Z"  # > 7 days old
    checkout_url_template: "https://www.hostinger.com/domain-checker?domain={domain}"
    currency: "USD"
"""
    yaml_file = tmp_path / "registrars.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    registrars = load_registrars(yaml_file)
    assert len(registrars) == 2
    assert registrars["dynadot"].is_stale is False
    assert registrars["hostinger"].is_stale is True
    assert registrars["dynadot"].carry_3yr == pytest.approx(39.35, 0.01)
    assert registrars["hostinger"].carry_3yr == pytest.approx(45.97, 0.01)
