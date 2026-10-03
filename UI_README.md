# SI Scout Local Dashboard User Manual

A calm, evidence-first, offline-ready research dashboard designed for evaluating `.si` domain combinations and modeling holding costs with mathematical realism.

---

## Quick Start (Demo Mode)

Launch demo mode with offline synthetic fixtures (zero live network lookups):
```bash
# Windows
run_demo.bat

# Linux / macOS
./run_demo.sh
```
Or directly from the terminal:
```bash
python ui/app.py --demo
```
Open **`http://127.0.0.1:8501`** in your browser.

---

## Design System & Theme
- **Color-Blind Safe Palette**: Diverging scales for sensitivity tables (Crimson for loss, Neutral for break-even, Teal for gain). Accessible status indicators.
- **Theme Switcher**: Instant Dark and Light mode toggle via the top navigation bar, with automatic OS preference detection and `localStorage` persistence.
- **Motion Reduction**: Strict `@media (prefers-reduced-motion: reduce)` support disables transitions and animations for users requesting minimal motion.
- **Zero External Fonts or CDNs**: 100% self-contained using modern system UI font stacks.

---

## Screen Inventory

### 1. Reality Check / Overview (`/`)
- **Three Live Computed Numbers**: Candidates screened, share already registered, and share unconfirmed 404s.
- **Honest Framing**: *"Most outcomes in this kind of portfolio lose money. Here is how to look at the numbers."*
- **Entry Hub**: Direct visual entry cards to **Budget Lab** and **Name Lab**.

### 2. Budget Lab (`/budget`)
- **The Interactive Centrepiece**:
  - Inputs: Total budget ($/€ with custom user FX rate), reserve buffer %, registrar fee presets (dated snapshot: 2026-09-30) or custom pricing, tax %, holding term (1–5 yrs), domain count slider (dynamically bounded by affordability), assumed annual sell-through (0–10%), and net sale price.
  - Live Carry Spend: Stacked animated budget bar dividing carry spend, reserve, and leftover cash.
  - **Headline Failure Rate**: Prominently displays the probability of selling **NOTHING** over the holding term (e.g. 73.9% chance of 0 sales with 5 names held 3 years at 2% sell-through).
  - Sensitivity Heatmap: 2D matrix comparing sell-through rates against net sale prices, highlighting the user's active scenario.
  - Plain-Language Summary: Generated arithmetic statement.
  - Sharing & Export: Live URL query parameter persistence (`?budget=...&term=...`), "Copy Summary" to clipboard, and CSV table export.
  - Non-Negotiable Label: *"Illustrative arithmetic from your inputs, not a forecast."*

### 3. Name Lab (`/name-lab`)
- **Instant Offline Heuristic Screener**:
  - Live character-by-character analysis without touching any network socket.
  - Register.si syntax rules (2–63 chars, hyphen positioning, valid characters).
  - Phonetic pronounceability, vowel ratio, and consonant cluster penalties.
  - Trademark & brand blocklist checks (`blocklist.yaml`, `reserved_domains.json`, and Tranco collisions).
  - Component score breakdown bar (Length 40, Pronounceability 35, Keyword Fit 25).
  - Permanent Banner: *"Not checked against the registry. Availability must be confirmed at a registrar."*

### 4. Screening Funnel Attrition & Saturation (`/funnel`)
- **Attrition Funnel**: Visual representation of the screening pipeline (100 lexical candidates &rarr; 75 pre-filtered &rarr; 75 checked &rarr; 15 registry 404 &rarr; 4 strict survivors).
- **Saturation by Pattern**: Empirical survival rates across single dictionary words, compound blends, and affixes.
- **Data Provenance**: Every metric displays its source file and build date.

### 5. Gate Simulator (`/gates`)
- **Educational Stepper**: Interactive checkboxes for all 6 non-negotiable verification gates:
  1. Not in Registry (RDAP 404)
  2. Fresh Registrar Pricing (&le; 7 days)
  3. Fresh Registry Check (&le; 60 minutes)
  4. Human Rationale (&ge; 8 words, human-authored)
  5. Budget Fit (affordable under holding term cap)
  6. Registrar Checkout Confirmation (&le; 60 minutes)
- Visual feedback on why automated tools cannot declare a domain ready to buy.

### 6. Candidate Explorer & Detail (`/candidates`, `/detail/<domain>`)
- Detailed candidate records, multi-tier ranking (`BUY_CANDIDATE`, `MONITOR`, `AVOID`), twin availability indicators (.com and .ai), and human rationale log.

### 7. Registrar Calibration (`/calibration`)
- Table comparing Register.si RDAP 404 responses against actual registrar checkout outcomes (e.g., `demo-agent.si` returned registry 404 but was reported taken at registrar checkout).

### 8. Watch & Drop Watch (`/watch`, `/drop-watch`)
- Daily tracking of status transitions and counter velocity.

### 9. Story Mode (`/story`)
- A 55-second, 7-slide presentation sequence optimized for creator screen recording and auditor walkthroughs.
- Features:
  - Slide Sequence: Hook &rarr; Funnel Attrition &rarr; Saturation &rarr; Registry/Registrar Discrepancy &rarr; 6 Gates &rarr; Budget Reality Check &rarr; Open Source Closing Card.
  - Aspect Ratio Controls: 16:9 (Landscape), 1:1 (Square), 4:5 (Vertical/Social).
  - Keyboard Controls: `[Space]` Play/Pause, `[Arrow Keys]` Step slides, `[A]` Cycle aspect ratios, `[C]` Toggle captions overlay, `[H]` Hide UI chrome and cursor for clean video capture.
