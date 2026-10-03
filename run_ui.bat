@echo off
title SI Scout Local Dashboard
echo ================================================================================
echo                    SI SCOUT: LOCAL RESEARCH DASHBOARD
echo ================================================================================
echo Checking local environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.11+ is not found in your PATH. Please install Python.
    pause
    exit /b 1
)

echo Installing / verifying UI requirements...
python -m pip install -r requirements-ui.txt --quiet

echo Launching SI Scout Dashboard bound strictly to 127.0.0.1:8501...
start "" http://127.0.0.1:8501
python ui/app.py
pause
