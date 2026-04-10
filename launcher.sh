#!/bin/bash

# UnifyLLM Launcher Script
# This script starts both the backend and frontend servers

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
    $PYTHON_CMD installer/config_wizard.py
fi

open_browser() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open http://localhost:8080/index.html
    else
        xdg-open http://localhost:8080/index.html 2>/dev/null || echo "Please open http://localhost:8080/index.html in your browser"
    fi
}

if $PYTHON_CMD service_runner.py status --quiet >/dev/null 2>&1; then
    echo "UnifyLLM is already running in the background."
    open_browser
    exit 0
fi

# Cleanup function
cleanup() {
    echo "Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Starting UnifyLLM..."
echo "==================="

# Start backend server
echo "Starting backend server on port 8000..."
$PYTHON_CMD -m backend.main &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start frontend server
echo "Starting frontend server on port 8080..."
$PYTHON_CMD -m http.server 8080 --directory frontend/src &
FRONTEND_PID=$!

# Wait a bit more for frontend to start
sleep 1

echo ""
echo "UnifyLLM is running!"
echo "==================="
echo "Backend API: http://localhost:8000"
echo "Frontend:    http://localhost:8080/index.html"
echo ""

# Open browser
open_browser

echo "Press Ctrl+C to stop the application"

# Wait for processes
wait
