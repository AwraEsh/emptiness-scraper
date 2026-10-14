@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 run.py
    if errorlevel 1 goto :failure
    exit /b 0
)
where python >nul 2>nul
if errorlevel 1 (
    echo Install Python 3.11 or newer from https://www.python.org/downloads/
    pause
    exit /b 1
)
python run.py
if errorlevel 1 goto :failure
exit /b 0
:failure
echo The launcher could not start. Review the message above and try again.
if not defined EMPTYNESS_SCRAPER_SMOKE pause
exit /b 1
