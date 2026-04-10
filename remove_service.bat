@echo off
setlocal

cd /d "%~dp0"

set "TASK_NAME=UnifyLLM"

if exist ".venv\Scripts\python.exe" if exist "service_runner.py" (
    ".venv\Scripts\python.exe" "service_runner.py" stop >nul 2>&1
)

schtasks /end /tn "%TASK_NAME%" >nul 2>&1
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

echo UnifyLLM auto-start has been removed.
exit /b 0
