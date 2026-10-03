"""
Comprehensive anti-forecast and anti-hype regression test.
Verifies that no public UI templates, static JavaScript, or documentation
contain speculative, predictive, or urgency marketing language.
"""
import re
from pathlib import Path
import pytest

PROHIBITED_TERMS = [
    r"\bradical\s+honesty\b",
    r"\bquietly\s+consume\b",
    r"\bauthoritative\s+empirical\s+snapshot\b",
    r"\bstabilizing\b",
    r"\bstatistical\s+confidence\b",
    r"\bguaranteed\s+profit\b",
    r"\brisk-free\b",
    r"\bhigh\s+yield\b",
    r"\bprice\s+target\b",
    r"\bwill\s+sell\s+for\b",
    r"\bestimated\s+resale\s+value\b",
    r"\bhot\s+domain\b",
    r"\bmoon\s+shot\b",
    r"\bsure\s+thing\b",
    r"\bprofit\s+assured\b",
    r"\bundervalued\b",
]

# Valid negative disclaimer indicators
NEGATION_CUES = [
    "not a forecast",
    "no forecast",
    "anti-forecast",
    "anti_forecast",
    "without forecasting",
    "does not forecast",
    "not a prediction",
    "no prediction",
    "does not predict",
    "not predict",
    "never predicts",
    "never predict",
    "nothing on this page constitutes a valuation, forecast, or prediction",
    "attempting to calculate or predict an exact public drop timestamp is speculative",
    "not an appraisal tool",
]


def test_anti_forecast_and_hype_scan():
    repo_root = Path(__file__).parent.parent
    scan_paths = [
        repo_root / "ui" / "templates",
        repo_root / "ui" / "static",
        repo_root / "README.md",
        repo_root / "LIMITATIONS.md",
        repo_root / "RESPONSIBLE_USE.md",
    ]

    violations = []

    for path in scan_paths:
        if not path.exists():
            continue
        files = [path] if path.is_file() else list(path.rglob("*"))
        for file in files:
            if not file.is_file():
                continue
            if file.suffix.lower() not in {".html", ".js", ".md", ".txt"}:
                continue

            try:
                content = file.read_text(encoding="utf-8")
            except Exception:
                continue

            # 1. Prohibited terms (never allowed anywhere)
            for pattern in PROHIBITED_TERMS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for m in matches:
                    violations.append(f"{file.name}: matched prohibited term '{m.group(0)}'")

            # 2. Check bare 'forecast' or 'predict'
            for word in ["forecast", "predict"]:
                for match in re.finditer(rf"\b{word}\w*\b", content, re.IGNORECASE):
                    line_start = max(0, content.rfind("\n", 0, match.start()))
                    line_end = content.find("\n", match.end())
                    if line_end == -1:
                        line_end = len(content)
                    line_text = content[line_start:line_end].lower()

                    # Acceptable if line contains an explicit negative disclaimer cue
                    has_disclaimer = any(cue in line_text for cue in NEGATION_CUES)
                    if not has_disclaimer:
                        violations.append(
                            f"{file.name}:{match.start()}: Unqualified '{match.group(0)}' without disclaimer in: '{line_text.strip()}'"
                        )

    assert not violations, f"Anti-forecast scan found violations:\n" + "\n".join(violations)
