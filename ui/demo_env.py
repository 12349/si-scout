"""
SI Scout: Demo Environment Helper for Serverless / Read-Only Filesystems.
Detects if the source demo_data folder is read-only (such as on Vercel / AWS Lambda),
and seamlessly mirrors synthetic fixtures to a writable directory in /tmp.
"""

import logging
import os
from pathlib import Path
import shutil
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent

def get_demo_dir(configured_dir: Optional[Path] = None) -> Path:
    source_dir = Path(configured_dir) if configured_dir else (REPO_ROOT / "demo_data")

    # Probe writability of source_dir
    is_writable = False
    try:
        source_dir.mkdir(parents=True, exist_ok=True)
        probe = source_dir / f".write_probe_{os.getpid()}"
        probe.write_text("1", encoding="utf-8")
        probe.unlink()
        is_writable = True
    except (OSError, PermissionError):
        is_writable = False

    # In serverless environments (e.g. Vercel) or read-only filesystems, use /tmp
    if is_writable and not os.environ.get("VERCEL"):
        effective_dir = source_dir
    else:
        effective_dir = Path(tempfile.gettempdir()) / "si_scout_demo_data"
        effective_dir.mkdir(parents=True, exist_ok=True)
        if source_dir.exists():
            for item in source_dir.iterdir():
                target = effective_dir / item.name
                if not target.exists():
                    try:
                        if item.is_dir():
                            shutil.copytree(item, target, dirs_exist_ok=True)
                        else:
                            shutil.copy2(item, target)
                    except Exception as e:
                        logger.warning(f"Could not copy fixture {item.name}: {e}")

    # Ensure scout.db and portfolio.db exist in effective_dir
    try:
        from scripts.generate_demo_data import ensure_demo_databases
        ensure_demo_databases(effective_dir)
    except Exception as e:
        logger.warning(f"Could not auto-generate demo databases in {effective_dir}: {e}")

    return effective_dir
