@echo off
REM Metadelphi one-line installer bootstrap for Windows.
REM Download this file and run it, or use a PowerShell one-liner.

setlocal EnableDelayedExpansion

REM Repository to install from. Override these for testing or forks.
if not defined METADELPHI_REPO_OWNER set "METADELPHI_REPO_OWNER=TanyuSylvain"
if not defined METADELPHI_REPO_NAME set "METADELPHI_REPO_NAME=metadelphi"
if not defined METADELPHI_VERSION set "METADELPHI_VERSION=latest"
if not defined METADELPHI_INSTALL_DIR set "METADELPHI_INSTALL_DIR=%LOCALAPPDATA%\Metadelphi"

set "REPO=%METADELPHI_REPO_OWNER%/%METADELPHI_REPO_NAME%"
set "INSTALL_DIR=%METADELPHI_INSTALL_DIR%"

echo ======================================
echo   Metadelphi Remote Installer
echo ======================================
echo.
echo Repository:  %REPO%
echo Version:     %METADELPHI_VERSION%
echo Install dir: %INSTALL_DIR%
echo.

REM Resolve version
if /i "%METADELPHI_VERSION%"=="latest" (
    echo Resolving latest release...
    for /f "usebackq tokens=*" %%a in (`powershell -NoProfile -Command "(Invoke-RestMethod -Uri 'https://api.github.com/repos/%REPO%/releases/latest').tag_name"`) do set "VERSION_TAG=%%a"
    if "!VERSION_TAG!"=="" (
        echo Error: Could not determine the latest release version.
        exit /b 1
    )
    echo Latest version: !VERSION_TAG!
) else (
    set "VERSION_TAG=v%METADELPHI_VERSION%"
    if "!VERSION_TAG:~0,1!"=="vv" set "VERSION_TAG=!VERSION_TAG:~1!"
)

set "ARCHIVE_NAME=Metadelphi-Installer-!VERSION_TAG!-Windows.zip"
if defined METADELPHI_DOWNLOAD_URL (
    set "DOWNLOAD_URL=%METADELPHI_DOWNLOAD_URL%"
) else (
    set "DOWNLOAD_URL=https://github.com/%REPO%/releases/download/!VERSION_TAG!/!ARCHIVE_NAME!"
)
set "TMP_DIR=%TEMP%\metadelphi-installer"

if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
mkdir "%TMP_DIR%"

echo.
echo Downloading !ARCHIVE_NAME!...
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%TMP_DIR%\%ARCHIVE_NAME%'"
if errorlevel 1 (
    echo Error: Download failed.
    exit /b 1
)

echo Extracting archive...
powershell -NoProfile -Command "Expand-Archive -Path '%TMP_DIR%\%ARCHIVE_NAME%' -DestinationPath '%TMP_DIR%' -Force"

set "EXTRACTED_DIR=%TMP_DIR%\Metadelphi-Installer-!VERSION_TAG!-Windows"
if not exist "%EXTRACTED_DIR%" (
    echo Error: Expected extracted directory not found: %EXTRACTED_DIR%
    exit /b 1
)

echo Installing Metadelphi to %INSTALL_DIR%...
if exist "%INSTALL_DIR%" (
    echo Existing installation found. Removing...
    rmdir /s /q "%INSTALL_DIR%"
)
mkdir "%INSTALL_DIR%"
xcopy /E /I /Q "%EXTRACTED_DIR%\*" "%INSTALL_DIR%"

echo.
echo Running local installer...
cd /d "%INSTALL_DIR%"
call install.bat

echo.
echo ======================================
echo   Installation Complete!
echo ======================================
echo.
echo Metadelphi is installed at: %INSTALL_DIR%
echo.
echo To start Metadelphi, open a new Command Prompt and run:
echo   metadelphi start
echo.
echo Then open http://localhost:8000/ and click 'Open Configuration'
echo to add your API keys.
echo.

pause
