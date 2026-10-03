import pytest
from si_scout.config import load_registrars
from si_scout.pricing import PricingEngine

def test_cheapest_non_stale_registrar():
    registrars = load_registrars()
    engine = PricingEngine(registrars=registrars)

    summary = engine.get_pricing_summary("agent.si")
    assert summary["cheapest_registrar"] is not None
    assert summary["cheapest_registrar"]["is_stale"] is False
    assert "confirm premium" in summary["disclaimer"].lower()
    assert "{domain}" not in summary["buy_link"]
    assert "agent.si" in summary["buy_link"]

def test_aftermarket_links():
    engine = PricingEngine()
    links = engine.get_aftermarket_links("mind.si")
    assert "sedo" in links
    assert "afternic" in links
    assert "mind.si" in links["sedo"]
    assert "mind.si" in links["afternic"]
