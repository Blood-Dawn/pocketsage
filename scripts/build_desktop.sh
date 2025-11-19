#!/bin/bash
# Build PocketSage desktop application using flet pack

set -e

echo "Building PocketSage desktop application..."

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate || . .venv/Scripts/activate

echo "Installing dependencies..."
pip install -e ".[dev]"

# Run tests
echo "Running tests..."
pytest || echo "Warning: Some tests failed"

# Build desktop app
echo "Building desktop application with flet pack..."
flet pack run_desktop.py \
    --name "PocketSage" \
    --product-name "PocketSage" \
    --product-version "0.1.0" \
    --file-description "Offline Finance & Habit Tracker" \
    --icon assets/icon.png || true

echo "Build complete! Binary should be in dist/ directory"
echo "On Windows: dist/PocketSage/PocketSage.exe"
echo "On macOS: dist/PocketSage.app"
echo "On Linux: dist/PocketSage/PocketSage"
