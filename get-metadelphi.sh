#!/usr/bin/env bash
# Metadelphi one-line installer bootstrap.
# This script is intended to be piped to bash from raw.githubusercontent.com:
#   curl -fsSL https://raw.githubusercontent.com/TanyuSylvain/metadelphi/main/get-metadelphi.sh | bash

set -e

# Repository to install from. Override these for testing or forks.
: "${METADELPHI_REPO_OWNER:=TanyuSylvain}"
: "${METADELPHI_REPO_NAME:=metadelphi}"
: "${METADELPHI_VERSION:=latest}"

REPO="${METADELPHI_REPO_OWNER}/${METADELPHI_REPO_NAME}"

# Detect OS
OS="linux"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    echo "For Windows, please use get-metadelphi.bat instead."
    exit 1
fi

# Default install directory
if [[ "$OS" == "macos" ]]; then
    INSTALL_DIR="${METADELPHI_INSTALL_DIR:-$HOME/Applications/Metadelphi}"
else
    INSTALL_DIR="${METADELPHI_INSTALL_DIR:-$HOME/.metadelphi}"
fi

# Determine which download tool is available
if command -v curl >/dev/null 2>&1; then
    DOWNLOADER="curl -fsSL"
elif command -v wget >/dev/null 2>&1; then
    DOWNLOADER="wget -qO-"
else
    echo "Error: curl or wget is required to download Metadelphi."
    exit 1
fi

echo "======================================"
echo "  Metadelphi Remote Installer"
echo "======================================"
echo ""
echo "Repository:  $REPO"
echo "Version:     $METADELPHI_VERSION"
echo "OS:          $OS"
echo "Install dir: $INSTALL_DIR"
echo ""

# Resolve version
if [[ "$METADELPHI_VERSION" == "latest" ]]; then
    echo "Resolving latest release..."
    RELEASE_URL="https://api.github.com/repos/$REPO/releases/latest"
    METADELPHI_VERSION=$($DOWNLOADER "$RELEASE_URL" | grep '"tag_name":' | sed -E 's/.*"tag_name": *"v?([^"]+)".*/\1/')
    if [[ -z "$METADELPHI_VERSION" ]]; then
        echo "Error: Could not determine the latest release version."
        exit 1
    fi
    echo "Latest version: v$METADELPHI_VERSION"
fi

VERSION_TAG="v${METADELPHI_VERSION#v}"
ARCHIVE_NAME="Metadelphi-Installer-${VERSION_TAG}.tar.gz"
DOWNLOAD_URL="${METADELPHI_DOWNLOAD_URL:-https://github.com/$REPO/releases/download/${VERSION_TAG}/${ARCHIVE_NAME}}"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

echo ""
echo "Downloading $ARCHIVE_NAME..."
$DOWNLOADER "$DOWNLOAD_URL" -o "$TMP_DIR/$ARCHIVE_NAME"

echo "Extracting archive..."
tar -xzf "$TMP_DIR/$ARCHIVE_NAME" -C "$TMP_DIR"

EXTRACTED_DIR="$TMP_DIR/Metadelphi-Installer-${VERSION_TAG}"
if [ ! -d "$EXTRACTED_DIR" ]; then
    echo "Error: Expected extracted directory not found: $EXTRACTED_DIR"
    exit 1
fi

echo "Installing Metadelphi to $INSTALL_DIR..."
if [ -d "$INSTALL_DIR" ]; then
    echo "Existing installation found. Removing..."
    rm -rf "$INSTALL_DIR"
fi
mkdir -p "$(dirname "$INSTALL_DIR")"
mv "$EXTRACTED_DIR" "$INSTALL_DIR"

echo ""
echo "Running local installer..."
cd "$INSTALL_DIR"
./install.sh

echo ""
echo "======================================"
echo "  Installation Complete!"
echo "======================================"
echo ""
echo "Metadelphi is installed at: $INSTALL_DIR"
echo ""
echo "To start Metadelphi, open a new terminal and run:"
echo "  metadelphi start"
echo ""
echo "Then open http://localhost:8000/ and click 'Open Configuration'"
echo "to add your API keys."
echo ""
