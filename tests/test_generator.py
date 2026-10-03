import pytest
from si_scout.generate import DomainGenerator

def test_generator_deduplication():
    generator = DomainGenerator()
    candidates = generator.generate(extra_names=["agent", "AGENT", "Agent", "customname"])
    
    labels = [c.label for c in candidates]
    # Check that all are lowercase and unique
    assert len(labels) == len(set(labels))
    assert "agent" in labels
    assert "customname" in labels

def test_generator_categories_coverage():
    generator = DomainGenerator()
    candidates = generator.generate(max_count=200)
    
    assert len(candidates) > 50
    # Every generated candidate must pass label validation
    for c in candidates:
        assert 2 <= len(c.label) <= 63
        assert not c.label.startswith("-")
        assert not c.label.endswith("-")
        assert not (len(c.label) >= 4 and c.label[2] == '-' and c.label[3] == '-')

def test_generator_si_theming():
    generator = DomainGenerator()
    candidates = generator.generate(extra_names=["superintelligence"])
    labels = {c.label for c in candidates}
    
    # Check that SI prefixes and suffixes are represented
    si_present = any(l.startswith("si") or l.endswith("si") or "agent" in l for l in labels)
    assert si_present
