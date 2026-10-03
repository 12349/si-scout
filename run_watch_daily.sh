#!/usr/bin/env bash
# ==============================================================================
# SI Scout - Daily Watch Scheduled Task (POSIX / Linux / macOS)
# Runs daily registry lookups for watchlist + earliest-expiring names (max 100/day)
# ==============================================================================
set -e
cd "$(dirname "$0")"

echo "[$(date -u)] Starting SI Scout Daily Watch..." >> watch_execution.log
python3 scripts/run_daily_watch.py "$@" >> watch_execution.log 2>&1 || python scripts/run_daily_watch.py "$@" >> watch_execution.log 2>&1
echo "[$(date -u)] Daily Watch Completed with exit code $?" >> watch_execution.log
