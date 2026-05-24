#!/bin/bash

# Metadelphi Launcher Script
# This script starts the backend server, which also serves the built React frontend

cd "$(dirname "$0")"

# Detect Python command
if command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1)
    if [ "$PYTHON_VERSION" -eq 3 ]; then
        PYTHON_CMD="python"
    else
        PYTHON_CMD="python3"
    fi
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "Error: Python 3 not found!"
    exit 1
fi

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found!"
    echo "Please run the installer first: ./install.sh"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found!"
    echo "Please configure your API keys by copying .env.template to .env"
    echo "Opening configuration wizard..."
    .venv/bin/python installer/config_wizard.py
fi

if [ ! -f "frontend/dist-react/index.html" ]; then
    echo "Error: Built React frontend not found at frontend/dist-react/index.html"
    echo "Build it first with:"
    echo "  cd frontend-react && npm install && npm run build"
    exit 1
fi

open_browser() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open http://localhost:8000/
    else
        xdg-open http://localhost:8000/ 2>/dev/null || echo "Please open http://localhost:8000/ in your browser"
    fi
}

if .venv/bin/python service_runner.py status --quiet >/dev/null 2>&1; then
    echo "Metadelphi is already running in the background."
    open_browser
    exit 0
fi

# Cleanup function
cleanup() {
    echo "Stopping server..."
    kill $BACKEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Starting Metadelphi..."
echo "==================="

# Start backend server (also serves React frontend)
echo "Starting server on port 8000..."
.venv/bin/python -m backend.main &
BACKEND_PID=$!

# Wait for server to start
sleep 2

echo ""
echo "Metadelphi is running!"
echo "==================="
echo "App:         http://localhost:8000/"
echo "Backend API: http://localhost:8000/docs"
echo ""

# Open browser
open_browser

echo "Press Ctrl+C to stop the application"

# Wait for processes
wait
