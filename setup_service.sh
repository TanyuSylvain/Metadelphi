#!/bin/bash

set -e

cd "$(dirname "$0")"

APP_DIR="$(pwd)"
PYTHON_BIN="$APP_DIR/.venv/bin/python"
SERVICE_SCRIPT="$APP_DIR/service_runner.py"
SERVICE_NAME="metadelphi"

xml_escape() {
    printf '%s' "$1" | sed \
        -e 's/&/\&amp;/g' \
        -e 's/</\&lt;/g' \
        -e 's/>/\&gt;/g' \
        -e 's/"/\&quot;/g' \
        -e "s/'/\&apos;/g"
}

if [ ! -x "$PYTHON_BIN" ]; then
    echo "Error: Virtual environment not found at $PYTHON_BIN"
    echo "Please run ./install.sh first."
    exit 1
fi

if [ ! -f "$SERVICE_SCRIPT" ]; then
    echo "Error: Service runner not found at $SERVICE_SCRIPT"
    exit 1
fi

if [[ "$OSTYPE" == linux* ]]; then
    if ! command -v systemctl >/dev/null 2>&1; then
        echo "Error: systemctl is not available on this Linux system."
        exit 1
    fi

    if ! systemctl --user show-environment >/dev/null 2>&1; then
        echo "Error: user-level systemd services are not available in this session."
        echo "Auto-start requires systemd --user support."
        exit 1
    fi

    UNIT_DIR="$HOME/.config/systemd/user"
    UNIT_FILE="$UNIT_DIR/$SERVICE_NAME.service"
    LEGACY_UNIT_FILE="$UNIT_DIR/unifyllm.service"
    mkdir -p "$UNIT_DIR"

    systemctl --user disable --now "unifyllm.service" >/dev/null 2>&1 || true
    rm -f "$LEGACY_UNIT_FILE"

    cat > "$UNIT_FILE" <<EOF
[Unit]
Description=Metadelphi background service
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart="$PYTHON_BIN" "$SERVICE_SCRIPT" run
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

    systemctl --user daemon-reload
    systemctl --user enable --now "$SERVICE_NAME.service"

    echo "Metadelphi auto-start service has been enabled."
    echo "Status: systemctl --user status $SERVICE_NAME.service"
    echo "Disable later with: ./remove_service.sh"
    exit 0
fi

if [[ "$OSTYPE" == darwin* ]]; then
    PLIST_DIR="$HOME/Library/LaunchAgents"
    PLIST_FILE="$PLIST_DIR/com.metadelphi.service.plist"
    LEGACY_PLIST_FILE="$PLIST_DIR/com.unifyllm.service.plist"
    LOG_DIR="$HOME/Library/Logs/Metadelphi"
    USER_ID="$(id -u)"
    APP_DIR_ESCAPED="$(xml_escape "$APP_DIR")"
    PYTHON_BIN_ESCAPED="$(xml_escape "$PYTHON_BIN")"
    SERVICE_SCRIPT_ESCAPED="$(xml_escape "$SERVICE_SCRIPT")"
    LOG_DIR_ESCAPED="$(xml_escape "$LOG_DIR")"

    mkdir -p "$PLIST_DIR"
    mkdir -p "$LOG_DIR"

    launchctl bootout "gui/$USER_ID" "$LEGACY_PLIST_FILE" >/dev/null 2>&1 || true
    rm -f "$LEGACY_PLIST_FILE"

    cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.metadelphi.service</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN_ESCAPED</string>
        <string>$SERVICE_SCRIPT_ESCAPED</string>
        <string>run</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$APP_DIR_ESCAPED</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>$LOG_DIR_ESCAPED/launchagent.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR_ESCAPED/launchagent-error.log</string>
</dict>
</plist>
EOF

    plutil -lint "$PLIST_FILE" >/dev/null

    launchctl bootout "gui/$USER_ID" "$PLIST_FILE" >/dev/null 2>&1 || true
    launchctl bootstrap "gui/$USER_ID" "$PLIST_FILE"

    echo "Metadelphi LaunchAgent has been enabled."
    echo "Disable later with: ./remove_service.sh"
    exit 0
fi

echo "Error: Unsupported Unix platform for service setup."
exit 1
