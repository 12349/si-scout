# Claims Register — SI Scout

This document registers every empirical, factual, and mathematical claim presented across the README, UI dashboards, and Story Mode.
In accordance with Rule 1 of release hardening, every claim is classified as:
- **COMPUTED**: Derived deterministically at render time from a tracked data file.
- **CITED**: Sourced from a named, dated third-party public investigation or registry report.
- **ILLUSTRATIVE**: A mathematical example or sensitivity scenario based on user-entered parameters.
- **HYPOTHESIS**: Stated explicitly as an unverified assumption or question for research.

---

## 1. Third-Party Empirical Citations

| Claim / Observation | Source | Date | Status | Where Displayed |
|:---|:---|:---|:---|:---|
| About 52% of Dynadot's .si registrations between Sept 19 and 22, 2026 were listed for resale | Netcraft Report on .si Domain Spike | Sept 2026 | CITED | Story Mode Slide 1, README.md |
| 2 of 35 public .si domain sales Jan–Jun 9, 2026 went to end users | Domain Name Wire .si Secondary Market Review | Jun 2026 | CITED | Story Mode Slide 1, Budget Lab, LIMITATIONS.md |
| Under Budget Lab default assumptions, most outcomes lose carry cost | Mathematical Sensitivity Matrix | 2026 | COMPUTED | Overview Page, Budget Lab |
| Typical annual sell-through rates for curated portfolios are 1–3% | Domain-investing guides (Namecheap & Name.com curated .com guides) | 2024–2026 | CITED / HYPOTHESIS | Budget Lab, LIMITATIONS.md |
| Register.si total domain registration counters | Register.si Public Counters | Daily | COMPUTED | Watch Mode, Funnel Page |

---

## 2. Dashboard Computed Metrics

| Screen / Feature | Metric Claim | Source File | Status |
|:---|:---|:---|:---|
| **Overview (Demo Mode)** | Candidates Screened: 100, Registry Checked: 75, Not In Registry: 15 | `demo_data/findings_data.json` | COMPUTED (Synthetic) |
| **Funnel Analysis** | Funnel stage attrition (100 -> 75 -> 75 -> 15 -> 4) | `demo_data/findings_data.json` | COMPUTED (Synthetic) |
| **Saturation by Pattern** | Single words 4.0% survival; Compound blends 26.7% unconfirmed | `demo_data/findings_data.json` | COMPUTED (Synthetic) |
| **Calibration Analysis** | Discrepancy comparison: 2 of 4 records disagreed | `demo_data/calibration.json` | COMPUTED (Synthetic) |
| **Registrar Pricing** | 1-Yr and Renewal USD costs for Dynadot, Hostinger, Domovanje | `si_scout/registrars.yaml` | COMPUTED (Snapshot: 2026-09-30) |

---

## 3. Budget Lab & Probability Claims

| Model Claim | Formula / Logic | Status | Where Displayed |
|:---|:---|:---|:---|
| Carry Cost | $\text{FirstYear} + (\text{Term} - 1) \times \text{Renewal}$ | COMPUTED (Arithmetic) | `/budget`, Story Slide 6 |
| Probability of Zero Sales | $P(0) = (1 - 	ext{SellThrough})^{	ext{Domains} 	imes 	ext{Years}}$ | ILLUSTRATIVE (Binomial) | `/budget`, Story Slide 6 |
| Break-Even Net Price | $\text{Total Spend} / \text{Expected Sales}$ | ILLUSTRATIVE (Arithmetic) | `/budget` |
| Sensitivity Matrix | Average outcome across combinations of sell-through and price | ILLUSTRATIVE (Arithmetic) | `/budget` |

---

## 4. Story Mode Presentation Slides

| Slide | Topic | Primary Assertion | Status / Evidence |
|:---|:---|:---|:---|
| **Slide 1** | Holding Costs | Holding costs compound over time; liquidity is low | CITED (Netcraft & Domain Name Wire) & ILLUSTRATIVE |
| **Slide 2** | Funnel Attrition | 96% attrition across lexical, brand, and registry checks | COMPUTED (Synthetic, `findings_data.json`) |
| **Slide 3** | Pattern Saturation | Single dictionary words have near-complete saturation | COMPUTED (Synthetic, `findings_data.json`) |
| **Slide 4** | Calibration Discrepancy | Registry 404 does not equal retail cart availability | COMPUTED (Synthetic, `calibration.json`) |
| **Slide 5** | Six Gating Safeguards | 6 strict gates required before declaring buy candidate | COMPUTED (`si_scout/config.py`, `ui/gates.py`) |
| **Slide 6** | Budget Reality Check | 73.9% chance of selling zero names in baseline scenario | ILLUSTRATIVE (`ui/static/js/budget_math.js`) |
| **Slide 7** | Open Source Release | Calm research tool with zero automated purchasing | FACTUAL |
