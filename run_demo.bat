@echo off
cd /d "%~dp0"
echo ================================================================================
echo           Starting SI Scout in DEMO MODE (Offline Synthetic Fixtures)
echo ================================================================================
echo Zero network calls. No live registry queries.
echo.
python scripts\generate_demo_data.py
python ui\app.py --demo %*
pause
