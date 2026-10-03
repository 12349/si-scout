# LIMITATIONS & REALITY AUDIT (SI Scout)

**Role**: 🧐 **SKEPTIC Review**  
**Date**: September 30, 2026  
**Audience**: Human Operator / Capital Allocator ($200 Loss Limit)

This document plainly catalogs the weakest assumptions, structural risks, and unproven claims underlying the `.si` domain registration thesis following the September 2026 "Super Intelligence" US government usage.

---

## 1. The Three Weakest Assumptions in the Thesis

### Assumption 1: Tech companies and AI founders will adopt `.si` as an alternative to `.ai` or `.com`
- **Skeptic Critique**: This is completely unproven. Historically, ccTLDs that attempted to reposition around tech terms had mixed or dismal long-term adoption rates:
  - `.ai` (Anguilla) took over a decade of compound organic interest before reaching institutional momentum in 2023–2024.
  - `.io` (British Indian Ocean Territory) was popular among startups, but is now facing geopolitical uncertainty and price inflation.
  - `.co` (Colombia) and `.me` (Montenegro) never replaced `.com` for primary enterprise brands.
- **The Cold Reality**: Serious venture-backed AI labs will either buy their `.com`, default to `.ai`, or choose a mainstream generic TLD (`.org`, `.net`, `.io`). A startup choosing `.si` risks audience confusion with Slovenia's national ccTLD.

### Assumption 2: Speculative holding costs and registry pricing will remain stable over 3 years
- **Skeptic Critique**: ccTLD registries (ARNES) and registrars (such as Dynadot and Hostinger) operate under fluctuating currency exchange rates (EUR/USD) and can adjust wholesale registry or retail renewal pricing at any time.
- **The Cold Reality**: The USD 200 budget model assumes a static 3-year carrying cost of ~$39.35 per domain ($12.13 yr 1 + 2 × $13.61 renewal). If renewal fees increase to $25/year, the 3-year holding cost escalates from $39.35 to $62.13 per name, forcing the liquidation or abandonment of domains before any liquidity event occurs.

### Assumption 3: High registration spikes indicate genuine end-user demand
- **Documented Evidence**: Register.si recorded ~10.6k registrations in 24 hours. Netcraft documented that ~52% of early Dynadot registrations following the rush were listed for resale on secondary marketplaces (Sedo, Dan, Afternic). Domain Name Wire (DNW) documented only 2 verified end-user buyers out of 35 public `.si` transactions in Jan–Jun 2026.
- **Working Hypothesis**: A prevailing hypothesis is that early secondary-market activity reflects speculators trading among themselves rather than organic end-user demand. If commercial end-user buyers do not materialize within 12 months, unrenewed portfolios are hypothesized to drop into registry quarantine en masse by autumn 2027.

---

## 2. Technical & Protocol Limitations

1. **RDAP 404 Is Not a Legal or Registrability Guarantee**:
   - An HTTP 404 response from `rdap.register.si` indicates that a domain object is not currently active in the registry database.
   - However, a domain may be on Register.si's reserved list, restricted under Slovenian naming laws, or flagged as a premium tier at checkout. Always verify at final registrar checkout.

2. **No Purchasing Automation (By Design)**:
   - SI Scout deliberately prohibits automated checkout, credit card storage, or registrar purchasing automation.
   - The tool generates verified links; the human operator must execute the transaction manually after independent legal review.

3. **WHOIS & Contact Privacy Prohibition (NIS2 Compliance)**:
   - Unlike `.com`, `.si` does not permit WHOIS privacy proxies under Slovenian registry regulations enforcing the European NIS2 framework. Registrant contact details must be accurate and verifiable.
   - Using inaccurate registrant information violates registry policy and can trigger a 21-day verification audit by ARNES, risking domain suspension.
   - *Adoption Hypothesis*: It is hypothesized that global tech founders may hesitate to register `.si` names because personal or corporate contact details cannot be hidden behind privacy proxies, though whether this actively suppresses commercial adoption remains an untested assumption.

4. **Trademark & ARDS Dispute Vulnerability**:
   - The ARNES Alternative Dispute Resolution Scheme (ARDS) permits trademark holders to recover domains registered in bad faith without compensation.
   - Registering well-known trademarks, acronyms, or public figures will result in total loss of invested capital.

---

## 3. Financial Downside Assessment

- **Expected Value**: Probably negative. Domain-investing guides about curated `.com` portfolios (for example the Namecheap and Name.com guides) cite annual sell-through rates around 1–3%. This benchmark does NOT reflect `.si` data, where secondary market transaction volume is thin and liquidity is unproven.
- **Liquidity Horizon**: Domain assets are illiquid. Cash committed is locked.
- **Hard Rule**: Never commit more than the $200 loss limit. If no inbound inquiries or comparable sales occur by the first renewal cycle (Sept–Oct 2027), execute the kill criteria and allow the names to drop.

---

## 4. Local Dashboard (UI) Operational Boundaries

1. **Dashboard Is an Evidence Viewer, Not an Execution Engine**:
   - The UI never communicates with registrar purchasing APIs and stores zero payment methods.
   - All purchases must be completed manually by the user on the registrar's official portal.

2. **The Human-Rationale Gate Requires Active Human Effort**:
   - The UI explicitly refuses to auto-fill or suggest rationales for candidates.
   - Any rationale with fewer than 15 words, lacking an author tag of "human", or without explicit self-written confirmation is rejected as `source unknown: please rewrite`.

3. **Cache Invalidation & Freshness Guardrails**:
   - The UI surfaces loud red banners when registrar pricing is older than 7 days or domain availability checks are older than 24 hours.
   - The tool strictly prevents a candidate from appearing as ready-to-buy until real-time freshness is verified.

---

## 5. The Three Weakest Assumptions in the Screening Score

1. **Length As a Pure Proxy for Value (Shape Score: <=5 chars = +25 pts)**:
   - *Weakness*: Assumes brevity inherently equals commercial desirability. In reality, short arbitrary acronyms or awkward consonant blends (e.g. `sci`, `qubit`) may be short but lack commercial trademarkability, pronounceability, or brand resonance compared to a memorable 7-letter word.
2. **Synthetic Keyword Compounding as High-Demand Tech Naming**:
   - *Weakness*: Combining two AI stems (e.g., `tensor` + `node`, `agent` + `logic`) assumes venture-backed AI startups desire literal descriptive compounds. Modern tech branding strongly favors coined/abstract brands (e.g., Anthropic, Scale, Mistral, Cursor) over synthetic dictionary compounds.
3. **Twin Presence (.com / .ai) as a Positive Signal**:
   - *Weakness*: Treating an active `.com` or parked `.ai` as positive signal assumes spillover interest or validation. In reality, an established `.com` operator often creates significant trademark dilution risk, potential ARDS dispute vulnerability, or brand confusion rather than an exit acquisition opportunity.

---

## 6. Structural Evidence & Drop Tracking Limits

1. **Parked / For-Sale Twin Flags Are Phrase-Match Only (Weak Evidence)**:
   - Exactly 100% of twin parking determinations rest solely on automated HTTP body substring searches (`'for sale'`, `'parked'`, `'domain broker'`).
   - *Limitation*: A page containing the phrase "this domain is parked" may be an unconfigured server default, a registrar parking lander, or an editorial article. Phrase matching is heuristic context, not proof of secondary market availability.

2. **Quarantine Release Timing Is Unverified Until Observed**:
   - Under Register.si policy (`https://www.register.si/statusi-domen/`), expired domains enter a 30-day quarantine (*karantena*) during which the prior registrant retains the exclusive legal right to renew.
   - *Limitation*: Attempting to calculate or predict an exact public drop timestamp is speculative. Release timing remains strictly `UNKNOWN` until an actual status transition to `AVAILABLE_CANDIDATE` is observed in the daily watch log.

3. **Domain Expiration Is Not Proof of Non-Renewal**:
   - Tracking upcoming expiration dates in `drop_watch.csv` or `expiring_soon.csv` reflects only administrative calendar milestones.
   - *Limitation*: Over 90% of commercial domains are configured with registrar auto-renew on the final day of validity. An approaching expiration date indicates when to watch, never an expectation that the domain will drop.

4. **"READ FROM FILE" Labels Are Not Proof**:
   - Marking a statistic, date, or metric with `[READ FROM FILE]` indicates the value was pulled from an underlying record, but labels themselves are not proof.
   - *Limitation*: Files and reports can contain parsing bugs, column misalignments (e.g., confusing registration dates with expiration dates), or stale values. Every reported figure must be actively rechecked against the raw data and validated with automated regression tests.



