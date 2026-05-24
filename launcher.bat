@echo off
REM Metadelphi Launcher Script
REM This script starts the backend server, which also serves the built React frontend

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

if not exist "frontend\dist-react\index.html" (
    echo Error: Built React frontend not found at frontend\dist-react\index.html
    echo Build it first with:
    echo   cd frontend-react ^&^& npm install ^&^& npm run build
    pause
    exit /b 1
)

%PYTHON_CMD% service_runner.py status --quiet >nul 2>&1
if not errorlevel 1 (
    echo Metadelphi is already running in the background.
    start http://localhost:8000/
    exit /b 0
)

echo Starting Metadelphi...
echo ===================

REM Start backend server
echo Starting server on port 8000...
start /B %PYTHON_CMD% -m backend.main
timeout /t 2 /nobreak >nul

echo.
echo Metadelphi is running!
echo ===================
echo App:         http://localhost:8000/
echo Backend API: http://localhost:8000/docs
echo.

REM Open browser
start http://localhost:8000/

echo Press Ctrl+C or close this window to stop the application
echo.

REM Keep window open
pause >nul
