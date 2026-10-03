#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "================================================================================"
echo "          Starting SI Scout in DEMO MODE (Offline Synthetic Fixtures)           "
echo "================================================================================"
echo "Zero network calls. No live registry queries."
echo ""
python3 scripts/generate_demo_data.py || python scripts/generate_demo_data.py
python3 ui/app.py --demo "$@" || python ui/app.py --demo "$@"
