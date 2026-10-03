# Contributing to SI Scout

Thank you for your interest in improving SI Scout!
We welcome bug reports, documentation clarifications, test coverage improvements, and cross-platform enhancements.

---

## Code of Conduct & Ground Rules
1. **Zero Hype / Anti-Forecast Policy**: Any PR adding speculative forecast language, "appreciation predictions", or automated investment recommendations will be rejected.
2. **Privacy First**: Never commit real personal information, registrant contact records, private API tokens, or unredacted WHOIS queries to this repository. Use `demo_data/` fixtures for all new tests.
3. **No Purchasing Automation**: We strictly refuse contributions that automate domain checkout, scrape registrar carts, or bypass human review gates.
4. **Offline Test Suite**: All unit and integration tests must pass without internet access (`python -m pytest`).

---

## Local Development Workflow

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/example/si-scout.git
cd si-scout

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development and test dependencies
pip install -r requirements-ui.txt
```

### 2. Running Tests
Ensure the entire test suite passes cleanly:
```bash
python -m pytest -v
```

### 3. Running Demo Mode
Test local UI changes using offline synthetic fixtures:
```bash
# On Linux / macOS
./run_demo.sh

# On Windows
run_demo.bat
```
Visit `http://127.0.0.1:8501` to view your changes.

---

## Good First Issues

Looking for a place to start? Consider one of these beginner-friendly improvements:
1. **Export Formats**: Add JSON export alongside the existing CSV and Markdown candidate exports.
2. **Additional Registrar Pricing Parsers**: Add offline pricing models in `si_scout/registrars.yaml` for regional European registrars (e.g. Hetzner, INWX).
3. **Keyboard Accessibility**: Enhance keyboard navigation in the Candidates data table (e.g., arrow key row selection, modal escape handling).
4. **Documentation Translations**: Translate user-facing limitation warnings and glossary entries into Slovenian or German.
