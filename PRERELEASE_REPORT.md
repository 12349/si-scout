# Pre-Release Audit & Hardening Report — SI Scout

**Date:** 2026-10-02  
**Target Repository:** `../si-scout-public`  
**Execution Context:** Fully offline verification, zero registry queries, demo mode synthetic fixtures.  
**Test Suite Status:** 106 passed / 106 tests across clean clone verification.

---

## 1. Resolution of Release Blockers (B1 – B10)

### **B1. Unsupported and Misattributed Claims in Story Mode**
- **What was wrong:** Slide 1 contained an alarmist headline (`Why .si Domain Speculation Is High Risk`), ungrounded hype (`quietly consume your entire budget`), and unsourced marketing language (`radical honesty`). Citations for Netcraft and Domain Name Wire were vague.
- **What changed:** Replaced with neutral headline: `What the numbers show about .si domain holding costs (illustrative)`. Added precise public citations: Netcraft's finding that ~52% of early Dynadot registrations were listed for resale, and Domain Name Wire's finding that only 2 of 35 public .si sales (Jan–Jun 2026) went to end-users. Replaced caption with neutral arithmetic description.
- **Test proving it:** `tests/test_release_hardening.py::test_b1_story_mode_claims_and_sources` and `tests/test_release_hardening.py::test_anti_forecast_extended_forbidden_terms`.

### **B2. Hard-Coded Real-World Claim on Funnel Page & Calibration Header**
- **What was wrong:** The Funnel page asserted as a fixed universal fact: *"In calibration testing, registrar checkout pages reported domains as 'already taken' ... despite registry 404 status"*. The Calibration page had a sub-label claiming *"Statistical confidence"* for 4 sample records.
- **What changed:** Dynamically computed from data at render time: `"In this dataset, {{ findings.calibration.disagrees_count }} of {{ findings.calibration.total_count }} comparisons disagreed. A registry 404 response does NOT confirm retail domain availability."` On `/calibration`, replaced *"Statistical confidence"* with `"Agreement rate (small sample)"` whenever sample size < 10.
- **Test proving it:** `tests/test_release_hardening.py::test_b2_funnel_calibration_data_claim`.

### **B3. Fabricated Checkout Outcomes Naming Real Companies**
- **What was wrong:** Synthetic calibration fixtures explicitly fabricated operational failure states for real companies (`Hostinger: already taken`, `Domovanje: registry busy`).
- **What changed:** Renamed all simulated checkout comparisons and notes in `demo_data/calibration.json`, `demo_data/registrar_confirmations.json`, `demo_data/results.csv`, and `scripts/generate_demo_data.py` to `Registrar A`, `Registrar B`, and `Registrar C`. Real registrar names remain solely in dated price snapshot references (`si_scout/registrars.yaml`).
- **Test proving it:** `tests/test_release_hardening.py::test_b3_no_real_company_names_in_demo_fixtures`.

### **B4. Currency Conversion Bug in Budget Lab**
- **What was wrong:** Switching currency to EUR simply relabeled USD amounts with `€` without applying currency conversion. Heatmap headers showed `$` while cells displayed `€`.
- **What changed:** Stored currency with each registrar preset (Dynadot/Hostinger = USD, Domovanje = EUR). Applied dynamic FX conversion upon currency selection or preset change. Synchronized single currency symbol (`$`, `€`) consistently across input labels, outputs, matrix headers, CSV export, summary sentence, copy clipboard, and share URLs.
- **Test proving it:** `tests/test_release_hardening.py::test_b4_currency_conversion_budget_lab`.

### **B5. Heatmap Framing & Probability of Zero Sales**
- **What was wrong:** The sensitivity matrix displayed green gain cells without explicit visible disclosure that individual outcomes are skewed toward zero sales.
- **What changed:** Appended mandatory framing directly under the matrix: *"Averages across many hypothetical portfolios. Most individual outcomes are a loss of the carry cost."* Enhanced `generate_sensitivity_matrix` to compute row-level `p_zero_pct` and displayed $P(0)$ in each sell-through row label (e.g. `2.0% (P(0) = 73.9%)`).
- **Test proving it:** `tests/test_release_hardening.py::test_b5_heatmap_averages_caption_and_row_pzero`.

### **B6. Gate Simulator Contradicting Core Rules**
- **What was wrong:** Simulator referenced "8 words" for Gate 4 rationale, whereas core engine (`ui/gates.py`, `si_scout/score.py`) strictly enforces 15 words. Header stated *"The tool never rates or recommends any name"*.
- **What changed:** Centralized thresholds in `si_scout/config.py` (`MIN_RATIONALE_WORDS = 15`, `MAX_CHECK_AGE_MINUTES = 60`, `MAX_PRICE_AGE_DAYS = 7`, `MAX_CONFIRMATION_AGE_MINUTES = 60`). Gate simulator imports from shared config and renders `15 words`. Reworded principle to: *"The tool never recommends a name to buy."*
- **Test proving it:** `tests/test_release_hardening.py::test_b6_gate_thresholds_shared_config`.

### **B7. Name Lab Overclaiming & popular-site List Transparency**
- **What was wrong:** Badge claimed *"NO BRAND / RESERVED COLLISIONS"*, quick test button used trademarked `"google"`, and footnote claimed a *"packaged top list"* and *"local trie"*.
- **What changed:** Badge renamed to *"Not on this tool's small example blocklist. This is not a trademark search."* Quick test chip replaced with synthetic `synthexample`. Footnote accurately explains that popular-site data is downloaded via `bootstrap_data.py` (not bundled) and shows *"popular-site list not loaded if absent"*.
- **Test proving it:** `tests/test_release_hardening.py::test_b7_name_lab_disclaimers`.

### **B8. Score Distinction Between Name Lab and Scanner**
- **What was wrong:** Name Lab's 0–100 heuristic shape score could be confused with the multi-stage scanner viability tiers.
- **What changed:** Labeled as `"Name Lab shape score, not the scanner score"` across UI headings, breakdown bars, and explanatory footnotes.
- **Test proving it:** `tests/test_release_hardening.py::test_b8_name_lab_score_distinct`.

### **B9. Internal Consistency Across Demo Screens**
- **What was wrong:** Overview claimed 75 checked and 60 registered; saturation table summed to 100 checked and 85 registered. Demo fixture used product-like name `AgentForge`.
- **What changed:** Unified single fixture object in `demo_data/findings_data.json` and `scripts/generate_demo_data.py`:
  - Funnel: 100 generated, 75 checked, 60 registered (80%), 15 unconfirmed (20%), 4 strict survivors.
  - Saturation by pattern: 25 single words + 30 compound blends + 15 affixes + 5 acronyms = 75 checked, 60 registered, 15 not in registry.
  - Replaced `AgentForge` with synthetic `SynthBlend`.
- **Test proving it:** `tests/test_release_hardening.py::test_b9_demo_data_internal_consistency`.

### **B10. Overview Headline Wording**
- **What was wrong:** Overview page banner claimed `"Authoritative Empirical Snapshot"`.
- **What changed:** Replaced with `"Demo snapshot (synthetic data) • Offline"`.
- **Test proving it:** `tests/test_release_hardening.py::test_b10_overview_wording_demo`.

---

## 2. Bug Fixes

- **Candidates Page Styling & NaN Registrar:**
  - Fixed white-on-white text in light mode by replacing hardcoded `#fff` with `var(--text-primary)`.
  - Missing registrar values now cleanly render `-` instead of `nan`.
  - Proved by: `tests/test_release_hardening.py::test_candidates_no_nan_and_domain_styled`.
- **Light Theme Contrast Across All Screens:**
  - Removed all orphaned `#fff` inline colors from text in `calibration.html`, `detail.html`, `drop_watch.html`, `glossary.html`, `portfolio.html`, `scan.html`, `shortlist.html`, `watch.html`. All typography now consumes semantic theme variables.
- **Watch Page Rush Velocity Assessment & Action Buttons:**
  - Removed speculative `Rush Velocity Assessment: STABILIZING / FADING` column and badges. Retained raw counters and neutral caption.
  - Disabled "Run Daily Watch Check Now" and "Start Scan" in demo mode with visible explanation banner: *"Zero live network lookups policy"*.
  - Proved by: `tests/test_release_hardening.py::test_watch_no_stabilizing_fading`.
- **Funnel Page Counter Chart:**
  - Replaced empty card with live tabular snapshot render of Register.si daily counters (`findings.counter.series`); hides automatically if no snapshot records exist.
- **Funnel Graphic Label Clipping:**
  - Realigned narrow lower stage labels so text never overflows SVG boundary.
- **Budget Lab Dropdown Truncation:**
  - Expanded sidebar control grid to `minmax(280px, 1fr)` ensuring registrar snapshots and dates are fully visible.

---

## 3. Release Safety Audit

- **Third-Party Disclaimers:** Added explicit non-affiliation and compliance notices to `README.md` and `ui/templates/base.html` footer:
  > *"Not affiliated with, or endorsed by, Register.si, ARNES, any registrar, Netcraft or Domain Name Wire. Product and company names belong to their owners. You are responsible for complying with the terms of any service you query."*
- **Claims Register:** Created `CLAIMS_REGISTER.md` cataloging every factual assertion, source, timestamp, and status classification (COMPUTED, CITED, ILLUSTRATIVE, HYPOTHESIS).
- **Maintainer Script Purge:** Removed `scripts/run_real_git_verification.py` from public release tree.
- **Private Terms Scanner:** Re-ran `scripts/check_private_terms.py` across all 109 release files (including dotfiles and extensionless); verified 0 hits.
- **Release Checklist:** Updated `RELEASE_CHECKLIST.md` with git identity verification steps before initial public commit.

---

## 4. Verification in Clean Clone

Executed clean copy outside the repository tree:
```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\public\Downloads\si-scout-clean-clone-test
configfile: pytest.ini
plugins: anyio-4.14.2
collected 106 items

tests/test_anti_forecast.py ..                                            [  1%]
tests/test_anti_forecast_comprehensive.py .                               [  2%]
tests/test_budget_math_parity.py ....                                     [  6%]
tests/test_budget_pricing.py ...                                          [  9%]
tests/test_demo_mode.py .......                                           [ 16%]
tests/test_generator.py ...                                               [ 18%]
tests/test_name_lab_offline.py ....                                       [ 22%]
tests/test_prefilter.py ......                                            [ 28%]
tests/test_pricing.py ..                                                  [ 30%]
tests/test_rate_limit.py .                                                [ 31%]
tests/test_rdap_mock.py .........                                         [ 39%]
tests/test_release_hardening.py ..............                            [ 52%]
tests/test_resume_cache.py .                                              [ 53%]
tests/test_score.py .......                                               [ 60%]
tests/test_twins.py ...                                                   [ 63%]
tests/test_ui_anti_forecast.py .                                          [ 64%]
tests/test_ui_data.py ...                                                 [ 66%]
tests/test_ui_freshness.py ....                                           [ 70%]
tests/test_ui_gates.py ..........                                         [ 80%]
tests/test_ui_recheck.py ..                                               [ 82%]
tests/test_ui_routes_demo.py ....                                         [ 85%]
tests/test_ui_smoke.py ...........                                        [ 96%]
tests/test_validator.py ....                                              [100%]
tests/test_watch.py .....                                                 [100%]

============================= 106 passed in 5.18s =============================
```

---

## 5. SKEPTIC Audit (Remaining Unverified Items)

The automated test suite verifies text patterns, code thresholds, and fixture parity. However, the following items cannot be verified by headless tests alone:
1. **Perceptual Balance & Readability:** While `#fff` hardcoding has been eliminated, human inspection across differing monitor contrasts is needed to ensure grey tones (`var(--text-muted)`) remain effortlessly legible in direct sunlight.
2. **Third-Party Rate Stability:** The default registrar prices (e.g. Dynadot $12.13, Hostinger $11.99, Domovanje €15.00) reflect snapshots from 2026-09-30. If a public user runs with stale prices, Gate 2 will correctly block them (>7 days), but live price scraping is intentionally omitted from demo mode.
3. **Subjective Tone:** Neutral phrasing has replaced all urgency claims. However, an external reader could still infer that passing all 6 gates implies a "good investment" rather than merely a "thoroughly screened candidate".

---

## 6. Mandatory Manual Pre-Release Steps (For User)

Before publishing or creating a public git remote, perform these four manual actions:
1. **Take Screenshots of Every Screen in Both Themes:**
   - Open [http://127.0.0.1:8501/](http://127.0.0.1:8501/) in your browser.
   - Click the theme toggle (🌙 / ☀️) to switch between Dark and Light mode.
   - Inspect and capture: `/`, `/budget`, `/name-lab`, `/funnel`, `/candidates`, `/gates`, `/watch`, `/calibration`, and `/story`.
2. **Read Every Sentence of Story Mode Aloud:**
   - Navigate to [http://127.0.0.1:8501/story](http://127.0.0.1:8501/story).
   - Advance through slides 1 to 7 using `[Space]` or `[→]`.
   - Read aloud to ensure no sentence sounds like sales advice or a get-rich-quick pitch.
3. **Set Your Public Git Identity:**
   - Execute in your release directory:
     ```bash
     git config user.name "Your Public Name"
     git config user.email "your-username@users.noreply.github.com"
     git log --format="%an <%ae>"
     ```
   - Ensure your personal machine username or private email is not attached to the git history.
4. **Run the First CI Build:**
   - Push to your intended remote only after verifying GitHub Actions runs pytest and `check_private_terms.py` green on Ubuntu and Windows.
