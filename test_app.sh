#!/bin/bash
#
# Test script for VVV Token Watch macOS app
#

echo "=== Testing VVV Token Watch App ==="
echo ""

# Kill any existing instances
killall VVVTokenWatch 2>/dev/null
sleep 1

# Open the app
echo "Opening app..."
open "dist/VVV Token Watch.app"

# Wait for startup
echo "Waiting 5 seconds for app to start..."
sleep 5

# Check if process is running
if pgrep -f "VVVTokenWatch" > /dev/null; then
    echo "✅ App process is running"
    
    # Check if window is visible
    osascript << 'APPLESCRIPT' 2>/dev/null
        tell application "System Events"
            if exists (window 1 of application process "VVVTokenWatch") then
                return "Window exists"
            else
                return "No window found"
            end if
        end tell
APPLESCRIPT
    
    # Check dock
    osascript << 'APPLESCRIPT' 2>/dev/null
        tell application "System Events"
            if exists (application process "VVVTokenWatch") then
                return "App in dock"
            else
                return "App not in dock"
            end if
        end tell
APPLESCRIPT
    
else
    echo "❌ App process NOT running"
    echo ""
    echo "Checking logs..."
    ls -la ~/Library/Logs/VVV-Token-Watch/ 2>/dev/null || echo "No logs directory"
fi

echo ""
echo "=== Test Complete ==="
