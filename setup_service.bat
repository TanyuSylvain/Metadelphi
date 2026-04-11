@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Error: Virtual environment not found.
    echo Please run install.bat first.
    exit /b 1
)

if not exist "service_runner.py" (
    echo Error: service_runner.py was not found.
    exit /b 1
)

set "TASK_NAME=Metadelphi"
set "LEGACY_TASK_NAME=UnifyLLM"
set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
set "PYTHONW_EXE=%CD%\.venv\Scripts\pythonw.exe"
if not exist "%PYTHONW_EXE%" (
    set "PYTHONW_EXE=%PYTHON_EXE%"
)

set "SERVICE_SCRIPT=%CD%\service_runner.py"

schtasks /query /tn "%LEGACY_TASK_NAME%" >nul 2>&1
if not errorlevel 1 (
    schtasks /end /tn "%LEGACY_TASK_NAME%" >nul 2>&1
    schtasks /delete /tn "%LEGACY_TASK_NAME%" /f >nul 2>&1
)

schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if not errorlevel 1 (
    schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
)

schtasks /create /tn "%TASK_NAME%" /sc onlogon /rl limited /tr "\"%PYTHONW_EXE%\" \"%SERVICE_SCRIPT%\" run" /f
if errorlevel 1 (
    echo Error: Failed to create the Metadelphi auto-start task.
    exit /b 1
)

schtasks /run /tn "%TASK_NAME%" >nul 2>&1

echo Metadelphi auto-start has been enabled.
echo Disable later with: remove_service.bat
exit /b 0
