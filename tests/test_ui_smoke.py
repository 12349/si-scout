import pytest
from pathlib import Path
from ui.app import create_app

@pytest.fixture
def client(tmp_path):
    app = create_app(test_config={
        "TESTING": True,
        "CSV_PATH": tmp_path / "results.csv",
        "DB_PATH": tmp_path / "scout.db",
        "PORTFOLIO_DB_PATH": tmp_path / "portfolio.db",
        "RATIONALES_PATH": tmp_path / "rationales.json"
    })
    return app.test_client()

def test_screen_overview_smoke(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "SI Scout" in html
    assert "Overview" in html
    assert "Screening score, not a value estimate." in html

def test_screen_candidates_smoke(client):
    response = client.get("/candidates")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Candidates" in html

def test_screen_shortlist_smoke(client):
    response = client.get("/shortlist")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Shortlist" in html

def test_screen_watch_smoke(client):
    response = client.get("/watch")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Watch" in html

def test_screen_scan_smoke(client):
    response = client.get("/scan")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Scan Control" in html

def test_screen_portfolio_smoke(client):
    response = client.get("/portfolio")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Portfolio" in html

def test_screen_glossary_smoke(client):
    response = client.get("/glossary")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Glossary" in html

def test_screen_drop_watch_smoke(client):
    response = client.get("/drop-watch")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Drop Watch" in html

def test_screen_calibration_smoke(client):
    response = client.get("/calibration")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Calibration" in html
    assert "Agreement Rate" in html

def test_screen_detail_smoke():
    app = create_app({"DEMO": True, "TESTING": True})
    client = app.test_client()
    response = client.get("/detail/example-cloud.si")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "example-cloud.si" in html
    assert "Gate 6: Registrar Checkout Confirmation" in html

