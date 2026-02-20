#!/bin/bash
#
# Launch VVV Token Watch with error logging
# Use this wrapper to see errors when double-clicking
#

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="VVVTokenWatch"
EXECUTABLE="$SCRIPT_DIR/$APP_NAME"

# Create log directory
LOG_DIR="$HOME/Library/Logs/VVV-Token-Watch"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/launch_$(date +%Y%m%d_%H%M%S).log"

echo "=== VVV Token Watch Launch ===" > "$LOG_FILE"
echo "Date: $(date)" >> "$LOG_FILE"
echo "Executable: $EXECUTABLE" >> "$LOG_FILE"
echo "Working Directory: $(pwd)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Launch the app and capture all output
exec "$EXECUTABLE" >> "$LOG_FILE" 2>&1
