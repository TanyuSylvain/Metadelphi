#!/bin/bash

# Metadelphi Launcher Script
# Starts the background service (if not running) and opens the web UI.

cd "$(dirname "$0")"

open_browser() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open http://localhost:8000/
    else
        xdg-open http://localhost:8000/ 2>/dev/null || echo "Please open http://localhost:8000/ in your browser"
    fi
}

PYTHON_BIN=".venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "Error: Virtual environment not found!"
    echo "Please run the installer first: ./install.sh"
    exit 1
fi

if [ ! -f "frontend/dist-react/index.html" ]; then
    echo "Error: Built React frontend not found at frontend/dist-react/index.html"
    echo "Build it first with:"
    echo "  cd frontend-react && npm install && npm run build"
    exit 1
fi

if $PYTHON_BIN service_runner.py status --quiet >/dev/null 2>&1; then
    echo "Metadelphi is already running in the background."
    open_browser
    exit 0
fi

echo "Starting Metadelphi..."
if $PYTHON_BIN service_runner.py start; then
    sleep 1
    open_browser
    echo ""
    echo "Metadelphi is running at http://localhost:8000/"
    echo "Use 'metadelphi stop' to stop the service."
else
    echo "Failed to start Metadelphi."
    exit 1
fi
