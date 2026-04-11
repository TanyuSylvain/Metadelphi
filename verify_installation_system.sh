#!/bin/bash

# Metadelphi Installation System Verification Script
# This script verifies that all installation components are properly set up

echo "======================================"
echo "  Metadelphi Installation Verification"
echo "======================================"
echo ""

ERRORS=0
WARNINGS=0

# Function to check if file exists
check_file() {
    if [ -f "$1" ]; then
        echo "✓ $1"
        return 0
    else
        echo "✗ $1 - MISSING"
        ((ERRORS++))
        return 1
    fi
}

# Function to check if file is executable
check_executable() {
    if [ -x "$1" ]; then
        echo "✓ $1 (executable)"
        return 0
    else
        echo "⚠ $1 - NOT EXECUTABLE"
        ((WARNINGS++))
        return 1
    fi
}

echo "Checking core installation files..."
echo "-----------------------------------"
check_file "requirements.txt"
check_file ".env.template"
check_file "LICENSE.txt"
echo ""

echo "Checking launcher scripts..."
echo "-----------------------------------"
check_executable "launcher.sh"
check_file "launcher.bat"
echo ""

echo "Checking installer scripts..."
echo "-----------------------------------"
check_executable "install.sh"
check_file "install.bat"
echo ""

echo "Checking installer utilities..."
echo "-----------------------------------"
check_executable "installer/config_wizard.py"
check_executable "installer/create_launcher.py"
check_executable "installer/create_shortcut.py"
check_executable "installer/generate_icons.py"
echo ""

echo "Checking icon files..."
echo "-----------------------------------"
check_file "installer/icon.png"
check_file "installer/icon.ico"
echo ""

echo "Checking source directories..."
echo "-----------------------------------"
if [ -d "backend" ]; then
    echo "✓ backend/ directory"
else
    echo "✗ backend/ directory - MISSING"
    ((ERRORS++))
fi

if [ -d "frontend" ]; then
    echo "✓ frontend/ directory"
else
    echo "✗ frontend/ directory - MISSING"
    ((ERRORS++))
fi
echo ""

echo "Checking Python requirements..."
echo "-----------------------------------"
# Check for python or python3
if command -v python &> /dev/null; then
    PYTHON_CMD="python"
    PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
else
    PYTHON_CMD=""
    PYTHON_VERSION=""
fi

if [ -n "$PYTHON_CMD" ]; then
    echo "✓ Python found: $PYTHON_VERSION (as $PYTHON_CMD)"

    # Check version
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        echo "✓ Python version is 3.10 or higher"
    else
        echo "⚠ Python version should be 3.10 or higher (found $PYTHON_VERSION)"
        ((WARNINGS++))
    fi
else
    echo "⚠ Python 3 not found (installer will handle this)"
    ((WARNINGS++))
fi
echo ""

echo "Checking Tkinter (for GUI configuration wizard)..."
echo "-----------------------------------"
if [ -n "$PYTHON_CMD" ]; then
    if $PYTHON_CMD -c "import tkinter" 2>/dev/null; then
        echo "✓ Tkinter is available"
    else
        echo "⚠ Tkinter not available (GUI wizard may not work)"
        echo "  Install with: sudo apt install python3-tk (Linux)"
        ((WARNINGS++))
    fi
else
    echo "⚠ Cannot check Tkinter (Python not found)"
    ((WARNINGS++))
fi
echo ""

echo "======================================"
echo "  Verification Summary"
echo "======================================"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "✓ All checks passed!"
    echo ""
    echo "The installation system is ready for distribution."
    echo ""
    echo "Next steps:"
    echo "1. Test the installation: ./install.sh"
    echo "2. Create distribution packages: ./create_distribution.sh"
    echo "3. Test packages on clean VMs for each platform"
    echo ""
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo "⚠ Verification completed with $WARNINGS warning(s)"
    echo ""
    echo "The installation system should work, but please review the warnings above."
    echo ""
    exit 0
else
    echo "✗ Verification failed with $ERRORS error(s) and $WARNINGS warning(s)"
    echo ""
    echo "Please fix the errors above before proceeding."
    echo ""
    exit 1
fi
