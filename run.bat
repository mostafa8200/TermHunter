@echo off
REM ============================================================
REM  Term Hunter launcher - just double-click this file.
REM  If Python is missing it is installed for you automatically.
REM  First run takes a few minutes; later runs open instantly.
REM ============================================================
cd /d "%~dp0"

set "PY="
for /f "delims=" %%i in ('python -c "import sys;print(sys.executable)" 2^>nul') do set "PY=%%i"
if not defined PY for /f "delims=" %%i in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do set "PY=%%i"

if not defined PY (
    echo Installing Python automatically - please wait a few minutes...
    winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
    set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not exist "%PY%" (
    echo.
    echo  Could not install Python automatically.
    echo  Opening the download page: install it, TICK "Add python.exe to PATH",
    echo  then double-click run.bat again.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist ".venv\installed.flag" (
    echo First-time setup - please wait, this only happens once...
    "%PY%" -m venv .venv || goto :fail
    ".venv\Scripts\python.exe" -m pip install --upgrade pip || goto :fail
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
    echo done > ".venv\installed.flag"
)

start "" ".venv\Scripts\pythonw.exe" app.py
exit /b 0

:fail
echo.
echo  Setup failed. Check your internet connection and try again.
echo  (Delete the ".venv" folder if this keeps happening.)
pause
exit /b 1
