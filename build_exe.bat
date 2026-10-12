@echo off
REM Optional: builds a single TermHunter.exe you can copy anywhere (no Python needed to run it).
cd /d "%~dp0"
set "PY=python"
where python >nul 2>nul || set "PY=py -3"
if not exist ".venv\installed.flag" (
    %PY% -m venv .venv || goto :fail
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
    echo done > ".venv\installed.flag"
)
".venv\Scripts\python.exe" -m pip install pyinstaller || goto :fail
".venv\Scripts\pyinstaller.exe" --noconsole --onefile --name TermHunter ^
    --collect-all customtkinter --collect-all wordfreq --collect-all pystray app.py || goto :fail
echo.
echo  Done!  Your program is:  dist\TermHunter.exe
pause
exit /b 0
:fail
echo Build failed.
pause
exit /b 1
