import pytest
from unittest.mock import patch, MagicMock
import requests
from si_scout.rdap import RDAPClient, RDAPStatus

def test_rdap_200_registered(tmp_path):
    db_path = tmp_path / "test_rdap.db"
    client = RDAPClient(db_path=db_path, min_interval_seconds=0.0)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "ldhName": "register.si",
        "status": ["server delete prohibited", "server transfer prohibited"]
    }

    with patch("requests.get", return_value=mock_resp):
        res = client.check_domain("register.si")
        assert res.status == RDAPStatus.REGISTERED
        assert res.http_status_code == 200
        assert "server delete prohibited" in res.raw_statuses

def test_rdap_200_quarantine_pending_delete(tmp_path):
    db_path = tmp_path / "test_rdap.db"
    client = RDAPClient(db_path=db_path, min_interval_seconds=0.0)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "ldhName": "expiring.si",
        "status": ["pendingDelete", "quarantine"]
    }

    with patch("requests.get", return_value=mock_resp):
        res = client.check_domain("expiring.si")
        assert res.status == RDAPStatus.QUARANTINE_PENDING_DELETE
        assert res.http_status_code == 200

def test_rdap_404_available_candidate(tmp_path):
    db_path = tmp_path / "test_rdap.db"
    client = RDAPClient(db_path=db_path, min_interval_seconds=0.0)

    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.json.return_value = {"errorCode": 404, "title": "Not Found"}

    with patch("requests.get", return_value=mock_resp):
        res = client.check_domain("nonexistent-brand-xyz.si")
        assert res.status == RDAPStatus.AVAILABLE_CANDIDATE
        assert res.http_status_code == 404

def test_rdap_429_backoff_then_200(tmp_path):
    db_path = tmp_path / "test_rdap.db"
    client = RDAPClient(db_path=db_path, min_interval_seconds=0.0, max_retries=2, initial_backoff=0.01)

    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {"ldhName": "slowdown.si", "status": ["active"]}

    with patch("requests.get", side_effect=[mock_resp_429, mock_resp_200]):
        res = client.check_domain("slowdown.si")
        assert res.status == RDAPStatus.REGISTERED
        assert res.http_status_code == 200

def test_rdap_500_server_error(tmp_path):
    db_path = tmp_path / "test_rdap.db"
    client = RDAPClient(db_path=db_path, min_interval_seconds=0.0, max_retries=1, initial_backoff=0.01)

    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch("requests.get", return_value=mock_resp):
        res = client.check_domain("error500.si")
        assert res.status == RDAPStatus.UNCERTAIN
        assert res.http_status_code == 500

def test_rdap_timeout(tmp_path):
    db_path = tmp_path / "test_rdap.db"
    client = RDAPClient(db_path=db_path, min_interval_seconds=0.0, max_retries=1, initial_backoff=0.01)

    with patch("requests.get", side_effect=requests.exceptions.Timeout("Connection timeout")):
        res = client.check_domain("timeout.si")
        assert res.status == RDAPStatus.UNCERTAIN
        assert "timeout" in res.notes.lower()

def test_rdap_malformed_json(tmp_path):
    db_path = tmp_path / "test_rdap.db"
    client = RDAPClient(db_path=db_path, min_interval_seconds=0.0)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("Invalid JSON")
    mock_resp.text = "<html>Error</html>"

    with patch("requests.get", return_value=mock_resp):
        res = client.check_domain("malformed.si")
        assert res.status == RDAPStatus.UNCERTAIN
        assert "malformed" in res.notes.lower()

def test_rdap_404_never_quarantine(tmp_path):
    """Regression test: HTTP 404 on arbitrary domain must never produce QUARANTINE."""
    db_path = tmp_path / "test_rdap.db"
    client = RDAPClient(db_path=db_path, min_interval_seconds=0.0)

    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.json.return_value = {"errorCode": 404, "title": "Domain 'example-candidate-404.si' not found"}

    with patch("requests.get", return_value=mock_resp):
        res = client.check_domain("example-candidate-404.si")
        assert res.status == RDAPStatus.AVAILABLE_CANDIDATE
        assert res.status != RDAPStatus.QUARANTINE_PENDING_DELETE
        assert res.http_status_code == 404

def test_rdap_register_si_pending_delete_space(tmp_path):
    """Regression test: Register.si status ['pending delete'] with space maps to QUARANTINE_PENDING_DELETE."""
    db_path = tmp_path / "test_rdap.db"
    client = RDAPClient(db_path=db_path, min_interval_seconds=0.0)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "ldhName": "example-quarantine-pending.si",
        "status": ["pending delete"],
        "events": [
            {"eventAction": "registration", "eventDate": "2025-09-29T10:27:06Z"},
            {"eventAction": "expiration", "eventDate": "2026-09-29T10:27:06Z"}
        ]
    }

    with patch("requests.get", return_value=mock_resp):
        res = client.check_domain("example-quarantine-pending.si")
        assert res.status == RDAPStatus.QUARANTINE_PENDING_DELETE
        assert res.http_status_code == 200
        assert "pending delete" in res.raw_statuses


