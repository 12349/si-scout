@echo off
REM ============================================================================
REM SI Scout - Daily Watch Scheduled Task
REM Runs daily registry lookups for watchlist + earliest-expiring names (max 100/day)
REM Captures Register.si velocity counters and logs to watch_log.csv
REM ============================================================================

cd /d "%~dp0"
echo [%date% %time%] Starting SI Scout Daily Watch... >> watch_execution.log

python scripts\run_daily_watch.py %* >> watch_execution.log 2>&1

echo [%date% %time%] Daily Watch Completed with exit code %ERRORLEVEL% >> watch_execution.log
exit /b %ERRORLEVEL%
