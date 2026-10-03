"""
Tests for SI Scout Demo Mode.
Validates that demo mode runs 100% offline, serves synthetic fixtures,
displays the mandatory disclaimer banner, renders the Findings page,
and performs zero network socket calls.
"""

import json
from pathlib import Path
import socket
import pytest
from flask import Flask

from ui.app import create_app
from ui.data import UIDataManager

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_data"

@pytest.fixture
def demo_app():
    app = create_app({"TESTING": True, "DEMO": True})
    return app

@pytest.fixture
def demo_client(demo_app: Flask):
    return demo_app.test_client()

def test_demo_fixtures_exist():
    assert DEMO_DIR.exists()
    assert (DEMO_DIR / "results.csv").exists()
    assert (DEMO_DIR / "calibration.json").exists()
    assert (DEMO_DIR / "findings_data.json").exists()
    assert (DEMO_DIR / "drop_watch.csv").exists()
    assert (DEMO_DIR / "watch_log.csv").exists()

def test_demo_synthetic_naming_convention():
    """Ensure all demo domains use explicit example/test prefixes and no real company names."""
    results_path = DEMO_DIR / "results.csv"
    with open(results_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()][1:] # skip header
    for line in lines:
        domain = line.split(",")[0]
        label = domain.replace(".si", "")
        assert any(label.startswith(p) for p in ["example-", "demo-", "sample-", "test-", "mock-"]), \
            f"Demo domain '{domain}' must start with a synthetic prefix"

def test_demo_banner_displayed_on_all_pages(demo_client):
    """Verify permanent banner 'Demo data. Not real registry results.' is displayed on pages."""
    pages = ["/", "/findings", "/candidates", "/shortlist", "/watch", "/drop-watch", "/calibration", "/scan", "/portfolio", "/glossary"]
    for page in pages:
        res = demo_client.get(page)
        assert res.status_code == 200, f"Page {page} returned status {res.status_code}"
        html = res.get_data(as_text=True)
        assert "Demo data. Not real registry results." in html, f"Page {page} missing mandatory demo banner"
        assert "DEMO MODE" in html

def test_findings_screen_content(demo_client):
    """Verify Findings screen displays funnel, saturation, counter with caption, and chart footers."""
    res = demo_client.get("/findings")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # 1. Funnel
    assert "Screening Funnel Attrition" in html
    assert "NOT IN REGISTRY" in html
    assert "Strict Survivors" in html

    # 2. Saturation
    assert "Saturation by Pattern" in html
    assert "Survival Rate (%)" in html

    # 3. Registry counter caption
    assert "Shows whether the rush continues, not a prediction." in html

    # 4. Calibration warning
    assert "Registrar-vs-Registry Calibration" in html

    # 5. Footers
    assert "Source file:" in html
    assert "Illustrative demo data" in html

def test_demo_mode_zero_network_calls(demo_client, monkeypatch):
    """
    Non-negotiable rule: Demo mode must make zero network calls.
    Fails immediately if any socket connect is attempted during demo requests.
    """
    def forbidden_connect(*args, **kwargs):
        raise RuntimeError("NETWORK CALL ATTEMPTED IN DEMO MODE! Sockets are strictly forbidden.")

    monkeypatch.setattr(socket.socket, "connect", forbidden_connect)

    # Hit all UI views
    routes = [
        "/",
        "/findings",
        "/candidates",
        "/shortlist",
        "/watch",
        "/drop-watch",
        "/calibration",
        "/scan",
        "/portfolio",
        "/glossary",
        "/detail/example-cloud.si",
        "/api/candidates/export/csv",
        "/api/shortlist/export/markdown",
    ]
    for r in routes:
        resp = demo_client.get(r)
        assert resp.status_code == 200, f"Failed on route {r}"

    # Hit action endpoints - should reject safely without network calls
    recheck_resp = demo_client.post("/api/recheck", json={"domains": ["example-cloud.si"]})
    assert recheck_resp.status_code == 400
    assert "disabled in demo mode" in recheck_resp.get_data(as_text=True).lower()

    scan_resp = demo_client.post("/api/scan/start", json={"top": 10})
    assert scan_resp.status_code == 400
    assert "disabled in demo mode" in scan_resp.get_data(as_text=True).lower()

    watch_resp = demo_client.post("/api/watch/run")
    assert watch_resp.status_code == 400
    assert "disabled in demo mode" in watch_resp.get_data(as_text=True).lower()

def test_demo_databases_recreation_when_deleted(tmp_path):
    """
    Validates that if demo_data/scout.db and demo_data/portfolio.db are deleted,
    demo mode automatically recreates both SQLite databases.
    """
    demo_tmp = tmp_path / "demo_data"
    demo_tmp.mkdir()
    for fname in ["results.csv", "calibration.json", "findings_data.json", "drop_watch.csv", "watch_log.csv", "rationales.json", "registrar_confirmations.json"]:
        src = DEMO_DIR / fname
        if src.exists():
            import shutil
            shutil.copy(src, demo_tmp / fname)

    scout_db = demo_tmp / "scout.db"
    portfolio_db = demo_tmp / "portfolio.db"
    if scout_db.exists():
        scout_db.unlink()
    if portfolio_db.exists():
        portfolio_db.unlink()

    assert not scout_db.exists()
    assert not portfolio_db.exists()

    # Recreate on demo app launch
    app = create_app({"TESTING": True, "DEMO": True, "DEMO_DIR": demo_tmp})
    dm = UIDataManager(is_demo=True, demo_dir=demo_tmp)

    assert scout_db.exists(), "demo_data/scout.db was not recreated by demo mode"
    assert portfolio_db.exists(), "demo_data/portfolio.db was not recreated by demo mode"

    # Also test deleting them while demo_data is used
    scout_db.unlink()
    portfolio_db.unlink()
    assert not scout_db.exists()
    assert not portfolio_db.exists()

    # Accessing UIDataManager again recreates them
    dm2 = UIDataManager(is_demo=True, demo_dir=demo_tmp)
    assert scout_db.exists(), "demo_data/scout.db was not recreated on re-instantiation"
    assert portfolio_db.exists(), "demo_data/portfolio.db was not recreated on re-instantiation"

