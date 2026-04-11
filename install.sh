#!/bin/bash

# Metadelphi Installer Script for Unix (MacOS/Linux)
# This script sets up Metadelphi on your system

set -e

echo "======================================"
echo "  Metadelphi Installation Wizard"
echo "======================================"
echo ""

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="MacOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
else
    OS="Unix"
fi

echo "Detected OS: $OS"
echo ""

# Check for Python command (try python first, then python3)
echo "Checking Python installation..."
if command -v python &> /dev/null; then
    # Check if it's Python 3
    PYTHON_VERSION=$(python --version 2>&1 | grep -oP '(?<=Python )\d+' | head -1)
    if [ "$PYTHON_VERSION" -eq 3 ]; then
        PYTHON_CMD="python"
    else
        # python exists but is Python 2, try python3
        if command -v python3 &> /dev/null; then
            PYTHON_CMD="python3"
        else
            PYTHON_CMD=""
        fi
    fi
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD=""
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: Python 3 not found!"
    echo ""
    if [[ "$OS" == "MacOS" ]]; then
        echo "To install Python on MacOS:"
        echo "1. Install Homebrew (if not installed): https://brew.sh/"
        echo "2. Run: brew install python@3.11"
    else
        echo "To install Python on Linux:"
        echo "Run: sudo apt install python3.11 python3.11-venv python3-pip"
    fi
    echo ""
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

echo "Found Python $PYTHON_VERSION"

# Check if version is 3.10 or higher
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "ERROR: Python 3.10 or higher is required!"
    echo "Found: Python $PYTHON_VERSION"
    echo ""
    if [[ "$OS" == "MacOS" ]]; then
        echo "To upgrade Python on MacOS:"
        echo "Run: brew install python@3.11"
    else
        echo "To upgrade Python on Linux:"
        echo "Run: sudo apt install python3.11 python3.11-venv"
    fi
    echo ""
    exit 1
fi

echo "✓ Python version is compatible"
echo ""

# Navigate to script directory
cd "$(dirname "$0")"

# Check if virtual environment already exists
if [ -d ".venv" ]; then
    echo "Virtual environment already exists. Removing old environment..."
    rm -rf .venv
fi

# Create virtual environment
echo "Creating virtual environment..."
$PYTHON_CMD -m venv .venv

if [ ! -d ".venv" ]; then
    echo "ERROR: Failed to create virtual environment!"
    echo "Make sure python3-venv is installed:"
    if [[ "$OS" == "MacOS" ]]; then
        echo "It should be included with Python from Homebrew"
    else
        echo "Run: sudo apt install python3-venv"
    fi
    exit 1
fi

echo "✓ Virtual environment created"
echo ""

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet

echo ""
echo "Installing dependencies..."
echo "This may take a few minutes. Progress will be shown below:"
echo "-----------------------------------------------------------"
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to install dependencies!"
    echo "Please check your internet connection and try again."
    exit 1
fi

echo ""
echo "✓ Dependencies installed successfully"
echo ""

# Run configuration wizard
echo "Starting configuration wizard..."
echo "Please configure at least one API key to use Metadelphi"
echo ""
$PYTHON_CMD installer/config_wizard.py

if [ $? -ne 0 ]; then
    echo "Configuration wizard failed or was cancelled."
    echo "You can run it again later with: $PYTHON_CMD installer/config_wizard.py"
fi

echo ""

# Create desktop launcher
echo "Creating desktop launcher..."
$PYTHON_CMD installer/create_launcher.py

if [ $? -eq 0 ]; then
    echo "✓ Desktop launcher created"
else
    echo "Warning: Failed to create desktop launcher"
    echo "You can still launch Metadelphi by running: ./launcher.sh"
fi

echo ""
read -p "Enable Metadelphi auto-start at login? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Setting up Metadelphi auto-start service..."
    ./setup_service.sh || echo "Warning: Failed to enable auto-start. You can try again later with: ./setup_service.sh"
else
    echo "Auto-start not enabled."
    echo "You can enable it later by running: ./setup_service.sh"
fi

echo ""
echo "======================================"
echo "  Installation Complete!"
echo "======================================"
echo ""
echo "To start Metadelphi:"
if [[ "$OS" == "MacOS" ]]; then
    echo "  - Open Metadelphi from Launchpad or ~/Applications folder, or"
elif [[ "$OS" == "Linux" ]]; then
    echo "  - Use the desktop launcher, or"
fi
echo "  - Run: ./launcher.sh"
echo ""
echo "The application will open in your default browser at:"
echo "  http://localhost:8080/index.html"
echo "To enable auto-start later, run:"
echo "  ./setup_service.sh"
echo ""

# Ask if user wants to launch now
read -p "Would you like to launch Metadelphi now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Launching Metadelphi..."
    ./launcher.sh
fi
