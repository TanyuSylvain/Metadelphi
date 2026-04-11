#!/bin/bash

# Metadelphi Distribution Package Creator
# This script creates distribution packages for Windows and Unix systems

set -e

VERSION=${1:-"1.0.0"}
DIST_DIR="dist"

echo "======================================"
echo "  Metadelphi Distribution Creator"
echo "======================================"
echo ""
echo "Creating distribution packages for version v${VERSION}..."
echo ""

# Create dist directory
mkdir -p "$DIST_DIR"

# Get the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Files/directories to exclude
EXCLUDE_PATTERNS=(
    ".git"
    ".venv"
    "venv"
    "__pycache__"
    ".vscode"
    ".DS_Store"
    "*.pyc"
    "*.pyo"
    "*.db"
    ".env"
    "dist"
    "*.log"
    ".claude"
    "create_distribution.sh"
    "INSTALLATION_SYSTEM_SUMMARY.md"
)

# Build exclude arguments for tar/zip
TAR_EXCLUDES=""
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    TAR_EXCLUDES="$TAR_EXCLUDES --exclude=$pattern"
done

echo "Step 1: Creating Unix distribution package..."
echo "---------------------------------------"

# Create tarball for Unix (MacOS/Linux)
UNIX_PACKAGE="$DIST_DIR/Metadelphi-Installer-v${VERSION}.tar.gz"

tar -czf "$UNIX_PACKAGE" \
    $TAR_EXCLUDES \
    -C "$SCRIPT_DIR/.." \
    "$(basename "$SCRIPT_DIR")"

# Rename to remove parent directory structure
cd "$DIST_DIR"
tar -xzf "Metadelphi-Installer-v${VERSION}.tar.gz"
mv "$(basename "$SCRIPT_DIR")" "Metadelphi-Installer-v${VERSION}"
tar -czf "Metadelphi-Installer-v${VERSION}.tar.gz" "Metadelphi-Installer-v${VERSION}"
rm -rf "Metadelphi-Installer-v${VERSION}"
cd ..

echo "✓ Created: $UNIX_PACKAGE"
echo ""

echo "Step 2: Creating Windows distribution package..."
echo "---------------------------------------"

# Create temporary directory for Windows package
WIN_TEMP="$DIST_DIR/Metadelphi-Installer-v${VERSION}-Windows"
mkdir -p "$WIN_TEMP"

# Copy files excluding patterns
rsync -a \
    --exclude=.git \
    --exclude=.venv \
    --exclude=venv \
    --exclude=__pycache__ \
    --exclude=.vscode \
    --exclude=.DS_Store \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='*.db' \
    --exclude=.env \
    --exclude=dist \
    --exclude='*.log' \
    --exclude=.claude \
    --exclude=create_distribution.sh \
    --exclude=INSTALLATION_SYSTEM_SUMMARY.md \
    "$SCRIPT_DIR/" "$WIN_TEMP/"

# Create zip for Windows
cd "$DIST_DIR"
WIN_PACKAGE="Metadelphi-Installer-v${VERSION}-Windows.zip"
zip -r "$WIN_PACKAGE" "Metadelphi-Installer-v${VERSION}-Windows" > /dev/null

# Clean up temp directory
rm -rf "Metadelphi-Installer-v${VERSION}-Windows"
cd ..

echo "✓ Created: $DIST_DIR/$WIN_PACKAGE"
echo ""

# Calculate sizes
UNIX_SIZE=$(du -h "$DIST_DIR/Metadelphi-Installer-v${VERSION}.tar.gz" | cut -f1)
WIN_SIZE=$(du -h "$DIST_DIR/$WIN_PACKAGE" | cut -f1)

echo "======================================"
echo "  Distribution Packages Created!"
echo "======================================"
echo ""
echo "Unix Package:    $UNIX_PACKAGE ($UNIX_SIZE)"
echo "Windows Package: $DIST_DIR/$WIN_PACKAGE ($WIN_SIZE)"
echo ""
echo "Next steps:"
echo "1. Test the installation packages on clean VMs"
echo "2. Create a GitHub release with tag v${VERSION}"
echo "3. Upload both packages to the GitHub release"
echo ""
echo "To create a GitHub release:"
echo "  git tag -a v${VERSION} -m 'Release v${VERSION}'"
echo "  git push origin v${VERSION}"
echo ""
echo "Then upload the packages from the dist/ directory to GitHub."
echo ""
