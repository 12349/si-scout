import pytest
import time
from unittest.mock import patch, MagicMock
from si_scout.rdap import RDAPClient

def test_rate_limiter_spacing(tmp_path):
    db_path = tmp_path / "rate_limit_test.db"
    # min_interval = 0.5s for fast test, verifying delta >= min_interval
    min_interval = 0.25
    client = RDAPClient(db_path=db_path, min_interval_seconds=min_interval)

    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.json.return_value = {}

    timestamps = []

    def mock_get(*args, **kwargs):
        timestamps.append(time.perf_counter())
        return mock_resp

    with patch("requests.get", side_effect=mock_get):
        client.check_domain("name1.si")
        client.check_domain("name2.si")
        client.check_domain("name3.si")

    assert len(timestamps) == 3
    # Check that time between consecutive requests is at least min_interval (with small margin for clock resolution)
    diff1 = timestamps[1] - timestamps[0]
    diff2 = timestamps[2] - timestamps[1]
    assert diff1 >= min_interval - 0.05
    assert diff2 >= min_interval - 0.05
