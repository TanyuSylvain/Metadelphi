#!/bin/bash

cd "$(dirname "$0")"

cleanup() {
    echo "Stopping server..."
    kill $BACKEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Starting server on port 8000..."
python -m backend.main &
BACKEND_PID=$!

echo ""
echo "App:         http://localhost:8000/"
echo "Backend API: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the application"

wait
