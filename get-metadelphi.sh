#!/usr/bin/env bash
# Metadelphi one-line installer bootstrap.
# This script is intended to be piped to bash from raw.githubusercontent.com:
#   curl -fsSL https://raw.githubusercontent.com/TanyuSylvain/metadelphi/main/get-metadelphi.sh | bash
#
# Minimal requirements:
#   - bash
#   - Python 3.10 or newer
#   - Internet connectivity to GitHub
#   - curl or wget

set -euo pipefail

# Print an error message and exit.
fail() {
    printf '\n' >&2
    printf 'Error: %b\n' "$*" >&2
    exit 1
}

# Verify Python 3.10+ is available and export PYTHON_CMD.
require_python() {
    local cmd
    for cmd in python3 python; do
        if command -v "$cmd" >/dev/null 2>&1; then
            if "$cmd" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
                PYTHON_CMD="$cmd"
                return 0
            fi
        fi
    done
    return 1
}

# Verify we can reach GitHub.
check_internet() {
    local url="https://github.com"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSI "$url" >/dev/null 2>&1
    elif command -v wget >/dev/null 2>&1; then
        wget --spider -q "$url" >/dev/null 2>&1
    else
        return 1
    fi
}

# Download URL to a file, using curl or wget.
download_file() {
    local url="$1" output="$2"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$url" -o "$output"
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$output" "$url"
    else
        fail "curl or wget is required to download Metadelphi."
    fi
}

# Resolve the latest release version via the GitHub API.
resolve_latest_version() {
    local api_url="https://api.github.com/repos/$REPO/releases/latest"
    local response version

    if command -v curl >/dev/null 2>&1; then
        response=$(curl -fsSL "$api_url" 2>/dev/null || true)
    else
        response=$(wget -qO- "$api_url" 2>/dev/null || true)
    fi

    version=$(echo "$response" | grep '"tag_name":' | sed -E 's/.*"tag_name": *"v?([^"]+)".*/\1/' | head -n 1 || true)

    # If unauthenticated API calls are rate-limited, try with a token if available.
    if [[ -z "$version" && -n "${GITHUB_TOKEN:-}" ]] && command -v curl >/dev/null 2>&1; then
        response=$(curl -fsSL -H "Authorization: Bearer $GITHUB_TOKEN" "$api_url" 2>/dev/null || true)
        version=$(echo "$response" | grep '"tag_name":' | sed -E 's/.*"tag_name": *"v?([^"]+)".*/\1/' | head -n 1 || true)
    fi

    if [[ -z "$version" ]]; then
        if echo "$response" | grep -q "API rate limit exceeded" 2>/dev/null; then
            fail "GitHub API rate limit exceeded.\nSet the GITHUB_TOKEN environment variable, or specify a version with METADELPHI_VERSION."
        else
            fail "Could not determine the latest release version.\nCheck your internet connection or specify a version with METADELPHI_VERSION."
        fi
    fi

    echo "$version"
}

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
    echo "For Windows, please use get-metadelphi.bat instead." >&2
    exit 1
fi

# Default install directory
if [[ "$OS" == "macos" ]]; then
    INSTALL_DIR="${METADELPHI_INSTALL_DIR:-$HOME/Applications/Metadelphi}"
else
    INSTALL_DIR="${METADELPHI_INSTALL_DIR:-$HOME/.metadelphi}"
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

# Preflight checks: fail fast if minimal requirements are not met.
echo "Checking requirements..."
if ! require_python; then
    fail "Python 3.10 or newer is required but was not found.\nPlease install Python 3.10+ and try again."
fi
echo "  ✓ Python $("$PYTHON_CMD" --version 2>&1 | cut -d' ' -f2) found"

if ! check_internet; then
    fail "Internet connectivity check failed.\nPlease check your connection and try again."
fi
echo "  ✓ Internet connectivity confirmed"

if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    fail "curl or wget is required to download Metadelphi."
fi
echo "  ✓ Download tool available"

if ! command -v tar >/dev/null 2>&1; then
    fail "tar is required to extract the Metadelphi archive."
fi
echo "  ✓ tar available"
echo ""

# Resolve version
if [[ "$METADELPHI_VERSION" == "latest" ]]; then
    echo "Resolving latest release..."
    METADELPHI_VERSION=$(resolve_latest_version)
    echo "Latest version: v$METADELPHI_VERSION"
fi

VERSION_TAG="v${METADELPHI_VERSION#v}"
ARCHIVE_NAME="Metadelphi-Installer-${VERSION_TAG}.tar.gz"
DOWNLOAD_URL="${METADELPHI_DOWNLOAD_URL:-https://github.com/$REPO/releases/download/${VERSION_TAG}/${ARCHIVE_NAME}}"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "${TMP_DIR:-}"' EXIT

echo ""
echo "Downloading $ARCHIVE_NAME..."
download_file "$DOWNLOAD_URL" "$TMP_DIR/$ARCHIVE_NAME"

if [[ ! -s "$TMP_DIR/$ARCHIVE_NAME" ]]; then
    fail "Downloaded archive is empty. Please check your internet connection and try again."
fi

echo "Extracting archive..."
if ! tar -xzf "$TMP_DIR/$ARCHIVE_NAME" -C "$TMP_DIR"; then
    fail "Failed to extract archive. The downloaded file may be corrupted."
fi

EXTRACTED_DIR="$TMP_DIR/Metadelphi-Installer-${VERSION_TAG}"
if [ ! -d "$EXTRACTED_DIR" ]; then
    fail "Expected extracted directory not found: $EXTRACTED_DIR"
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
if [ ! -x "./install.sh" ]; then
    fail "Local installer (install.sh) not found in the downloaded archive."
fi

# If stdin is the pipe that fed this script, install.sh's interactive prompts
# would read EOF. Run it non-interactively so prompts default to "no".
if [ -t 0 ]; then
    ./install.sh
else
    ./install.sh < /dev/null
fi

echo ""
echo "======================================"
echo "  Installation Complete!"
echo "======================================"
echo ""
echo "Metadelphi is installed at: $INSTALL_DIR"
echo ""
echo "To start Metadelphi, open a new terminal and run:"
echo "  metadelphi"
echo ""
echo "Then open http://localhost:8000/ and click 'Open Configuration'"
echo "to add your API keys."
echo ""
