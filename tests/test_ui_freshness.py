import pytest
from datetime import datetime, timedelta, timezone
from ui.freshness import evaluate_freshness

def test_freshness_all_fresh():
    now = datetime.now(timezone.utc)
    scan_time = (now - timedelta(hours=2)).isoformat()
    check_time = (now - timedelta(minutes=20)).isoformat()
    price_time = (now - timedelta(days=2)).isoformat()

    status = evaluate_freshness(scan_time_iso=scan_time, check_time_iso=check_time, price_time_iso=price_time)
    assert status["is_all_fresh"] is True
    assert len(status["warnings"]) == 0
    assert status["check_fresh_60m"] is True
    assert status["check_age_minutes"] is not None

def test_freshness_stale_scan():
    now = datetime.now(timezone.utc)
    stale_scan = (now - timedelta(hours=26)).isoformat() # > 24 hours
    check_time = (now - timedelta(minutes=20)).isoformat()
    price_time = (now - timedelta(days=2)).isoformat()

    status = evaluate_freshness(scan_time_iso=stale_scan, check_time_iso=check_time, price_time_iso=price_time)
    assert status["is_all_fresh"] is False
    assert any("scan is older than 24 hours" in w.lower() for w in status["warnings"])

def test_freshness_stale_prices():
    now = datetime.now(timezone.utc)
    scan_time = (now - timedelta(hours=2)).isoformat()
    check_time = (now - timedelta(minutes=20)).isoformat()
    stale_price = (now - timedelta(days=9)).isoformat() # > 7 days

    status = evaluate_freshness(scan_time_iso=scan_time, check_time_iso=check_time, price_time_iso=stale_price)
    assert status["is_all_fresh"] is False
    assert any("registrar prices are older than 7 days" in w.lower() for w in status["warnings"])

def test_freshness_check_age_60_minutes_rule():
    now = datetime.now(timezone.utc)
    check_time = (now - timedelta(minutes=75)).isoformat() # > 60 minutes
    status = evaluate_freshness(check_time_iso=check_time)
    assert status["check_fresh_60m"] is False
    assert status["check_age_minutes"] >= 74
    assert any("60 minutes" in w for w in status["warnings"])

