@echo off
REM Metadelphi Launcher Script
REM Starts the background service (if not running) and opens the web UI.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Error: Virtual environment not found!
    echo Please run the installer first: install.bat
    pause
    exit /b 1
)

if not exist "frontend\dist-react\index.html" (
    echo Error: Built React frontend not found at frontend\dist-react\index.html
    echo Build it first with:
    echo   cd frontend-react ^&^& npm install ^&^& npm run build
    pause
    exit /b 1
)

.venv\Scripts\python.exe service_runner.py status --quiet >nul 2>&1
if not errorlevel 1 (
    echo Metadelphi is already running in the background.
    start http://localhost:8000/
    exit /b 0
)

echo Starting Metadelphi...
.venv\Scripts\python.exe service_runner.py start
if errorlevel 1 (
    echo Failed to start Metadelphi.
    pause
    exit /b 1
)

timeout /t 2 /nobreak >nul
start http://localhost:8000/
echo.
echo Metadelphi is running at http://localhost:8000/
echo Use 'metadelphi stop' to stop the service.
pause
