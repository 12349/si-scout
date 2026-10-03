"""
Deterministic budget, carry cost, and sell-through probability calculator.

NON-NEGOTIABLE POLICY:
This module performs arithmetic calculations based on user-provided inputs.
It is NOT a forecast, prediction, or valuation model.
"""
from typing import Dict, Any, List
import math


def calculate_carry_cost(first_year: float, renewal: float, term_years: int) -> float:
    """
    Computes holding cost for a single domain over the given term.
    carry_cost = first_year + (term_years - 1) * renewal
    """
    if term_years < 1:
        term_years = 1
    cost = first_year + (term_years - 1) * renewal
    return round(cost, 2)


def calculate_budget_model(
    budget: float = 200.0,
    reserve_pct: float = 0.0,
    first_year: float = 12.13,
    renewal: float = 13.61,
    tax_pct: float = 0.0,
    term_years: int = 3,
    domain_count: int = 5,
    annual_sell_through_pct: float = 2.0,
    net_sale_price: float = 500.0,
    currency: str = "EUR",
    exchange_rate: float = 1.0,
) -> Dict[str, Any]:
    """
    Evaluates budget allocation, carry spend, and binomial sales probability.
    """
    if budget < 0:
        budget = 0.0
    reserve_pct = max(0.0, min(90.0, reserve_pct))
    tax_pct = max(0.0, min(100.0, tax_pct))
    term_years = max(1, min(10, int(term_years)))
    annual_sell_through_pct = max(0.0, min(100.0, annual_sell_through_pct))
    net_sale_price = max(0.0, net_sale_price)

    # 1. Carry cost
    base_carry_cost = calculate_carry_cost(first_year, renewal, term_years)
    tax_multiplier = 1.0 + (tax_pct / 100.0)
    carry_cost_with_tax = round(base_carry_cost * tax_multiplier, 2)

    # 2. Reserve & Usable Budget
    reserve_amount = round(budget * (reserve_pct / 100.0), 2)
    usable_budget = max(0.0, round(budget - reserve_amount, 2))

    # 3. Max affordable domains
    if carry_cost_with_tax > 0:
        max_affordable_domains = int(usable_budget // carry_cost_with_tax)
    else:
        max_affordable_domains = 0

    # User domain count clamped by affordability
    selected_domain_count = max(0, min(int(domain_count), max_affordable_domains))

    # 4. Total Spend and Leftover
    total_spend = round(selected_domain_count * carry_cost_with_tax, 2)
    leftover_budget = round(usable_budget - total_spend, 2)

    # 5. Probabilities (Binomial independent domain-years)
    p_annual = annual_sell_through_pct / 100.0
    total_domain_years = selected_domain_count * term_years

    if total_domain_years == 0 or p_annual <= 0.0:
        p_zero = 1.0
        p_at_least_one = 0.0
        expected_sales = 0.0
    elif p_annual >= 1.0:
        p_zero = 0.0
        p_at_least_one = 1.0
        expected_sales = float(total_domain_years)
    else:
        p_zero = (1.0 - p_annual) ** total_domain_years
        p_at_least_one = 1.0 - p_zero
        expected_sales = total_domain_years * p_annual

    p_zero_pct = round(p_zero * 100.0, 1)
    p_at_least_one_pct = round(p_at_least_one * 100.0, 1)
    expected_sales_rounded = round(expected_sales, 2)

    # 6. Financial Expected Value & Break-Even
    expected_revenue = round(expected_sales * net_sale_price, 2)
    expected_net = round(expected_revenue - total_spend, 2)

    if expected_sales > 0:
        break_even_price = round(total_spend / expected_sales, 2)
    else:
        break_even_price = None

    # 7. Plain-language headline sentence
    summary_sentence = generate_summary_sentence(
        domain_count=selected_domain_count,
        term_years=term_years,
        annual_sell_through_pct=annual_sell_through_pct,
        p_zero_pct=p_zero_pct,
        p_at_least_one_pct=p_at_least_one_pct,
        expected_net=expected_net,
        currency=currency,
    )

    return {
        "budget": budget,
        "reserve_pct": reserve_pct,
        "reserve_amount": reserve_amount,
        "usable_budget": usable_budget,
        "tax_pct": tax_pct,
        "first_year": first_year,
        "renewal": renewal,
        "term_years": term_years,
        "carry_cost": base_carry_cost,
        "carry_cost_with_tax": carry_cost_with_tax,
        "max_affordable_domains": max_affordable_domains,
        "selected_domain_count": selected_domain_count,
        "total_spend": total_spend,
        "leftover_budget": leftover_budget,
        "annual_sell_through_pct": annual_sell_through_pct,
        "net_sale_price": net_sale_price,
        "total_domain_years": total_domain_years,
        "p_zero": round(p_zero, 4),
        "p_zero_pct": p_zero_pct,
        "p_at_least_one": round(p_at_least_one, 4),
        "p_at_least_one_pct": p_at_least_one_pct,
        "expected_sales": expected_sales_rounded,
        "expected_revenue": expected_revenue,
        "expected_net": expected_net,
        "break_even_price": break_even_price,
        "currency": currency,
        "exchange_rate": exchange_rate,
        "summary_sentence": summary_sentence,
        "disclaimer": "Illustrative arithmetic from your inputs, not a forecast.",
    }


def generate_sensitivity_matrix(
    domain_count: int,
    term_years: int,
    carry_cost_with_tax: float,
    sell_through_rates: List[float] = None,
    sale_prices: List[float] = None,
) -> Dict[str, Any]:
    """
    Generates a grid of net outcomes: rows = sell-through rates, cols = sale prices.
    Each cell shows net expected result = (N * term * rate * price) - (N * carry_cost_with_tax).
    """
    if sell_through_rates is None:
        sell_through_rates = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0, 10.0]
    if sale_prices is None:
        sale_prices = [50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0]

    total_domain_years = domain_count * term_years
    total_spend = round(domain_count * carry_cost_with_tax, 2)

    rows = []
    for rate in sell_through_rates:
        row_cells = []
        p = rate / 100.0
        exp_sales = total_domain_years * p
        for price in sale_prices:
            exp_rev = exp_sales * price
            net = round(exp_rev - total_spend, 2)
            row_cells.append({
                "rate": rate,
                "price": price,
                "net": net,
                "status": "gain" if net > 0 else ("loss" if net < 0 else "even"),
            })
        p_zero = (1.0 - p) ** total_domain_years if total_domain_years > 0 else 1.0
        p_zero_pct = round(p_zero * 100.0, 1)
        rows.append({
            "rate": rate,
            "p_zero_pct": p_zero_pct,
            "cells": row_cells,
        })

    return {
        "sell_through_rates": sell_through_rates,
        "sale_prices": sale_prices,
        "total_spend": total_spend,
        "matrix": rows,
    }


def generate_summary_sentence(
    domain_count: int,
    term_years: int,
    annual_sell_through_pct: float,
    p_zero_pct: float,
    p_at_least_one_pct: float,
    expected_net: float,
    currency: str = "EUR",
) -> str:
    """
    Honest plain-language statement emphasizing the probability of zero sales.
    """
    sym = "€" if currency == "EUR" else ("$" if currency == "USD" else f"{currency} ")
    if domain_count == 0:
        return "With zero domains selected, total spend is zero and no sales occur."

    if expected_net < 0:
        net_clause = f"an illustrative net loss of {sym}{abs(expected_net):,.2f}"
    elif expected_net > 0:
        net_clause = f"an illustrative net gain of {sym}{expected_net:,.2f}"
    else:
        net_clause = "an illustrative break-even outcome"

    return (
        f"Illustrative arithmetic from your inputs, not a forecast: Over {term_years} year(s) "
        f"with {domain_count} name(s) at an assumed {annual_sell_through_pct}% annual sell-through, "
        f"there is a {p_zero_pct}% chance of selling zero names ({p_at_least_one_pct}% chance of 1 or more sales), "
        f"yielding {net_clause}."
    )
