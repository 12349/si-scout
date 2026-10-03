import pytest
from unittest.mock import patch, MagicMock
from si_scout.rdap import RDAPClient, RDAPStatus

def test_sqlite_cache_resume(tmp_path):
    db_path = tmp_path / "resume_test.db"
    
    # First instance runs 2 domains
    client1 = RDAPClient(db_path=db_path, min_interval_seconds=0.0)
    
    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {"ldhName": "test1.si", "status": ["active"]}

    mock_resp_404 = MagicMock()
    mock_resp_404.status_code = 404
    mock_resp_404.json.return_value = {}

    with patch("requests.get", side_effect=[mock_resp_200, mock_resp_404]) as mock_get:
        r1 = client1.check_domain("test1.si")
        r2 = client1.check_domain("test2.si")
        assert mock_get.call_count == 2
        assert r1.status == RDAPStatus.REGISTERED
        assert r2.status == RDAPStatus.AVAILABLE_CANDIDATE

    # Second instance starts up and re-checks the same domains (simulating restart/resume)
    client2 = RDAPClient(db_path=db_path, min_interval_seconds=0.0)
    with patch("requests.get") as mock_get_resumed:
        # These should hit SQLite cache, network call count must be ZERO
        r1_cached = client2.check_domain("test1.si")
        r2_cached = client2.check_domain("test2.si")
        
        assert mock_get_resumed.call_count == 0
        assert r1_cached.status == RDAPStatus.REGISTERED
        assert r2_cached.status == RDAPStatus.AVAILABLE_CANDIDATE
        assert r1_cached.checked_utc == r1.checked_utc
