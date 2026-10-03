"""
Tests for newly added interactive routes in demo mode.
Validates zero network socket calls, status 200 responses,
fixed timestamp banner presence, and anti-forecast disclaimers.
"""
import socket
import pytest
from flask import Flask

from ui.app import create_app


@pytest.fixture
def demo_app():
    app = create_app({"TESTING": True, "DEMO": True})
    return app


@pytest.fixture
def demo_client(demo_app: Flask):
    return demo_app.test_client()


def test_new_interactive_routes_render_in_demo(demo_client, monkeypatch):
    """
    Ensures every new screen renders successfully with status 200 in offline demo mode.
    Guarantees zero network calls by poisoning socket.connect.
    """
    def forbidden_connect(*args, **kwargs):
        raise RuntimeError("NETWORK CALL ATTEMPTED! Sockets are forbidden.")
    monkeypatch.setattr(socket.socket, "connect", forbidden_connect)

    routes = [
        "/",
        "/budget",
        "/name-lab",
        "/funnel",
        "/gates",
        "/story",
    ]

    for route in routes:
        resp = demo_client.get(route)
        assert resp.status_code == 200, f"Route {route} failed with status {resp.status_code}"
        html = resp.get_data(as_text=True)

        # Permanent disclaimer footer
        assert "Screening score, not a value estimate. No purchase is ever made by this tool." in html

        # Demo banner
        assert "Demo data. Not real registry results." in html
        assert "Demo data timestamps are fixed" in html


def test_budget_api_endpoint(demo_client):
    payload = {
        "budget": 200,
        "reserve_pct": 0,
        "first_year": 12.13,
        "renewal": 13.61,
        "tax_pct": 0,
        "term_years": 3,
        "domain_count": 5,
        "annual_sell_through_pct": 2.0,
        "net_sale_price": 500,
        "currency": "EUR",
    }
    resp = demo_client.post("/api/budget/calculate", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["carry_cost"] == 39.35
    assert data["total_spend"] == 196.75
    assert data["p_zero_pct"] == 73.9
    assert data["p_at_least_one_pct"] == 26.1
    assert "Illustrative arithmetic from your inputs, not a forecast" in data["disclaimer"]


def test_name_lab_api_endpoint(demo_client):
    resp = demo_client.post("/api/name-lab/screen", json={"label": "example-cloud"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["label"] == "example-cloud"
    assert data["is_valid_syntax"] is True
    assert "Not checked against the registry" in data["disclaimer"]


def test_funnel_api_endpoint(demo_client):
    resp = demo_client.get("/api/funnel/data")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "stages" in data
    assert "source_file" in data
    assert "snapshot_date" in data
