import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from si_scout.watch import WatchEngine, RegistryCounterSnapshot

def test_parse_public_counters():
    sample_html = """
    <div data-statistics>
        <div class="statistics-inside px-3">
            <span class="d-block text-white h1">233.469</span>
            <p class="m-0">.si domen</p>
        </div>
        <div class="statistics-inside px-3">
            <span class="d-block text-white h1">3.515</span>
            <p class="m-0">registriranih <strong>.si</strong> domen v prejšnjem mesecu</p>
        </div>
        <div class="statistics-inside px-3">
            <span class="d-block text-white h1">10.790</span>
            <p class="m-0">registriranih <strong>.si</strong> domen v zadnjih 24 urah</p>
        </div>
        <div class="statistics-inside px-3">
            <span class="d-block text-white h1">92</span>
            <p class="m-0">registrarjev <strong>.si</strong> domen</p>
        </div>
    </div>
    """
    engine = WatchEngine(db_path=Path(":memory:"))
    snapshot = engine.parse_counters_from_html(sample_html)
    assert snapshot is not None
    assert snapshot.total_domains == 233469
    assert snapshot.domains_last_month == 3515
    assert snapshot.domains_last_24h == 10790
    assert snapshot.total_registrars == 92

def test_diff_reporting(tmp_path):
    db_path = tmp_path / "watch_test.db"
    engine = WatchEngine(db_path=db_path)
    
    # Store initial state
    prev_state = {
        "alpha.si": "REGISTERED",
        "beta.si": "REGISTERED"
    }
    current_state = {
        "alpha.si": "QUARANTINE/PENDING_DELETE",
        "beta.si": "AVAILABLE_CANDIDATE"
    }
    
    diffs = engine.compute_status_diff(prev_state, current_state)
    assert len(diffs) == 2
    assert any(d["domain"] == "alpha.si" and d["new_status"] == "QUARANTINE/PENDING_DELETE" for d in diffs)
    assert any(d["domain"] == "beta.si" and d["new_status"] == "AVAILABLE_CANDIDATE" for d in diffs)

def test_watch_log_schema_and_backfill():
    import csv
    log_path = Path("demo_data/watch_log.csv")
    if not log_path.exists():
        pytest.skip("demo_data/watch_log.csv fixture not found")
    with open(log_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        expected = ["timestamp_utc", "domain", "old_status", "new_status", "http_status", "raw_rdap_status", "event_type", "notes", "source"]
        assert header == expected
        rows = list(reader)
        assert len(rows) >= 1
        for r in rows:
            assert len(r) == len(expected)

def test_expiring_soon_expiration_dates_in_future():
    import pandas as pd
    from datetime import datetime, timezone
    
    csv_path = Path("demo_data/expiring_soon.csv")
    if not csv_path.exists():
        pytest.skip("demo_data/expiring_soon.csv fixture not found")
    
    df = pd.read_csv(csv_path)
    assert len(df) >= 1, "Expected rows in demo expiring_soon.csv"
    
    now = datetime.now(timezone.utc)
    for idx, r in df.iterrows():
        exp_dt = datetime.fromisoformat(r["expiration_date"])
        assert exp_dt >= now, f"Expiry date {exp_dt} for {r['domain']} is earlier than today {now}"
        assert float(r["age_at_expiry_years"]) >= 1.0, f"Invalid age_at_expiry_years for {r['domain']}"


def test_daily_watch_runner_with_demo_fixtures(tmp_path):
    """Verify scripts/run_daily_watch.py runs cleanly on synthetic fixtures with zero network calls."""
    from scripts.run_daily_watch import run_daily_watch
    repo_root = Path(__file__).resolve().parent.parent
    test_db = tmp_path / "scout.db"
    test_log = tmp_path / "watch_log.csv"

    entries = run_daily_watch(
        repo_root=repo_root,
        is_demo=True,
        db_path=test_db,
        log_path=test_log
    )
    assert len(entries) >= 1
    assert test_log.exists()
    with open(test_log, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) >= 2
        header = lines[0].strip().split(",")
        assert "timestamp_utc" in header
        assert "domain" in header



