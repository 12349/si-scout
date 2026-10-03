"""
Offline Name Lab screener tests: validates label rules, brand blocklist,
and scoring heuristics without any network socket calls.
"""
import pytest
import socket
from si_scout.name_lab import screen_label_offline


def test_name_lab_valid_label_breakdown(monkeypatch):
    # Ensure zero network calls occur by poisoning socket connect
    def forbidden_connect(*args, **kwargs):
        raise RuntimeError("Network call attempted during offline Name Lab test!")
    monkeypatch.setattr(socket.socket, "connect", forbidden_connect)

    result = screen_label_offline("mindagent")
    assert result["label"] == "mindagent"
    assert result["is_valid_syntax"] is True
    assert result["is_blocked"] is False
    assert result["score"] >= 60.0
    assert "Not checked against the registry" in result["disclaimer"]
    assert "Availability must be confirmed at a registrar" in result["disclaimer"]


def test_name_lab_invalid_syntax_hyphen_rules():
    res1 = screen_label_offline("-invalid")
    assert res1["is_valid_syntax"] is False
    assert "hyphen" in res1["syntax_reason"].lower()

    res2 = screen_label_offline("invalid-")
    assert res2["is_valid_syntax"] is False

    res3 = screen_label_offline("in--valid")
    assert res3["is_valid_syntax"] is False

    res4 = screen_label_offline("a")  # Too short (min 2)
    assert res4["is_valid_syntax"] is False


def test_name_lab_brand_blocked():
    res = screen_label_offline("google")
    assert res["is_blocked"] is True
    assert res["score"] == 0.0
    assert "trademark" in res["block_reason"].lower() or "blocked" in res["block_reason"].lower()


def test_name_lab_reserved_domain():
    res = screen_label_offline("112")
    assert res["is_blocked"] is True
    assert res["is_reserved"] is True
    assert res["score"] == 0.0
    assert "reserved" in res["block_reason"].lower()
