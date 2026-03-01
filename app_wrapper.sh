#!/bin/bash
#
# Proper macOS App Bundle Wrapper for VVV Token Watch
# This script handles the environment setup when launching from Finder
#

# Get the directory where this script is located (inside the app bundle)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESOURCES_DIR="$(cd "$SCRIPT_DIR/../Resources" && pwd)"

# Change to the Resources directory (where bundled files are)
cd "$RESOURCES_DIR"

# Set environment variables
export PYTHONPATH="$RESOURCES_DIR:$PYTHONPATH"

# Create logs directory
mkdir -p "$HOME/Library/Logs/VVV-Token-Watch"

# Log startup
exec >> "$HOME/Library/Logs/VVV-Token-Watch/startup.log" 2>&1
echo "=== VVV Token Watch Startup ==="
echo "Date: $(date)"
echo "Script dir: $SCRIPT_DIR"
echo "Resources dir: $RESOURCES_DIR"
echo "Working dir: $(pwd)"
echo "Python: $(which python3)"
echo ""

# Run the actual Python executable
exec "$SCRIPT_DIR/VVV Token Watch" "$@"
