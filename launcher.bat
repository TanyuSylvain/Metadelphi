@echo off
REM Metadelphi Launcher Script
REM This script starts both the backend and frontend servers

cd /d "%~dp0"

REM Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo Error: Virtual environment not found!
    echo Please run the installer first: install.bat
    pause
    exit /b 1
)

REM Detect Python command (try python, then python3, then py)
set PYTHON_CMD=python
python --version 2>NUL
if errorlevel 1 (
    python3 --version 2>NUL
    if not errorlevel 1 (
        set PYTHON_CMD=python3
    ) else (
        py --version 2>NUL
        if not errorlevel 1 (
            set PYTHON_CMD=py
        )
    )
)

REM Check if .env file exists
if not exist ".env" (
    echo Warning: .env file not found!
    echo Please configure your API keys by copying .env.template to .env
    echo Opening configuration wizard...
    %PYTHON_CMD% installer\config_wizard.py
)

%PYTHON_CMD% service_runner.py status --quiet >nul 2>&1
if not errorlevel 1 (
    echo Metadelphi is already running in the background.
    start http://localhost:8080/index.html
    exit /b 0
)

echo Starting Metadelphi...
echo ===================

REM Start backend server
echo Starting backend server on port 8000...
start /B %PYTHON_CMD% -m backend.main
timeout /t 2 /nobreak >nul

REM Start frontend server
echo Starting frontend server on port 8080...
start /B %PYTHON_CMD% -m http.server 8080 --directory frontend\src
timeout /t 1 /nobreak >nul

echo.
echo Metadelphi is running!
echo ===================
echo Backend API: http://localhost:8000
echo Frontend:    http://localhost:8080/index.html
echo.

REM Open browser
start http://localhost:8080/index.html

echo Press Ctrl+C or close this window to stop the application
echo.

REM Keep window open
pause >nul
