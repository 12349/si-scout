/**
 * Name Lab Client Screener.
 * Evaluates candidate domain names offline with instant heuristics.
 * Enhanced with quick sample chips and dynamic score coloring.
 * Zero external calls.
 */

document.addEventListener('DOMContentLoaded', () => {
  const labelInput = document.getElementById('nameLabInput');
  const clearBtn = document.getElementById('clearInputBtn');
  const sampleBtns = document.querySelectorAll('.name-sample-btn');
  const resultCard = document.getElementById('nameLabResults');
  const fqdnTitle = document.getElementById('fqdnTitle');
  const scoreNumber = document.getElementById('scoreNumber');
  const syntaxBadge = document.getElementById('syntaxBadge');
  const blockBadge = document.getElementById('blockBadge');
  const lengthScoreBar = document.getElementById('lengthScoreBar');
  const pronounceScoreBar = document.getElementById('pronounceScoreBar');
  const keywordScoreBar = document.getElementById('keywordScoreBar');
  const lengthScoreVal = document.getElementById('lengthScoreVal');
  const pronounceScoreVal = document.getElementById('pronounceScoreVal');
  const keywordScoreVal = document.getElementById('keywordScoreVal');
  const metricsDetails = document.getElementById('metricsDetails');

  let debounceTimer = null;

  async function evaluateLabel(rawLabel) {
    const label = (rawLabel || '').trim();
    if (!label) {
      resultCard.style.display = 'none';
      return;
    }

    try {
      const resp = await fetch('/api/name-lab/screen', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label }),
      });
      if (!resp.ok) return;
      const data = await resp.json();
      renderResults(data);
    } catch (err) {
      console.error('Offline screening error:', err);
    }
  }

  function renderResults(d) {
    resultCard.style.display = 'block';
    fqdnTitle.textContent = `${d.label}.si`;
    scoreNumber.textContent = d.score.toFixed(1);

    // Dynamic Score Coloring
    if (d.score >= 70) {
      scoreNumber.style.color = 'var(--status-positive)';
    } else if (d.score >= 40) {
      scoreNumber.style.color = 'var(--status-caution)';
    } else {
      scoreNumber.style.color = 'var(--status-negative)';
    }

    // Syntax Badge
    if (d.is_valid_syntax) {
      syntaxBadge.textContent = 'Syntax Valid (2-63 chars)';
      syntaxBadge.style.backgroundColor = 'var(--status-positive)';
      syntaxBadge.style.color = '#ffffff';
    } else {
      syntaxBadge.textContent = `Syntax Invalid: ${d.syntax_reason}`;
      syntaxBadge.style.backgroundColor = 'var(--status-negative)';
      syntaxBadge.style.color = '#ffffff';
    }

    // Blocklist Badge
    if (d.is_blocked) {
      blockBadge.textContent = d.is_reserved ? 'Reserved Domain (Blocked)' : 'Protected Mark / Brand Collision';
      blockBadge.style.backgroundColor = 'var(--status-negative)';
      blockBadge.style.color = '#ffffff';
    } else {
      blockBadge.textContent = "Not on this tool's small example blocklist. This is not a trademark search.";
      blockBadge.style.backgroundColor = 'var(--bg-subtle)';
      blockBadge.style.color = 'var(--text-muted)';
    }

    // Breakdown Bars
    const b = d.breakdown || {};
    const lPct = ((b.length_score || 0) / 40) * 100;
    const pPct = ((b.pronounceability_score || 0) / 35) * 100;
    const kPct = ((b.keyword_fit_score || 0) / 25) * 100;

    lengthScoreBar.style.width = `${lPct}%`;
    pronounceScoreBar.style.width = `${pPct}%`;
    keywordScoreBar.style.width = `${kPct}%`;

    lengthScoreVal.textContent = `${(b.length_score || 0).toFixed(1)} / 40`;
    pronounceScoreVal.textContent = `${(b.pronounceability_score || 0).toFixed(1)} / 35`;
    keywordScoreVal.textContent = `${(b.keyword_fit_score || 0).toFixed(1)} / 25`;

    // Metrics Details
    let detailsHtml = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-top: 1.25rem;">
        <div style="background: var(--bg-surface); padding: 0.85rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
          <div style="font-size: 0.72rem; text-transform: uppercase; color: var(--text-faint); font-weight: 700;">Character Count</div>
          <div style="font-size: 1.25rem; font-family: var(--font-mono); font-weight: 700;">${d.length} chars</div>
        </div>
        <div style="background: var(--bg-surface); padding: 0.85rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
          <div style="font-size: 0.72rem; text-transform: uppercase; color: var(--text-faint); font-weight: 700;">Vowel Ratio</div>
          <div style="font-size: 1.25rem; font-family: var(--font-mono); font-weight: 700;">${Math.round(d.vowel_ratio * 100)}%</div>
          <div style="font-size: 0.72rem; color: var(--text-faint);">${d.vowel_count} vowels / ${d.consonant_count} consonants</div>
        </div>
        <div style="background: var(--bg-surface); padding: 0.85rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
          <div style="font-size: 0.72rem; text-transform: uppercase; color: var(--text-faint); font-weight: 700;">Consonant Flow</div>
          <div style="font-size: 1.1rem; font-weight: 700; margin-top: 0.15rem;">${d.has_awkward_consonants ? '<span style="color:var(--status-caution)">⚠️ Awkward Cluster</span>' : '<span style="color:var(--status-positive)">✓ Smooth</span>'}</div>
        </div>
        <div style="background: var(--bg-surface); padding: 0.85rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
          <div style="font-size: 0.72rem; text-transform: uppercase; color: var(--text-faint); font-weight: 700;">Lexical Pre-Filter</div>
          <div style="font-size: 1.1rem; font-weight: 700; margin-top: 0.15rem;">${d.prefilter_passed ? '<span style="color:var(--status-positive)">✓ Passed</span>' : '<span style="color:var(--status-negative)">✕ Rejected</span>'}</div>
        </div>
      </div>
    `;
    if (d.block_reason) {
      detailsHtml += `<div style="margin-top: 1rem; padding: 0.75rem 1rem; background: rgba(244, 63, 94, 0.08); border-left: 4px solid var(--status-negative); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; font-size: 0.88rem; color: var(--status-negative); font-weight: 500;"><strong>Filter Restriction:</strong> ${d.block_reason}</div>`;
    }
    metricsDetails.innerHTML = detailsHtml;
  }

  // Sample Chips Listeners
  sampleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const lbl = btn.getAttribute('data-label');
      labelInput.value = lbl;
      evaluateLabel(lbl);
      labelInput.focus();
    });
  });

  // Clear Button
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      labelInput.value = '';
      resultCard.style.display = 'none';
      labelInput.focus();
    });
  }

  labelInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      evaluateLabel(labelInput.value);
    }, 150);
  });

  if (labelInput.value) {
    evaluateLabel(labelInput.value);
  }
});
