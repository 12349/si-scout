import re
import pytest
from pathlib import Path

FORBIDDEN_UI_PHRASES = [
    r"\bwill appreciate\b",
    r"\bhigh potential\b",
    r"\bundervalued\b",
    r"\bgem\b",
    r"\bguaranteed\b",
    r"\bguarantee\b",
    r"\bnext \.ai\b",
    r"\b100x\b",
    r"\brisk[- ]free\b",
    r"\bpassive income\b",
    r"\bsure thing\b"
]

def test_ui_anti_forecast_strings():
    ui_dir = Path("ui")
    if not ui_dir.exists():
        pytest.skip("ui directory does not exist yet")

    files_to_check = list(ui_dir.rglob("*.py")) + list(ui_dir.rglob("*.html")) + list(ui_dir.rglob("*.js"))
    assert len(files_to_check) > 0, "No UI files found to scan"

    violations = []
    for file_path in files_to_check:
        content = file_path.read_text(encoding="utf-8", errors="ignore").lower()
        for phrase_regex in FORBIDDEN_UI_PHRASES:
            match = re.search(phrase_regex, content)
            if match:
                violations.append(f"File {file_path}: Found forbidden phrase '{match.group(0)}'")

    assert len(violations) == 0, f"Found anti-forecast violations in UI:\n" + "\n".join(violations)
