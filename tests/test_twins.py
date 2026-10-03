import pytest
from unittest.mock import patch, MagicMock
from si_scout.twins import TwinAnalyzer, TwinStatus

def test_twin_unregistered(tmp_path):
    db_path = tmp_path / "twins_test.db"
    analyzer = TwinAnalyzer(db_path=db_path)

    with patch("socket.gethostbyname", side_effect=OSError("Name or service not known")):
        status, details = analyzer.check_twin("definitelynonexistent123.com")
        assert status == TwinStatus.UNREGISTERED

def test_twin_parked(tmp_path):
    db_path = tmp_path / "twins_test.db"
    analyzer = TwinAnalyzer(db_path=db_path)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><title>This domain is for sale - Buy it now</title><body>Dan.com parking</body></html>"

    with patch("socket.gethostbyname", return_value="1.2.3.4"):
        with patch("requests.get", return_value=mock_resp):
            status, details = analyzer.check_twin("parkeddomain.com")
            assert status == TwinStatus.PARKED_OR_FOR_SALE

def test_twin_active_site(tmp_path):
    db_path = tmp_path / "twins_test.db"
    analyzer = TwinAnalyzer(db_path=db_path)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><title>Autonomous Systems Inc</title><body>Next-generation intelligent agent infrastructure</body></html>"

    with patch("socket.gethostbyname", return_value="1.2.3.4"):
        with patch("requests.get", return_value=mock_resp):
            status, details = analyzer.check_twin("activeai.com")
            assert status == TwinStatus.ACTIVE_SITE
