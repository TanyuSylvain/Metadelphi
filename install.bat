@echo off
REM Metadelphi Installer Script for Windows
REM This script sets up Metadelphi on your system

echo ======================================
echo   Metadelphi Installation Wizard
echo ======================================
echo.

cd /d "%~dp0"
set "APP_DIR=%CD%"

REM Check if Python is installed (try python, then python3, then py)
echo Checking Python installation...
set PYTHON_CMD=

python --version 2>NUL
if not errorlevel 1 (
    set PYTHON_CMD=python
    goto :python_found
)

python3 --version 2>NUL
if not errorlevel 1 (
    set PYTHON_CMD=python3
    goto :python_found
)

py --version 2>NUL
if not errorlevel 1 (
    set PYTHON_CMD=py
    goto :python_found
)

echo ERROR: Python not found!
echo.
echo Python 3.10 or higher is required to run Metadelphi.
echo.
echo Please install Python from: https://www.python.org/downloads/
echo.
echo IMPORTANT: During installation, check "Add Python to PATH"
echo.
echo Opening Python download page...
start https://www.python.org/downloads/
echo.
echo After installing Python, please run this installer again.
pause
exit /b 1

:python_found
REM Check Python version
for /f "tokens=2" %%a in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%a
echo Found Python %PYTHON_VERSION% (using %PYTHON_CMD%)

REM Extract major and minor version (simple check)
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set PYTHON_MAJOR=%%a
    set PYTHON_MINOR=%%b
)

REM Check if version is 3.10 or higher (simplified check)
if %PYTHON_MAJOR% LSS 3 (
    echo ERROR: Python 3.10 or higher is required!
    echo Found: Python %PYTHON_VERSION%
    echo.
    echo Please upgrade Python from: https://www.python.org/downloads/
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

if %PYTHON_MAJOR% EQU 3 if %PYTHON_MINOR% LSS 10 (
    echo ERROR: Python 3.10 or higher is required!
    echo Found: Python %PYTHON_VERSION%
    echo.
    echo Please upgrade Python from: https://www.python.org/downloads/
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python version is compatible
echo.

REM Check if virtual environment already exists
if exist ".venv" (
    echo Virtual environment already exists. Removing old environment...
    rmdir /s /q .venv
)

REM Create virtual environment
echo Creating virtual environment...
%PYTHON_CMD% -m venv .venv

if not exist ".venv" (
    echo ERROR: Failed to create virtual environment!
    echo Please make sure Python is properly installed.
    pause
    exit /b 1
)

echo [OK] Virtual environment created
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
%PYTHON_CMD% -m pip install --upgrade pip --quiet

echo.
echo Installing dependencies...
echo This may take a few minutes. Progress will be shown below:
echo -----------------------------------------------------------
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies!
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo [OK] Dependencies installed successfully
echo.

REM Build frontend if needed
if not exist "frontend\dist-react\index.html" (
    echo Built frontend not found. Checking for Node.js...
    node --version >nul 2>&1
    if errorlevel 1 (
        echo Warning: Node.js not found. Skipping frontend build.
        echo Install Node.js, then build with:
        echo   cd frontend-react ^&^& npm install ^&^& npm run build
    ) else (
        echo Building React frontend...
        cd frontend-react
        call npm install
        call npm run build
        cd ..
        if exist "frontend\dist-react\index.html" (
            echo [OK] Frontend built successfully
        ) else (
            echo Warning: Frontend build did not produce frontend\dist-react\index.html.
        )
    )
    echo.
)

REM Add APP_DIR to user PATH so metadelphi.bat is callable as "metadelphi"
echo Adding Metadelphi to your PATH...
powershell -NoProfile -Command "& {$p=[Environment]::GetEnvironmentVariable('Path','User'); if ($p -notlike '*%APP_DIR%*') { [Environment]::SetEnvironmentVariable('Path', $p + ';%APP_DIR%', 'User'); Write-Host '[OK] Added %APP_DIR% to user PATH'} else { Write-Host '[OK] %APP_DIR% is already in user PATH'} }"
echo.

REM Create desktop shortcut
echo Creating desktop shortcut...
%PYTHON_CMD% installer\create_shortcut.py

if errorlevel 1 (
    echo Warning: Failed to create desktop shortcut
    echo You can still launch Metadelphi by running: metadelphi start
) else (
    echo [OK] Desktop shortcut created
)

echo.
set /p ENABLE_SERVICE="Enable Metadelphi auto-start at login? (y/n) "
if /i "%ENABLE_SERVICE%"=="y" (
    echo Setting up Metadelphi auto-start service...
    call setup_service.bat
    if errorlevel 1 (
        echo Warning: Failed to enable auto-start. You can try again later with: setup_service.bat
    )
) else (
    echo Auto-start not enabled.
    echo You can enable it later by running: setup_service.bat
)

echo.
echo ======================================
echo   Installation Complete!
echo ======================================
echo.
echo To start Metadelphi, run:
echo   metadelphi start
echo.
echo Then open http://localhost:8000/ in your browser and click
echo 'Open Configuration' to add your API keys.
echo.
echo Useful commands:
echo   metadelphi status   - check service status
echo   metadelphi restart  - restart the service
echo   metadelphi logs     - view backend logs
echo   metadelphi stop     - stop the service
echo.
echo To enable auto-start later, run:
echo   setup_service.bat
echo.
echo NOTE: If 'metadelphi' is not recognized, open a new Command Prompt
echo       so the updated PATH takes effect.
echo.

REM Ask if user wants to launch now
set /p LAUNCH="Would you like to launch Metadelphi now? (y/n) "
if /i "%LAUNCH%"=="y" (
    echo Launching Metadelphi...
    start launcher.bat
)

pause
