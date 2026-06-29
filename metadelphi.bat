@echo off
REM Global Metadelphi CLI wrapper for Windows.
REM This script is added to the user PATH by install.bat.

setlocal EnableDelayedExpansion

REM Resolve project directory from this script's location.
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

set "PYTHON_BIN=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "SERVICE_RUNNER=%PROJECT_DIR%\service_runner.py"

if not exist "%PYTHON_BIN%" (
    echo Error: Metadelphi virtual environment not found at %PROJECT_DIR%\.venv
    echo Please run the installer first.
    exit /b 1
)

if not exist "%SERVICE_RUNNER%" (
    echo Error: Metadelphi service runner not found at %SERVICE_RUNNER%
    exit /b 1
)

set "COMMAND=%~1"

if "%COMMAND%"=="start" goto :delegate
if "%COMMAND%"=="stop" goto :delegate
if "%COMMAND%"=="restart" goto :delegate
if "%COMMAND%"=="status" goto :delegate
if "%COMMAND%"=="logs" goto :delegate
if "%COMMAND%"=="run" goto :delegate
if "%COMMAND%"=="config" goto :config
if "%COMMAND%"=="help" goto :help
if "%COMMAND%"=="--help" goto :help
if "%COMMAND%"=="-h" goto :help
if "%COMMAND%"=="" goto :help
goto :unknown

:delegate
shift
"%PYTHON_BIN%" "%SERVICE_RUNNER%" %COMMAND% %*
exit /b %ERRORLEVEL%

:config
set "URL=http://localhost:8000/"
echo Opening %URL% in your browser...
start "" "%URL%"
exit /b 0

:help
echo Metadelphi CLI
echo.
echo Usage: metadelphi ^<command^>
echo.
echo Commands:
echo   start     Start the background Metadelphi service.
echo   stop      Stop the background Metadelphi service.
echo   restart   Restart the background Metadelphi service.
echo   status    Check whether the service is running.
echo   logs      Show the backend log (use -f to follow).
echo   config    Open the Metadelphi web UI in your browser.
echo   help      Show this help message.
echo.
echo Examples:
echo   metadelphi start
echo   metadelphi status
echo   metadelphi logs -f
exit /b 0

:unknown
echo Unknown command: %COMMAND%
echo Run 'metadelphi help' for usage.
exit /b 1
