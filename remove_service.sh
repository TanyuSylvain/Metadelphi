#!/bin/bash

set -e

cd "$(dirname "$0")"

APP_DIR="$(pwd)"
PYTHON_BIN="$APP_DIR/.venv/bin/python"
SERVICE_SCRIPT="$APP_DIR/service_runner.py"
SERVICE_NAME="metadelphi"

if [[ "$OSTYPE" == linux* ]]; then
    UNIT_FILE="$HOME/.config/systemd/user/$SERVICE_NAME.service"
    LEGACY_UNIT_FILE="$HOME/.config/systemd/user/unifyllm.service"

    if command -v systemctl >/dev/null 2>&1; then
        systemctl --user disable --now "$SERVICE_NAME.service" >/dev/null 2>&1 || true
        systemctl --user disable --now "unifyllm.service" >/dev/null 2>&1 || true
    fi

    rm -f "$UNIT_FILE"
    rm -f "$LEGACY_UNIT_FILE"

    if command -v systemctl >/dev/null 2>&1; then
        systemctl --user daemon-reload >/dev/null 2>&1 || true
    fi

    if [ -x "$PYTHON_BIN" ] && [ -f "$SERVICE_SCRIPT" ]; then
        "$PYTHON_BIN" "$SERVICE_SCRIPT" stop >/dev/null 2>&1 || true
    fi

    echo "Metadelphi auto-start service has been removed."
    exit 0
fi

if [[ "$OSTYPE" == darwin* ]]; then
    PLIST_FILE="$HOME/Library/LaunchAgents/com.metadelphi.service.plist"
    LEGACY_PLIST_FILE="$HOME/Library/LaunchAgents/com.unifyllm.service.plist"
    USER_ID="$(id -u)"

    launchctl bootout "gui/$USER_ID" "$PLIST_FILE" >/dev/null 2>&1 || true
    launchctl bootout "gui/$USER_ID" "$LEGACY_PLIST_FILE" >/dev/null 2>&1 || true
    rm -f "$PLIST_FILE"
    rm -f "$LEGACY_PLIST_FILE"

    if [ -x "$PYTHON_BIN" ] && [ -f "$SERVICE_SCRIPT" ]; then
        "$PYTHON_BIN" "$SERVICE_SCRIPT" stop >/dev/null 2>&1 || true
    fi

    echo "Metadelphi LaunchAgent has been removed."
    exit 0
fi

echo "Error: Unsupported Unix platform for service removal."
exit 1
