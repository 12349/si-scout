# Public Open-Source Release Checklist

This checklist defines the required verification steps before tagging or packaging a public release of SI Scout.
It ensures that the project remains reproducible, offline-first, completely private, and free of proprietary or sensitive operator records.

---

## 1. Secrets and Personal Data Scrub
- [ ] Ensure `.gitignore` is up to date and excludes all local scan databases (`scout.db*`), research CSVs (`results.csv`, `drop_watch.csv`, `expiring_soon.csv`), human records (`rationales.json`, `calibration.json`, `registrar_confirmations.json`), and operational logs (`watch_log.csv`, `*.log`).
- [ ] Ensure personal configuration files (`watchlist.yaml`, `private_terms.txt`, `.env`) are untracked and excluded.
- [ ] Run the automated private terms scanner:
  ```bash
  python scripts/check_private_terms.py
  ```
  Verify that the scanner returns exit code 0 with 0 sensitive keyword hits.
- [ ] Confirm that no absolute local file paths (e.g. `C:\Users\...` or `file:///` URIs) exist in documentation or code.

---

## 2. Git Author Identity & Commit Sanitization
- [ ] Set a local git identity (public pseudonym/handle plus GitHub noreply email) in the repository before making the first commit:
  ```bash
  git config user.name "Public Contributor Name"
  git config user.email "username@users.noreply.github.com"
  ```
- [ ] Inspect the commit author in git log before publishing:
  ```bash
  git log --format="%an <%ae>"
  ```
  Confirm that no private real name or personal email appears in the commit history.
- [ ] Confirm that no real names or personal emails are written into any tracked repository file.

---

## 3. Dependency & Licensing Audit
- [ ] Verify that all runtime dependencies in `requirements.txt` and `requirements-ui.txt` have exact pinned versions.
- [ ] Check `THIRD_PARTY_NOTICES.md` to ensure all open-source dependencies (Flask, Pandas, PyYAML, Requests, Pytest, Wordfreq) have accurate code and data licenses documented.
- [ ] Confirm that external research datasets (Tranco Top Sites) and word frequency data tables are **not bundled** in version control.
- [ ] Confirm zero copyleft (GPL / AGPL) license conflicts.

---

## 4. Demo Mode & Offline Isolation
- [ ] Confirm synthetic fixtures exist in `demo_data/`:
  - `demo_data/results.csv`
  - `demo_data/findings_data.json`
  - `demo_data/calibration.json`
  - `demo_data/drop_watch.csv`
  - `demo_data/watch_log.csv`
  - `demo_data/expiring_soon.csv`
  *(Note: `scout.db` and `portfolio.db` are automatically generated on first run of `--demo` and are gitignored).*
- [ ] Verify that all candidate domain names in `demo_data/` use synthetic prefixes (`example-`, `demo-`, `sample-`, `test-`, `mock-`) and reference no real entities.
- [ ] Start the demo dashboard locally:
  ```bash
  # Windows
  run_demo.bat

  # macOS / Linux
  ./run_demo.sh
  ```
- [ ] Verify that the top banner displays: `DEMO MODE | Demo data. Not real registry results.`
- [ ] Confirm socket blocking tests pass (`tests/test_demo_mode.py`), proving zero network calls are made in demo mode.

---

## 5. Documentation & Anti-Forecast Verification
- [ ] Verify that `README.md`, `LIMITATIONS.md`, and `RESPONSIBLE_USE.md` contain no speculative appreciation claims or forecast language.
- [ ] Verify that the 1–3% sell-through rate is properly attributed to general curated `.com` domain guides (not `.si` data).
- [ ] Verify that secondary market buyer findings cite documented reports (Netcraft, Domain Name Wire) as hypotheses rather than unproven generalities.
- [ ] Verify that registrar pricing is explicitly labeled as dated snapshots rather than live quotes.

---

## 6. Automated Test Suite
- [ ] Run the full test suite in an isolated clean environment:
  ```bash
  python -m pytest -v
  ```
  Ensure all 75+ tests pass with zero network lookups.
- [ ] Confirm GitHub Actions workflow (`.github/workflows/ci.yml`) is configured for Python 3.11 on Windows and Linux.
