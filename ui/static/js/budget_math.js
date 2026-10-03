/**
 * Deterministic budget, carry cost, and sell-through probability calculator.
 *
 * NON-NEGOTIABLE POLICY:
 * This module performs arithmetic calculations based on user-provided inputs.
 * It is NOT a forecast, prediction, or valuation model.
 */

export function calculateCarryCost(firstYear, renewal, termYears) {
  const term = Math.max(1, Math.floor(termYears || 1));
  const cost = Number(firstYear || 0) + (term - 1) * Number(renewal || 0);
  return Math.round(cost * 100) / 100;
}

export function calculateBudgetModel({
  budget = 200,
  reservePct = 0,
  firstYear = 12.13,
  renewal = 13.61,
  taxPct = 0,
  termYears = 3,
  domainCount = 5,
  annualSellThroughPct = 2.0,
  netSalePrice = 500,
  currency = 'EUR',
  exchangeRate = 1.0,
} = {}) {
  const b = Math.max(0, Number(budget) || 0);
  const resPct = Math.max(0, Math.min(90, Number(reservePct) || 0));
  const tax = Math.max(0, Math.min(100, Number(taxPct) || 0));
  const term = Math.max(1, Math.min(10, Math.floor(termYears || 1)));
  const sellThrough = Math.max(0, Math.min(100, Number(annualSellThroughPct) || 0));
  const price = Math.max(0, Number(netSalePrice) || 0);

  // 1. Carry cost
  const baseCarryCost = calculateCarryCost(firstYear, renewal, term);
  const taxMultiplier = 1.0 + (tax / 100.0);
  const carryCostWithTax = Math.round(baseCarryCost * taxMultiplier * 100) / 100;

  // 2. Reserve & Usable Budget
  const reserveAmount = Math.round(b * (resPct / 100.0) * 100) / 100;
  const usableBudget = Math.max(0, Math.round((b - reserveAmount) * 100) / 100);

  // 3. Max affordable domains
  const maxAffordableDomains = carryCostWithTax > 0 
    ? Math.floor(usableBudget / carryCostWithTax) 
    : 0;

  // Selected domain count clamped by affordability
  const selectedDomainCount = Math.max(0, Math.min(Math.floor(domainCount || 0), maxAffordableDomains));

  // 4. Total Spend and Leftover
  const totalSpend = Math.round(selectedDomainCount * carryCostWithTax * 100) / 100;
  const leftoverBudget = Math.round((usableBudget - totalSpend) * 100) / 100;

  // 5. Probabilities (Binomial independent domain-years)
  const pAnnual = sellThrough / 100.0;
  const totalDomainYears = selectedDomainCount * term;

  let pZero = 1.0;
  let pAtLeastOne = 0.0;
  let expectedSales = 0.0;

  if (totalDomainYears === 0 || pAnnual <= 0.0) {
    pZero = 1.0;
    pAtLeastOne = 0.0;
    expectedSales = 0.0;
  } else if (pAnnual >= 1.0) {
    pZero = 0.0;
    pAtLeastOne = 1.0;
    expectedSales = Number(totalDomainYears);
  } else {
    pZero = Math.pow(1.0 - pAnnual, totalDomainYears);
    pAtLeastOne = 1.0 - pZero;
    expectedSales = totalDomainYears * pAnnual;
  }

  const pZeroPct = Math.round(pZero * 1000) / 10;
  const pAtLeastOnePct = Math.round(pAtLeastOne * 1000) / 10;
  const expectedSalesRounded = Math.round(expectedSales * 100) / 100;

  // 6. Financial Expected Value & Break-Even
  const expectedRevenue = Math.round(expectedSales * price * 100) / 100;
  const expectedNet = Math.round((expectedRevenue - totalSpend) * 100) / 100;

  const breakEvenPrice = expectedSales > 0 
    ? Math.round((totalSpend / expectedSales) * 100) / 100 
    : null;

  const summarySentence = generateSummarySentence({
    domainCount: selectedDomainCount,
    termYears: term,
    annualSellThroughPct: sellThrough,
    pZeroPct,
    pAtLeastOnePct,
    expectedNet,
    currency,
  });

  return {
    budget: b,
    reservePct: resPct,
    reserveAmount,
    usableBudget,
    taxPct: tax,
    firstYear: Number(firstYear),
    renewal: Number(renewal),
    termYears: term,
    carryCost: baseCarryCost,
    carryCostWithTax,
    maxAffordableDomains,
    selectedDomainCount,
    totalSpend,
    leftoverBudget,
    annualSellThroughPct: sellThrough,
    netSalePrice: price,
    totalDomainYears,
    pZero: Math.round(pZero * 10000) / 10000,
    pZeroPct,
    pAtLeastOne: Math.round(pAtLeastOne * 10000) / 10000,
    pAtLeastOnePct,
    expectedSales: expectedSalesRounded,
    expectedRevenue,
    expectedNet,
    breakEvenPrice,
    currency,
    exchangeRate: Number(exchangeRate) || 1.0,
    summarySentence,
    disclaimer: 'Illustrative arithmetic from your inputs, not a forecast.',
  };
}

export function generateSensitivityMatrix({
  domainCount = 5,
  termYears = 3,
  carryCostWithTax = 39.35,
  sellThroughRates = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0, 10.0],
  salePrices = [50, 100, 250, 500, 1000, 2500, 5000],
} = {}) {
  const totalDomainYears = domainCount * termYears;
  const totalSpend = Math.round(domainCount * carryCostWithTax * 100) / 100;

  const matrix = sellThroughRates.map((rate) => {
    const p = rate / 100.0;
    const expSales = totalDomainYears * p;
    const cells = salePrices.map((price) => {
      const expRev = expSales * price;
      const net = Math.round((expRev - totalSpend) * 100) / 100;
      let status = 'even';
      if (net > 0) status = 'gain';
      else if (net < 0) status = 'loss';
      return {
        rate,
        price,
        net,
        status,
      };
    });
    return {
      rate,
      cells,
    };
  });

  return {
    sellThroughRates,
    salePrices,
    totalSpend,
    matrix,
  };
}

export function generateSummarySentence({
  domainCount = 0,
  termYears = 3,
  annualSellThroughPct = 2.0,
  pZeroPct = 73.9,
  pAtLeastOnePct = 26.1,
  expectedNet = -46.75,
  currency = 'EUR',
} = {}) {
  const sym = currency === 'EUR' ? '€' : (currency === 'USD' ? '$' : `${currency} `);
  if (domainCount === 0) {
    return 'With zero domains selected, total spend is zero and no sales occur.';
  }

  let netClause = '';
  if (expectedNet < 0) {
    netClause = `an illustrative net loss of ${sym}${Math.abs(expectedNet).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  } else if (expectedNet > 0) {
    netClause = `an illustrative net gain of ${sym}${expectedNet.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  } else {
    netClause = 'an illustrative break-even outcome';
  }

  return `Illustrative arithmetic from your inputs, not a forecast: Over ${termYears} year(s) with ${domainCount} name(s) at an assumed ${annualSellThroughPct}% annual sell-through, there is a ${pZeroPct}% chance of selling zero names (${pAtLeastOnePct}% chance of 1 or more sales), yielding ${netClause}.`;
}
