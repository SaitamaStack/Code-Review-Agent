#!/bin/bash
# ============================================================================
# Build script for Code Review Agent (Linux/macOS)
# 
# This script builds a standalone executable using PyInstaller
# 
# Prerequisites:
#   - Python 3.8+ installed
#   - Virtual environment activated (recommended)
#   - pip install pyinstaller
# 
# Usage:
#   chmod +x build.sh
#   ./build.sh
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "============================================"
echo -e "${BLUE} Code Review Agent - Build Script${NC}"
echo "============================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python 3 is not installed${NC}"
    echo "Please install Python 3.8+ from https://python.org"
    exit 1
fi

echo -e "${GREEN}[1/5]${NC} Checking Python version..."
python3 --version

# Determine pip command
PIP_CMD="pip3"
if ! command -v pip3 &> /dev/null; then
    PIP_CMD="pip"
fi

# Check if PyInstaller is installed
if ! $PIP_CMD show pyinstaller &> /dev/null; then
    echo ""
    echo -e "${GREEN}[2/5]${NC} Installing PyInstaller..."
    $PIP_CMD install pyinstaller
else
    echo -e "${GREEN}[2/5]${NC} PyInstaller is already installed"
fi

# Install project dependencies
echo ""
echo -e "${GREEN}[3/5]${NC} Installing project dependencies..."
$PIP_CMD install -r requirements.txt

# Clean previous builds
echo ""
echo -e "${GREEN}[4/5]${NC} Cleaning previous builds..."
rm -rf build/ dist/

# Run PyInstaller
echo ""
echo -e "${GREEN}[5/5]${NC} Building executable with PyInstaller..."
echo "This may take a few minutes..."
echo ""
pyinstaller code_review_agent.spec --clean --noconfirm

if [ $? -ne 0 ]; then
    echo ""
    echo "============================================"
    echo -e "${RED}[ERROR] Build failed!${NC}"
    echo "============================================"
    echo ""
    echo "Common issues:"
    echo "  - Missing dependencies: pip install -r requirements.txt"
    echo "  - tkinter not installed: sudo apt install python3-tk (Ubuntu/Debian)"
    echo "  - Permission denied: Check folder permissions"
    echo ""
    exit 1
fi

echo ""
echo "============================================"
echo -e "${GREEN} Build Complete!${NC}"
echo "============================================"
echo ""
echo "Executable location:"
echo "  dist/CodeReviewAgent"
echo ""
echo "To run the application:"
echo "  1. Make sure Ollama is installed and running"
echo "  2. Pull required model: ollama pull qwen3:14b"
echo "  3. Run: ./dist/CodeReviewAgent"
echo ""

# Make executable (just in case)
chmod +x dist/CodeReviewAgent 2>/dev/null || true

# Platform-specific notes
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${YELLOW}macOS Note:${NC}"
    echo "  You may need to allow the app in System Preferences > Security & Privacy"
    echo "  if Gatekeeper blocks it on first run."
    echo ""
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -e "${YELLOW}Linux Note:${NC}"
    echo "  If tkinter is missing, install with:"
    echo "    Ubuntu/Debian: sudo apt install python3-tk"
    echo "    Fedora: sudo dnf install python3-tkinter"
    echo "    Arch: sudo pacman -S tk"
    echo ""
fi

echo "============================================"
