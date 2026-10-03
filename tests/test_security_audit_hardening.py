import socket
from unittest.mock import patch, MagicMock
import pytest
from flask import Flask

from si_scout.twins import TwinAnalyzer, TwinStatus
from si_scout.rdap import RDAPClient, RDAPStatus
from ui.app import create_app

def test_ssrf_protection_private_ip(tmp_path):
    analyzer = TwinAnalyzer(db_path=tmp_path / "test.db")
    with patch("socket.gethostbyname", return_value="127.0.0.1"):
        status, details = analyzer.check_twin("test-loopback.com")
        assert status == TwinStatus.UNKNOWN
        assert "non-public/private IP" in details

    with patch("socket.gethostbyname", return_value="10.100.0.1"):
        status, details = analyzer.check_twin("test-private.com")
        assert status == TwinStatus.UNKNOWN
        assert "non-public/private IP" in details

def test_twin_analyzer_disables_redirects(tmp_path):
    analyzer = TwinAnalyzer(db_path=tmp_path / "test.db")
    mock_resp = MagicMock()
    mock_resp.status_code = 302
    mock_resp.headers = {"Location": "http://127.0.0.1:8501/api/scan/start"}
    mock_resp.text = ""

    with patch("socket.gethostbyname", return_value="93.184.216.34"): # example.com public IP
        with patch("requests.get", return_value=mock_resp) as mock_get:
            status, details = analyzer.check_twin("test-redirect.com")
            assert status == TwinStatus.ACTIVE_SITE
            assert "302" in details
            # Verify allow_redirects=False was passed to prevent SSRF redirect chasing
            assert mock_get.call_args[1]["allow_redirects"] is False

def test_rdap_client_rejects_invalid_syntax_and_tld(tmp_path):
    client = RDAPClient(db_path=tmp_path / "test.db")
    with patch("requests.get") as mock_get:
        # Invalid characters / path traversal attempt
        res = client.check_domain("../../traversal.si")
        assert res.status == RDAPStatus.UNCERTAIN
        assert res.http_status_code == 400
        assert "Invalid .si domain syntax" in res.notes
        mock_get.assert_not_called()

        # Non-.si TLD
        res2 = client.check_domain("validname.com")
        assert res2.status == RDAPStatus.UNCERTAIN
        assert res2.http_status_code == 400
        assert "Non-.si TLD rejected" in res2.notes
        mock_get.assert_not_called()

def test_csrf_origin_rejection():
    app = create_app({"TESTING": True, "DEMO": True})
    client = app.test_client()

    # Cross-origin request rejected
    resp = client.post(
        "/api/shortlist/toggle",
        headers={"Origin": "https://malicious-website.com"},
        json={"domain": "agent.si"}
    )
    assert resp.status_code == 403
    data = resp.get_json()
    assert "Cross-origin request rejected" in data["error"]

    # Same-origin request permitted
    resp_ok = client.post(
        "/api/shortlist/toggle",
        headers={"Origin": "http://127.0.0.1:8501"},
        json={"domain": "agent.si"}
    )
    assert resp_ok.status_code == 200

def test_security_headers_present():
    app = create_app({"TESTING": True, "DEMO": True})
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert "default-src 'self'" in resp.headers.get("Content-Security-Policy", "")

def test_scan_api_extra_names_validation():
    app = create_app({"TESTING": True, "DEMO": False})
    client = app.test_client()
    # Malicious/invalid extra argument format rejected
    resp = client.post(
        "/api/scan/start",
        headers={"Origin": "http://127.0.0.1:8501"},
        json={"top": 10, "extra": "invalid;command&injection"}
    )
    assert resp.status_code == 400
    assert "Invalid characters in extra names" in resp.get_json()["error"]
