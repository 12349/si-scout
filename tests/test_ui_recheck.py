import pytest
from unittest.mock import patch, MagicMock
from ui.recheck import perform_recheck_batch
from si_scout.rdap import RDAPStatus

def test_recheck_batch_limit():
    # Attempting to recheck 30 names should clamp or raise error
    domains = [f"domain{i}.si" for i in range(30)]
    with pytest.raises(ValueError, match="maximum of 25 names"):
        perform_recheck_batch(domains, max_allowed=25)

def test_recheck_batch_execution(tmp_path):
    domains = ["domain1.si", "domain2.si"]
    mock_rdap = MagicMock()
    mock_res = MagicMock()
    mock_res.status = RDAPStatus.AVAILABLE_CANDIDATE
    mock_res.checked_utc = "2026-09-30T19:00:00Z"
    mock_rdap.check_domain.return_value = mock_res

    results = perform_recheck_batch(domains, rdap_client=mock_rdap, max_allowed=25)
    assert len(results) == 2
    assert mock_rdap.check_domain.call_count == 2
    assert results[0]["domain"] == "domain1.si"
