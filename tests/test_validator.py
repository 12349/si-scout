import pytest
from si_scout.validator import validate_si_label

def test_valid_labels():
    valid_samples = [
        "ai",
        "agent",
        "superintelligence",
        "deep-mind",
        "neuro-core",
        "a16z",
        "cog-7",
        "a" * 63
    ]
    for label in valid_samples:
        is_valid, reason = validate_si_label(label)
        assert is_valid, f"Expected '{label}' to be valid, but got reason: {reason}"

def test_invalid_length():
    is_valid, reason = validate_si_label("a")
    assert not is_valid
    assert "length" in reason.lower()

    is_valid, reason = validate_si_label("a" * 64)
    assert not is_valid
    assert "length" in reason.lower()

def test_hyphen_rules():
    # Leading hyphen
    assert not validate_si_label("-agent")[0]
    # Trailing hyphen
    assert not validate_si_label("agent-")[0]
    # Hyphens at position 3 and 4 (e.g. index 2 and 3: 'ab--cd' where pos 3 and 4 are hyphens)
    assert not validate_si_label("ab--cd")[0]
    # Valid hyphen inside
    assert validate_si_label("ab-cd")[0]
    assert validate_si_label("a-b")[0]

def test_disallowed_characters():
    assert not validate_si_label("agent_core")[0] # Underscore not allowed in labels
    assert not validate_si_label("ai.core")[0]    # Dot inside label
    assert not validate_si_label("ai core")[0]    # Space
    assert not validate_si_label("ai!core")[0]    # Special character
