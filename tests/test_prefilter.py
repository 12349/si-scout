import pytest
from si_scout.prefilter import DomainPreFilter
from si_scout.config import load_blocklist, load_reserved_domains

@pytest.fixture
def prefilter():
    blocklist = load_blocklist()
    reserved = load_reserved_domains()
    return DomainPreFilter(blocklist=blocklist, reserved_domains=reserved)

def test_hard_block_brands(prefilter):
    # Brand collision
    passed, reason, _ = prefilter.evaluate("google")
    assert not passed
    assert "trademark" in reason.lower()

    # Substring brand collision
    passed, reason, _ = prefilter.evaluate("openairesearch")
    assert not passed
    assert "trademark" in reason.lower()

    # Public figure
    passed, reason, _ = prefilter.evaluate("donaldtrump")
    assert not passed
    assert "trademark" in reason.lower()

def test_hard_block_reserved(prefilter):
    # Official Register.si reserved names
    passed, reason, _ = prefilter.evaluate("112")
    assert not passed
    assert "reserved" in reason.lower()

    passed, reason, _ = prefilter.evaluate("rs")
    assert not passed
    assert "reserved" in reason.lower()

def test_penalize_awkward_consonants(prefilter):
    # "bcdfgh" has an awkward 6-consonant cluster
    passed, reason, score = prefilter.evaluate("bcdfgh")
    assert score < 30

def test_reward_common_compound(prefilter):
    # "mindagent" or "neurocore"
    passed, reason, score = prefilter.evaluate("mindagent")
    assert passed
    assert score >= 60

def test_length_penalty(prefilter):
    # Length > 10 should receive a lower shape score than short 5-6 char words
    _, _, score_short = prefilter.evaluate("agent")
    _, _, score_long = prefilter.evaluate("supercomputingintelligence")
    assert score_short > score_long
