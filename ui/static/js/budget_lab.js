/**
 * Budget Lab Interactive Controller.
 * Powered by deterministic budget_math.js.
 * Enhanced with scenario chips and click-to-lock sensitivity cells.
 * Zero external dependencies.
 */
import { calculateBudgetModel, generateSensitivityMatrix, generateSummarySentence } from './budget_math.js';

const PRESETS = {
  dynadot: { name: 'Dynadot (Dated snapshot: 2026-09-30)', firstYear: 12.13, renewal: 13.61, currency: 'USD' },
  hostinger: { name: 'Hostinger (Dated snapshot: 2026-09-30)', firstYear: 11.99, renewal: 16.99, currency: 'USD' },
  domovanje: { name: 'Domovanje (Dated snapshot: 2026-09-30)', firstYear: 16.90, renewal: 16.90, currency: 'EUR' },
  custom: { name: 'Custom values', firstYear: 12.13, renewal: 13.61, currency: 'USD' },
};

function parseQueryState() {
  const params = new URLSearchParams(window.location.search);
  return {
    budget: params.has('budget') ? parseFloat(params.get('budget')) : 200,
    reservePct: params.has('reserve') ? parseFloat(params.get('reserve')) : 0,
    preset: params.has('preset') ? params.get('preset') : 'dynadot',
    firstYear: params.has('y1') ? parseFloat(params.get('y1')) : 12.13,
    renewal: params.has('ren') ? parseFloat(params.get('ren')) : 13.61,
    taxPct: params.has('tax') ? parseFloat(params.get('tax')) : 0,
    termYears: params.has('term') ? parseInt(params.get('term'), 10) : 3,
    domainCount: params.has('names') ? parseInt(params.get('names'), 10) : 5,
    annualSellThroughPct: params.has('st') ? parseFloat(params.get('st')) : 2.0,
    netSalePrice: params.has('price') ? parseFloat(params.get('price')) : 500,
    currency: params.has('currency') ? params.get('currency') : 'USD',
    exchangeRate: params.has('fx') ? parseFloat(params.get('fx')) : 1.0,
  };
}

function syncUrlState(state) {
  const params = new URLSearchParams();
  params.set('budget', state.budget);
  params.set('reserve', state.reservePct);
  params.set('preset', state.preset);
  params.set('y1', state.firstYear);
  params.set('ren', state.renewal);
  params.set('tax', state.taxPct);
  params.set('term', state.termYears);
  params.set('names', state.domainCount);
  params.set('st', state.annualSellThroughPct);
  params.set('price', state.netSalePrice);
  params.set('currency', state.currency);
  if (state.currency === 'USD') {
    params.set('fx', state.exchangeRate);
  }
  const newUrl = `${window.location.pathname}?${params.toString()}`;
  window.history.replaceState({}, '', newUrl);
}

document.addEventListener('DOMContentLoaded', () => {
  const state = parseQueryState();

  // Inputs
  const budgetInput = document.getElementById('budgetInput');
  const currencySelect = document.getElementById('currencySelect');
  const fxGroup = document.getElementById('fxGroup');
  const fxInput = document.getElementById('fxInput');
  const reserveInput = document.getElementById('reserveInput');
  const presetSelect = document.getElementById('presetSelect');
  const firstYearInput = document.getElementById('firstYearInput');
  const renewalInput = document.getElementById('renewalInput');
  const taxInput = document.getElementById('taxInput');
  const termSlider = document.getElementById('termSlider');
  const termDisplay = document.getElementById('termDisplay');
  const domainSlider = document.getElementById('domainSlider');
  const domainDisplay = document.getElementById('domainDisplay');
  const domainMaxHint = document.getElementById('domainMaxHint');
  const sellThroughSlider = document.getElementById('sellThroughSlider');
  const sellThroughDisplay = document.getElementById('sellThroughDisplay');
  const salePriceInput = document.getElementById('salePriceInput');
  const chipButtons = document.querySelectorAll('.chip-btn');

  // Outputs
  const carryCostDisplay = document.getElementById('carryCostDisplay');
  const totalSpendDisplay = document.getElementById('totalSpendDisplay');
  const leftoverDisplay = document.getElementById('leftoverDisplay');
  const pZeroDisplay = document.getElementById('pZeroDisplay');
  const pOneDisplay = document.getElementById('pOneDisplay');
  const expSalesDisplay = document.getElementById('expSalesDisplay');
  const expNetDisplay = document.getElementById('expNetDisplay');
  const breakEvenDisplay = document.getElementById('breakEvenDisplay');
  const summarySentenceElem = document.getElementById('summarySentence');
  const heatmapContainer = document.getElementById('heatmapContainer');

  // Budget Bar
  const barSpend = document.getElementById('barSpend');
  const barReserve = document.getElementById('barReserve');
  const barLeftover = document.getElementById('barLeftover');
  const legendSpend = document.getElementById('legendSpend');
  const legendReserve = document.getElementById('legendReserve');
  const legendLeftover = document.getElementById('legendLeftover');

  // Action Buttons
  const copyBtn = document.getElementById('copyBtn');
  const csvBtn = document.getElementById('csvBtn');
  const copyFeedback = document.getElementById('copyFeedback');

  function initInputs() {
    budgetInput.value = state.budget;
    currencySelect.value = state.currency;
    fxInput.value = state.exchangeRate;
    reserveInput.value = state.reservePct;
    presetSelect.value = state.preset;
    firstYearInput.value = state.firstYear;
    renewalInput.value = state.renewal;
    taxInput.value = state.taxPct;
    termSlider.value = state.termYears;
    termDisplay.textContent = `${state.termYears} year(s)`;
    sellThroughSlider.value = state.annualSellThroughPct;
    sellThroughDisplay.textContent = `${state.annualSellThroughPct}%`;
    salePriceInput.value = state.netSalePrice;

    if (state.currency === 'USD') {
      fxGroup.style.display = 'flex';
    } else {
      fxGroup.style.display = 'none';
    }
  }

  function readInputs() {
    state.budget = Math.max(0, parseFloat(budgetInput.value) || 0);
    state.currency = currencySelect.value;
    state.exchangeRate = Math.max(0.01, parseFloat(fxInput.value) || 1.0);
    state.reservePct = Math.max(0, Math.min(90, parseFloat(reserveInput.value) || 0));
    state.preset = presetSelect.value;
    state.firstYear = Math.max(0, parseFloat(firstYearInput.value) || 0);
    state.renewal = Math.max(0, parseFloat(renewalInput.value) || 0);
    state.taxPct = Math.max(0, Math.min(100, parseFloat(taxInput.value) || 0));
    state.termYears = Math.max(1, Math.min(10, parseInt(termSlider.value, 10) || 1));
    state.annualSellThroughPct = Math.max(0, Math.min(10, parseFloat(sellThroughSlider.value) || 0));
    state.netSalePrice = Math.max(0, parseFloat(salePriceInput.value) || 0);
  }

  function render() {
    readInputs();

    // Model calculation
    const model = calculateBudgetModel(state);
    const sym = state.currency === 'EUR' ? '€' : (state.currency === 'USD' ? '$' : `${state.currency} `);

    // Update domain slider bounds based on affordability
    domainSlider.max = Math.max(1, model.maxAffordableDomains);
    if (state.domainCount > model.maxAffordableDomains) {
      state.domainCount = model.maxAffordableDomains;
    }
    domainSlider.value = state.domainCount;
    domainDisplay.textContent = `${state.domainCount} name(s)`;
    domainMaxHint.textContent = `Max affordable: ${model.maxAffordableDomains} names under budget`;

    // Re-evaluate with clamped domain count
    const finalModel = calculateBudgetModel(state);

    // Render Displays
    carryCostDisplay.textContent = `${sym}${finalModel.carryCostWithTax.toFixed(2)}`;
    totalSpendDisplay.textContent = `${sym}${finalModel.totalSpend.toFixed(2)}`;
    leftoverDisplay.textContent = `${sym}${finalModel.leftoverBudget.toFixed(2)}`;

    pZeroDisplay.textContent = `${finalModel.pZeroPct}%`;
    pOneDisplay.textContent = `${finalModel.pAtLeastOnePct}%`;
    expSalesDisplay.textContent = `${finalModel.expectedSales.toFixed(2)} sales`;

    const netVal = finalModel.expectedNet;
    if (netVal < 0) {
      expNetDisplay.textContent = `-${sym}${Math.abs(netVal).toFixed(2)} (loss)`;
      expNetDisplay.style.color = 'var(--status-negative)';
    } else if (netVal > 0) {
      expNetDisplay.textContent = `+${sym}${netVal.toFixed(2)} (gain)`;
      expNetDisplay.style.color = 'var(--status-positive)';
    } else {
      expNetDisplay.textContent = `${sym}0.00 (break-even)`;
      expNetDisplay.style.color = 'var(--text-primary)';
    }

    if (finalModel.breakEvenPrice) {
      breakEvenDisplay.textContent = `${sym}${finalModel.breakEvenPrice.toFixed(2)} / sale`;
    } else {
      breakEvenDisplay.textContent = 'N/A (0 sales expected)';
    }

    summarySentenceElem.textContent = finalModel.summarySentence;

    // Budget Bar Animation
    const totalB = Math.max(1, finalModel.budget);
    const spendPct = Math.min(100, (finalModel.totalSpend / totalB) * 100);
    const reservePct = Math.min(100, (finalModel.reserveAmount / totalB) * 100);
    const leftPct = Math.max(0, 100 - spendPct - reservePct);

    barSpend.style.width = `${spendPct}%`;
    barReserve.style.width = `${reservePct}%`;
    barLeftover.style.width = `${leftPct}%`;

    legendSpend.textContent = `Carry Spend: ${sym}${finalModel.totalSpend.toFixed(2)} (${spendPct.toFixed(1)}%)`;
    legendReserve.textContent = `Reserve: ${sym}${finalModel.reserveAmount.toFixed(2)} (${reservePct.toFixed(1)}%)`;
    legendLeftover.textContent = `Leftover: ${sym}${finalModel.leftoverBudget.toFixed(2)} (${leftPct.toFixed(1)}%)`;

    // Render Sensitivity Heatmap
    renderHeatmap(finalModel, sym);

    // Sync URL query state
    syncUrlState(state);
  }

  function renderHeatmap(model, sym) {
    const rates = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0, 10.0];
    const prices = [50, 100, 250, 500, 1000, 2500, 5000];
    const matrixData = generateSensitivityMatrix({
      domainCount: model.selectedDomainCount,
      termYears: model.termYears,
      carryCostWithTax: model.carryCostWithTax,
      sellThroughRates: rates,
      salePrices: prices,
    });

    let html = '<table class="heatmap-table"><thead><tr><th>Annual Sell-Through</th>';
    prices.forEach(p => {
      html += `<th>${sym}${p}</th>`;
    });
    html += '</tr></thead><tbody>';

    matrixData.matrix.forEach(row => {
      const isCurrentRate = Math.abs(row.rate - model.annualSellThroughPct) < 0.25;
      html += `<tr><td><strong>${row.rate.toFixed(1)}%</strong> <span style="font-size:0.75rem; color:var(--text-faint); font-family:var(--font-mono);">P(0): ${row.p_zero_pct}%</span></td>`;
      row.cells.forEach(cell => {
        const isCurrentPrice = Math.abs(cell.price - model.netSalePrice) < 50;
        const isCurrentPoint = isCurrentRate && isCurrentPrice;
        let cellClass = 'heatmap-cell-even';
        if (cell.net > 0) cellClass = 'heatmap-cell-gain';
        else if (cell.net < 0) cellClass = 'heatmap-cell-loss';

        if (isCurrentPoint) cellClass += ' heatmap-current-point';

        const sign = cell.net > 0 ? '+' : '';
        html += `<td class="${cellClass}" data-rate="${cell.rate}" data-price="${cell.price}" title="Click to lock: Rate ${cell.rate}%, Price ${sym}${cell.price}, Net ${sign}${sym}${cell.net.toFixed(2)}">${sign}${sym}${Math.round(cell.net)}</td>`;
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
    heatmapContainer.innerHTML = html;

    // Attach click listeners to matrix cells
    const tdCells = heatmapContainer.querySelectorAll('td[data-rate]');
    tdCells.forEach(td => {
      td.addEventListener('click', () => {
        const targetRate = parseFloat(td.getAttribute('data-rate'));
        const targetPrice = parseFloat(td.getAttribute('data-price'));
        sellThroughSlider.value = targetRate;
        sellThroughDisplay.textContent = `${targetRate}%`;
        salePriceInput.value = targetPrice;
        render();
      });
    });
  }

  // Preset Chips Listener
  chipButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      chipButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const bVal = parseFloat(btn.getAttribute('data-budget'));
      const tVal = parseInt(btn.getAttribute('data-term'), 10);
      const stVal = parseFloat(btn.getAttribute('data-st'));
      const pVal = parseFloat(btn.getAttribute('data-price'));

      budgetInput.value = bVal;
      termSlider.value = tVal;
      termDisplay.textContent = `${tVal} year(s)`;
      sellThroughSlider.value = stVal;
      sellThroughDisplay.textContent = `${stVal}%`;
      salePriceInput.value = pVal;

      render();
    });
  });

  // Event Listeners for Inputs
  [budgetInput, reserveInput, firstYearInput, renewalInput, taxInput, salePriceInput, fxInput].forEach(inp => {
    inp.addEventListener('input', () => {
      chipButtons.forEach(b => b.classList.remove('active'));
      render();
    });
  });

  presetSelect.addEventListener('change', () => {
    const choice = presetSelect.value;
    if (choice !== 'custom' && PRESETS[choice]) {
      firstYearInput.value = PRESETS[choice].firstYear;
      renewalInput.value = PRESETS[choice].renewal;
    }
    render();
  });

  currencySelect.addEventListener('change', () => {
    state.currency = currencySelect.value;
    if (state.currency === 'USD') {
      fxGroup.style.display = 'flex';
    } else {
      fxGroup.style.display = 'none';
    }
    render();
  });

  termSlider.addEventListener('input', () => {
    termDisplay.textContent = `${termSlider.value} year(s)`;
    chipButtons.forEach(b => b.classList.remove('active'));
    render();
  });

  domainSlider.addEventListener('input', () => {
    state.domainCount = parseInt(domainSlider.value, 10);
    domainDisplay.textContent = `${state.domainCount} name(s)`;
    render();
  });

  sellThroughSlider.addEventListener('input', () => {
    sellThroughDisplay.textContent = `${sellThroughSlider.value}%`;
    chipButtons.forEach(b => b.classList.remove('active'));
    render();
  });

  copyBtn.addEventListener('click', () => {
    const text = `${summarySentenceElem.textContent}\n\nInputs:\n- Budget: ${budgetInput.value} ${currencySelect.value}\n- Carry Cost / Name: ${carryCostDisplay.textContent}\n- Names: ${domainSlider.value}\n- Holding Term: ${termSlider.value} yr(s)\n- Sell-Through: ${sellThroughSlider.value}%\n- Net Price: ${salePriceInput.value}\n- Expected Net Outcome: ${expNetDisplay.textContent}\n\nDisclaimer: Illustrative arithmetic from your inputs, not a forecast.`;
    navigator.clipboard.writeText(text).then(() => {
      copyFeedback.textContent = '✓ Summary copied!';
      setTimeout(() => { copyFeedback.textContent = ''; }, 3000);
    });
  });

  csvBtn.addEventListener('click', () => {
    const rates = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0, 10.0];
    const prices = [50, 100, 250, 500, 1000, 2500, 5000];
    let csv = `SI Scout Budget Lab Export\nDate: ${new Date().toISOString()}\nDisclaimer: Illustrative arithmetic from your inputs not a forecast\n\n`;
    csv += `Annual Sell-Through Rate,` + prices.map(p => `"${state.currency} ${p}"`).join(',') + '\n';

    const matrix = generateSensitivityMatrix({
      domainCount: state.domainCount,
      termYears: state.termYears,
      carryCostWithTax: parseFloat(carryCostDisplay.textContent.replace(/[^0-9.]/g, '')),
      sellThroughRates: rates,
      salePrices: prices,
    });

    matrix.matrix.forEach(row => {
      csv += `${row.rate}%,` + row.cells.map(c => c.net).join(',') + '\n';
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `si_scout_budget_sensitivity_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  });

  initInputs();
  render();
});
