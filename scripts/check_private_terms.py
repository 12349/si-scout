#!/usr/bin/env python3
"""
SI Scout: Pre-Publish Private Terms Scanner
Scans tracked repository files to prevent accidental leakage of private research
candidate labels, operator usernames, or internal codenames.

Exits with code 1 if any private terms are discovered.
Exits with code 0 if all tracked files are clean.
"""

import fnmatch
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import List, Set

REPO_ROOT = Path(__file__).resolve().parent.parent

def load_private_terms(root: Path) -> Set[str]:
    """Loads terms from private_terms.txt (ignored) plus private_terms.example.txt (placeholders)."""
    terms = set()
    for filename in ["private_terms.txt", "private_terms.example.txt"]:
        terms_file = root / filename
        if terms_file.exists():
            with open(terms_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        terms.add(line.lower())
    return terms

def get_tracked_files(root: Path) -> List[Path]:
    """Retrieves git-tracked files via 'git ls-files', or non-ignored files if git is unavailable."""
    try:
        res = subprocess.run(
            ["git", "ls-files"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=True
        )
        files = [root / line.strip() for line in res.stdout.splitlines() if line.strip()]
        return [f for f in files if f.is_file()]
    except Exception:
        patterns = []
        gi = root / ".gitignore"
        if gi.exists():
            with open(gi, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)

        def is_ignored(rel_p: str) -> bool:
            rel_p = rel_p.replace("\\", "/")
            if rel_p.startswith("demo_data/") or rel_p == "ui/templates/portfolio.html":
                return False
            for pat in patterns:
                if pat.startswith("!"):
                    continue
                if pat.startswith("/"):
                    root_pat = pat.lstrip("/")
                    if "/" not in rel_p and fnmatch.fnmatch(rel_p, root_pat):
                        return True
                else:
                    pat_clean = pat.rstrip("/")
                    if fnmatch.fnmatch(rel_p, pat_clean) or fnmatch.fnmatch(os.path.basename(rel_p), pat_clean):
                        return True
                    for part in rel_p.split("/"):
                        if fnmatch.fnmatch(part, pat_clean):
                            return True
            return False

        files = []
        for r, d, fs in os.walk(root):
            if any(p in r for p in [".git", "__pycache__", ".pytest_cache", "scratch", "_clean_release_test"]):
                continue
            for file in fs:
                full_p = Path(r) / file
                rel_p = full_p.relative_to(root).as_posix()
                if not is_ignored(rel_p):
                    files.append(full_p)
        return files

def main():
    terms = load_private_terms(REPO_ROOT)
    if not terms:
        print("[check_private_terms] No terms to scan. Exiting clean.")
        sys.exit(0)

    print(f"[check_private_terms] Loaded {len(terms)} private term(s) for verification.")
    files = get_tracked_files(REPO_ROOT)
    
    # Files to exclude from scan (the private_terms files themselves)
    ignore_files = {"private_terms.txt", "private_terms.example.txt"}
    
    print(f"[check_private_terms] Scanning {len(files)} release file(s) (including dotfiles and extensionless)...")
    
    skipped = []
    for f in REPO_ROOT.glob("*"):
        if f.is_file() and f.name in ignore_files:
            skipped.append((f.name, "contains search patterns"))
    if skipped:
        print(f"[check_private_terms] Excluded files from self-scan: {skipped}")

    # Compile word-boundary regex pattern
    escaped = [re.escape(t) for t in terms]
    regex = re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE)

    violations = []
    for fpath in files:
        if fpath.name in ignore_files:
            continue
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                for line_no, line in enumerate(fp, start=1):
                    for match in regex.finditer(line):
                        violations.append((
                            fpath.relative_to(REPO_ROOT).as_posix(),
                            line_no,
                            match.group(0),
                            line.strip()[:80]
                        ))
        except Exception as e:
            print(f"[WARNING] Could not read {fpath}: {e}")

    if violations:
        print(f"\n[FAIL] Found {len(violations)} private term hit(s) in release files:")
        for v in violations:
            print(f"  {v[0]}:{v[1]}: [{v[2]}] {v[3]}")
        print("\nPlease redact or exclude these files before publishing.")
        sys.exit(1)
    else:
        print("\n[PASS] 0 private term hits found across all release files. Clean to publish.")
        sys.exit(0)

if __name__ == "__main__":
    main()
