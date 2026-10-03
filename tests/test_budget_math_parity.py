"""
Tests for deterministic budget math, carry costs, and probability calculations.
Verifies golden vectors, property boundaries, and parity.
"""
import pytest
from si_scout.budget_math import (
    calculate_carry_cost,
    calculate_budget_model,
    generate_sensitivity_matrix,
    generate_summary_sentence,
)


def test_golden_case_carry_cost_and_budget_math():
    """
    Hand-verified golden case:
    Budget: 200 EUR, First-year: 12.13 EUR, Renewal: 13.61 EUR, Term: 3 years.
    Carry cost: 12.13 + 2 * 13.61 = 39.35 EUR.
    Affordable: floor(200 / 39.35) = 5 names.
    Spend: 5 * 39.35 = 196.75 EUR.
    Leftover: 3.25 EUR.
    At 2.0% annual sell-through:
      total domain-years = 15
      p_zero = (0.98)^15 = 0.738569... -> 73.9%
      p_at_least_one = 1 - 0.738569... -> 26.1%
      expected sales = 15 * 0.02 = 0.30
      at 500 EUR net price:
        expected revenue = 150.00 EUR
        expected net = 150.00 - 196.75 = -46.75 EUR (loss)
        break-even sale price = 196.75 / 0.30 = 655.83 EUR
    """
    model = calculate_budget_model(
        budget=200.0,
        reserve_pct=0.0,
        first_year=12.13,
        renewal=13.61,
        tax_pct=0.0,
        term_years=3,
        domain_count=5,
        annual_sell_through_pct=2.0,
        net_sale_price=500.0,
        currency="EUR",
    )

    assert model["carry_cost"] == 39.35
    assert model["carry_cost_with_tax"] == 39.35
    assert model["max_affordable_domains"] == 5
    assert model["selected_domain_count"] == 5
    assert model["total_spend"] == 196.75
    assert model["leftover_budget"] == 3.25
    assert model["total_domain_years"] == 15
    assert model["p_zero_pct"] == 73.9
    assert model["p_at_least_one_pct"] == 26.1
    assert model["expected_sales"] == 0.30
    assert model["expected_revenue"] == 150.00
    assert model["expected_net"] == -46.75
    assert model["break_even_price"] == 655.83
    assert "73.9% chance of selling zero names" in model["summary_sentence"]
    assert "Illustrative arithmetic from your inputs, not a forecast" in model["disclaimer"]


def test_property_probability_bounds_and_monotonicity():
    """
    Ensures probabilities strictly reside within [0, 1] and satisfy monotonicity.
    """
    # 1. Monotonic in domain count
    probs_by_domains = []
    for count in range(1, 15):
        m = calculate_budget_model(
            budget=2000.0,
            reserve_pct=0.0,
            first_year=10.0,
            renewal=10.0,
            tax_pct=0.0,
            term_years=3,
            domain_count=count,
            annual_sell_through_pct=2.5,
            net_sale_price=300.0,
        )
        assert 0.0 <= m["p_zero"] <= 1.0
        assert 0.0 <= m["p_at_least_one"] <= 1.0
        assert pytest.approx(m["p_zero"] + m["p_at_least_one"], abs=1e-4) == 1.0
        probs_by_domains.append(m["p_at_least_one"])

    # Probability of >=1 sale strictly increases with number of names
    for i in range(len(probs_by_domains) - 1):
        assert probs_by_domains[i] < probs_by_domains[i + 1]

    # 2. Monotonic in term years
    probs_by_years = []
    for term in range(1, 6):
        m = calculate_budget_model(
            budget=2000.0,
            reserve_pct=0.0,
            first_year=10.0,
            renewal=10.0,
            tax_pct=0.0,
            term_years=term,
            domain_count=5,
            annual_sell_through_pct=3.0,
            net_sale_price=300.0,
        )
        probs_by_years.append(m["p_at_least_one"])

    for i in range(len(probs_by_years) - 1):
        assert probs_by_years[i] < probs_by_years[i + 1]


def test_budget_reserve_and_tax_handling():
    """
    Ensures reserve % and tax % deduct and scale accurately.
    """
    # Budget 1000, 20% reserve -> usable 800
    # First year 10, renewal 10, term 2 -> base carry = 20
    # Tax 20% -> carry with tax = 24.00
    # max domains = floor(800 / 24) = 33
    m = calculate_budget_model(
        budget=1000.0,
        reserve_pct=20.0,
        first_year=10.0,
        renewal=10.0,
        tax_pct=20.0,
        term_years=2,
        domain_count=33,
        annual_sell_through_pct=2.0,
        net_sale_price=400.0,
    )
    assert m["reserve_amount"] == 200.0
    assert m["usable_budget"] == 800.0
    assert m["carry_cost"] == 20.0
    assert m["carry_cost_with_tax"] == 24.0
    assert m["max_affordable_domains"] == 33
    assert m["total_spend"] == 33 * 24.0
    assert m["total_spend"] <= m["usable_budget"]


def test_sensitivity_matrix_structure():
    """
    Verifies sensitivity matrix dimensions and calculation consistency.
    """
    rates = [1.0, 2.0, 5.0]
    prices = [100.0, 500.0]
    mat = generate_sensitivity_matrix(
        domain_count=5,
        term_years=3,
        carry_cost_with_tax=39.35,
        sell_through_rates=rates,
        sale_prices=prices,
    )
    assert len(mat["matrix"]) == 3
    for row in mat["matrix"]:
        assert len(row["cells"]) == 2
        for cell in row["cells"]:
            # spend is 5 * 39.35 = 196.75
            expected_sales = 5 * 3 * (cell["rate"] / 100.0)
            expected_net = round(expected_sales * cell["price"] - 196.75, 2)
            assert cell["net"] == expected_net
            if expected_net > 0:
                assert cell["status"] == "gain"
            elif expected_net < 0:
                assert cell["status"] == "loss"
            else:
                assert cell["status"] == "even"
