@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 (
    set "PYTHON=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python 3.11 or newer is required. Install Python from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set "PYTHON=python"
)

%PYTHON% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 (
    echo Python 3.11 or newer is required. Your current interpreter is too old.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating the private Python environment...
    %PYTHON% -m venv .venv
    if errorlevel 1 goto :failure
)

set "PYTHONUTF8=1"
echo Checking required packages...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet -r requirements.txt
if errorlevel 1 goto :failure

".venv\Scripts\python.exe" -m emptiness_scraper
if errorlevel 1 exit /b 1
exit /b 0

:failure
echo Setup failed. Check your internet connection and Python installation, then run this file again.
pause
exit /b 1
