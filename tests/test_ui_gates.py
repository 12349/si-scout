import pytest
from datetime import datetime, timezone
from ui.gates import validate_human_rationale, check_buy_readiness

def test_rationale_word_count_requirement():
    # Less than 15 words
    short_text = "This is a short rationale that should be rejected by the tool."
    is_valid, msg = validate_human_rationale(short_text, verified_checkbox=True, author="human")
    assert not is_valid
    assert "at least 15 words" in msg.lower()

    # Exactly 15 words with checkbox and author: human
    valid_text = "A machine learning silicon accelerator startup would readily pay five hundred dollars for this clean domain."
    assert len(valid_text.split()) >= 15
    is_valid, msg = validate_human_rationale(valid_text, verified_checkbox=True, author="human")
    assert is_valid

def test_rationale_missing_checkbox():
    valid_text = "A machine learning silicon accelerator startup would readily pay five hundred dollars for this clean domain."
    is_valid, msg = validate_human_rationale(valid_text, verified_checkbox=False, author="human")
    assert not is_valid
    assert "source unknown" in msg.lower()

def test_legacy_rationale_flagged_source_unknown():
    legacy_entry = "A company would pay $500" # String format or missing author='human'
    is_valid, msg = validate_human_rationale(legacy_entry, verified_checkbox=True, author="legacy")
    assert not is_valid
    assert "source unknown" in msg.lower()

def test_regression_entry_without_human_tag_cannot_produce_buy_candidate():
    """Phase A Step 3 Regression Test: UI Path."""
    # 1. Plain string entry without dict
    is_valid, msg = validate_human_rationale("Plain string without author or metadata tags here that is long enough.")
    assert not is_valid
    assert "source unknown" in msg.lower()

    # 2. Dict with author="agent" (e.g. LLM generated)
    agent_dict = {
        "rationale": "A machine learning silicon accelerator startup would readily pay five hundred dollars for this clean domain.",
        "author": "agent",
        "self_written": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    is_valid, msg = validate_human_rationale(agent_dict)
    assert not is_valid
    assert "source unknown" in msg.lower()

    # 3. Dict with self_written=False
    unverified_dict = {
        "rationale": "A machine learning silicon accelerator startup would readily pay five hundred dollars for this clean domain.",
        "author": "human",
        "self_written": False,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    is_valid, msg = validate_human_rationale(unverified_dict)
    assert not is_valid
    assert "source unknown" in msg.lower()

    # 4. Dict missing timestamp
    no_ts_dict = {
        "rationale": "A machine learning silicon accelerator startup would readily pay five hundred dollars for this clean domain.",
        "author": "human",
        "self_written": True
    }
    is_valid, msg = validate_human_rationale(no_ts_dict)
    assert not is_valid
    assert "source unknown" in msg.lower()

    # 5. Gate readiness must strictly block BUY readiness
    readiness = check_buy_readiness(
        rdap_status="AVAILABLE_CANDIDATE",
        is_price_stale=False,
        is_scan_stale=False,
        is_check_stale=False,
        has_trademark_flag=False,
        human_rationale_valid=is_valid, # False
        within_budget=True,
        registrar_confirmation={"author": "human", "registrar": "Dynadot", "checked_utc": "2026-10-01T20:00:00Z", "result": "available"}
    )
    assert readiness["is_ready"] is False
    assert any("rationale" in r.lower() for r in readiness["blocking_reasons"])

def test_check_buy_readiness_all_pass():
    valid_conf = {
        "author": "human",
        "registrar": "Dynadot",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "result": "available"
    }
    res = check_buy_readiness(
        rdap_status="AVAILABLE_CANDIDATE",
        is_price_stale=False,
        is_scan_stale=False,
        is_check_stale=False,
        has_trademark_flag=False,
        human_rationale_valid=True,
        within_budget=True,
        registrar_confirmation=valid_conf,
        check_age_minutes=15.0
    )
    assert res["is_ready"] is True
    assert len(res["blocking_reasons"]) == 0
    assert res["gates"]["registrar_confirmed"] is True

def test_check_buy_readiness_fails_if_stale_or_missing_rationale():
    res = check_buy_readiness(
        rdap_status="AVAILABLE_CANDIDATE",
        is_price_stale=True,
        is_scan_stale=False,
        is_check_stale=False,
        has_trademark_flag=False,
        human_rationale_valid=False,
        within_budget=True
    )
    assert res["is_ready"] is False
    assert len(res["blocking_reasons"]) >= 2

def test_gate_6_validation_and_registry_busy():
    from ui.gates import validate_registrar_confirmation
    now_ts = datetime.now(timezone.utc).isoformat()

    # Missing author or bot author
    pass_bot, msg = validate_registrar_confirmation({
        "author": "bot",
        "registrar": "Hostinger",
        "checked_utc": now_ts,
        "result": "available"
    })
    assert pass_bot is False
    assert "human" in msg.lower()

    # Taken or already taken
    pass_taken, msg_taken = validate_registrar_confirmation({
        "author": "human",
        "registrar": "Hostinger",
        "checked_utc": now_ts,
        "result": "already taken"
    })
    assert pass_taken is False
    assert "already taken" in msg_taken

    # Registry busy / could not confirm: strictly fails Gate 6
    pass_busy, msg_busy = validate_registrar_confirmation({
        "author": "human",
        "registrar": "Hostinger",
        "checked_utc": now_ts,
        "result": "registry busy / could not confirm"
    })
    assert pass_busy is False
    assert "registry busy / could not confirm" in msg_busy.lower()
    assert "retries allowed" in msg_busy.lower()

    # Valid human available confirmation passes
    pass_avail, msg_avail = validate_registrar_confirmation({
        "author": "human",
        "registrar": "Hostinger",
        "checked_utc": now_ts,
        "result": "available"
    })
    assert pass_avail is True
    assert "confirmed available" in msg_avail.lower()

    # Confirm that 'registry busy / could not confirm' can NEVER pass check_buy_readiness
    res_busy = check_buy_readiness(
        rdap_status="AVAILABLE_CANDIDATE",
        is_price_stale=False,
        is_scan_stale=False,
        is_check_stale=False,
        has_trademark_flag=False,
        human_rationale_valid=True,
        within_budget=True,
        registrar_confirmation={
            "author": "human",
            "registrar": "Hostinger",
            "checked_utc": now_ts,
            "result": "registry busy / could not confirm"
        }
    )
    assert res_busy["is_ready"] is False
    assert res_busy["gates"]["registrar_confirmed"] is False
    assert any("registry busy / could not confirm" in r.lower() for r in res_busy["blocking_reasons"])


def test_freshness_60_minute_rule_in_gates():
    valid_conf = {
        "author": "human",
        "registrar": "Hostinger",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "result": "available"
    }
    # Check is older than 60 minutes
    res_stale = check_buy_readiness(
        rdap_status="AVAILABLE_CANDIDATE",
        is_price_stale=False,
        is_scan_stale=False,
        is_check_stale=True,
        has_trademark_flag=False,
        human_rationale_valid=True,
        within_budget=True,
        registrar_confirmation=valid_conf,
        check_age_minutes=85.0
    )
    assert res_stale["is_ready"] is False
    assert any("60 minutes" in b for b in res_stale["blocking_reasons"])
    assert any("85 min old" in b for b in res_stale["blocking_reasons"])


def test_registrar_confirmation_60_minute_expiration_window():
    """
    Tests that a registrar confirmation expires 60 minutes after its attempt time.
    Tests just-inside (e.g. 59 minutes elapsed) and just-outside (e.g. 61 minutes elapsed).
    Proves that outside the window, Gate 6 strictly fails with:
    'Confirmation expired: re-confirm at checkout.'
    """
    from datetime import datetime, timezone, timedelta
    from ui.gates import validate_registrar_confirmation, get_registrar_confirmation_remaining_minutes, check_buy_readiness

    base_time = datetime(2026, 10, 1, 20, 0, 0, tzinfo=timezone.utc)
    attempt_time_iso = base_time.isoformat()

    valid_conf = {
        "author": "human",
        "registrar": "Hostinger",
        "checked_utc": attempt_time_iso,
        "result": "available",
        "notes": "manual checkout cart test"
    }

    # 1. Just-inside the window (59.0 minutes after attempt) -> PASS
    time_just_inside = base_time + timedelta(minutes=59)
    passed_inside, msg_inside = validate_registrar_confirmation(valid_conf, now_utc=time_just_inside)
    assert passed_inside is True
    assert "confirmed available" in msg_inside.lower()

    rem_inside = get_registrar_confirmation_remaining_minutes(valid_conf, now_utc=time_just_inside)
    assert rem_inside == 1.0

    readiness_inside = check_buy_readiness(
        rdap_status="AVAILABLE_CANDIDATE",
        is_price_stale=False,
        is_scan_stale=False,
        is_check_stale=False,
        has_trademark_flag=False,
        human_rationale_valid=True,
        within_budget=True,
        registrar_confirmation=valid_conf,
        now_utc=time_just_inside
    )
    assert readiness_inside["is_ready"] is True
    assert readiness_inside["gates"]["registrar_confirmed"] is True

    # 2. At boundary (59.9 minutes after attempt) -> PASS
    time_boundary = base_time + timedelta(minutes=59, seconds=54)
    passed_boundary, _ = validate_registrar_confirmation(valid_conf, now_utc=time_boundary)
    assert passed_boundary is True

    # 3. Just-outside the window (60.1 minutes after attempt) -> FAIL with exact message
    time_just_outside_sub = base_time + timedelta(minutes=60, seconds=6)
    passed_outside_sub, msg_outside_sub = validate_registrar_confirmation(valid_conf, now_utc=time_just_outside_sub)
    assert passed_outside_sub is False
    assert msg_outside_sub == "Confirmation expired: re-confirm at checkout."

    # 4. Just-outside the window (61.0 minutes after attempt) -> FAIL with exact message
    time_just_outside = base_time + timedelta(minutes=61)
    passed_outside, msg_outside = validate_registrar_confirmation(valid_conf, now_utc=time_just_outside)
    assert passed_outside is False
    assert msg_outside == "Confirmation expired: re-confirm at checkout."

    rem_outside = get_registrar_confirmation_remaining_minutes(valid_conf, now_utc=time_just_outside)
    assert rem_outside is not None and rem_outside < 0

    readiness_outside = check_buy_readiness(
        rdap_status="AVAILABLE_CANDIDATE",
        is_price_stale=False,
        is_scan_stale=False,
        is_check_stale=False,
        has_trademark_flag=False,
        human_rationale_valid=True,
        within_budget=True,
        registrar_confirmation=valid_conf,
        now_utc=time_just_outside
    )
    assert readiness_outside["is_ready"] is False
    assert readiness_outside["gates"]["registrar_confirmed"] is False
    assert "Confirmation expired: re-confirm at checkout." in readiness_outside["blocking_reasons"]

    # 5. Non-UTC / UNKNOWN attempt timestamp must fail
    conf_unknown = {
        "author": "human",
        "registrar": "Hostinger",
        "checked_utc": "UNKNOWN",
        "result": "available"
    }
    pass_unknown, msg_unknown = validate_registrar_confirmation(conf_unknown, now_utc=time_just_inside)
    assert pass_unknown is False
    assert "cannot be unknown" in msg_unknown.lower()

