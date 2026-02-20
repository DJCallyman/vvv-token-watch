#!/bin/bash
# Diagnostic script for VVV Token Watch macOS app

echo "=== VVV Token Watch Diagnostic Tool ==="
echo ""

# Check if app exists
if [ ! -d "dist/VVV Token Watch.app" ]; then
    echo "❌ App not found at dist/VVV Token Watch.app"
    echo "Please build the app first with: ./build_macos.sh"
    exit 1
fi

echo "✅ App bundle found"
echo ""

# Check app structure
echo "=== App Structure ==="
echo "Executable:"
ls -la "dist/VVV Token Watch.app/Contents/MacOS/"
echo ""
echo "Resources:"
ls -la "dist/VVV Token Watch.app/Contents/Resources/" 2>/dev/null || echo "No Resources directory"
echo ""

# Try to run the executable directly to see errors
echo "=== Attempting to Run Executable ==="
echo "Running: ./dist/VVV\ Token\ Watch.app/Contents/MacOS/VVV\ Token\ Watch"
echo ""
echo "--- Output ---"
"./dist/VVV Token Watch.app/Contents/MacOS/VVV Token Watch" 2>&1 | head -50
echo "--- End Output ---"
echo ""

# Check for common issues
echo "=== Checking for Common Issues ==="

# Check if .env.example is bundled
if [ -f "dist/VVV Token Watch.app/Contents/Resources/.env.example" ]; then
    echo "✅ .env.example bundled"
else
    echo "⚠️  .env.example not found in bundle"
fi

# Check if src directory is bundled
if [ -d "dist/VVV Token Watch.app/Contents/Resources/src" ]; then
    echo "✅ src directory bundled"
else
    echo "⚠️  src directory not found in bundle"
fi

# Check entitlements
echo ""
echo "=== Entitlements ==="
codesign -d --entitlements - "dist/VVV Token Watch.app" 2>&1 || echo "Not signed (expected for unsigned builds)"

echo ""
echo "=== Console Logs (last 20 lines) ==="
log show --predicate 'process == "VVV Token Watch"' --last 1m 2>/dev/null | tail -20 || echo "No recent logs found"

echo ""
echo "=== Diagnostic Complete ==="
echo ""
echo "To see detailed error messages, run:"
echo "  ./dist/VVV\ Token\ Watch.app/Contents/MacOS/VVV\ Token\ Watch"
