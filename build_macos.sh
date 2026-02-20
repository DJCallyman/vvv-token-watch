#!/bin/bash
#
# Build script for VVV Token Watch macOS app
# Creates a signed, notarized application bundle
#

set -e

echo "============================================"
echo "VVV Token Watch - macOS Build Script"
echo "============================================"

# Configuration
APP_NAME="VVV Token Watch"
BUNDLE_ID="com.djcallyman.vvvtokenwatch"
VERSION="1.0.0"
SPEC_FILE="VVV-Token-Watch.spec"
DIST_DIR="dist"
BUILD_DIR="build"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script must be run on macOS"
    exit 1
fi

# Check for required tools
print_status "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

if ! command -v pyinstaller &> /dev/null; then
    print_status "Installing PyInstaller..."
    pip3 install pyinstaller
fi

# Clean previous builds
print_status "Cleaning previous builds..."
rm -rf "$DIST_DIR" "$BUILD_DIR"

# Create assets directory if it doesn't exist
if [ ! -d "assets" ]; then
    mkdir -p assets
    print_warning "Created assets directory. Please add icon.icns file for custom app icon."
fi

# Install dependencies
print_status "Installing dependencies..."
pip3 install -r requirements.txt

# Build the app
print_status "Building application bundle..."
pyinstaller "$SPEC_FILE" --clean --noconfirm

# Check if build was successful
if [ ! -d "$DIST_DIR/$APP_NAME.app" ]; then
    print_error "Build failed - app bundle not found"
    exit 1
fi

print_status "Build completed successfully!"

# Code signing (optional - requires Apple Developer account)
if [ -n "$CODESIGN_IDENTITY" ]; then
    print_status "Signing application with identity: $CODESIGN_IDENTITY"
    codesign --force --deep --sign "$CODESIGN_IDENTITY" --entitlements entitlements.plist "$DIST_DIR/$APP_NAME.app"
    print_status "Application signed successfully"
else
    print_warning "No CODESIGN_IDENTITY set - application will be unsigned"
    print_warning "To sign, run: export CODESIGN_IDENTITY='Developer ID Application: Your Name'"
fi

# Create DMG (optional)
if command -v create-dmg &> /dev/null; then
    print_status "Creating DMG installer..."
    
    DMG_NAME="${APP_NAME}-${VERSION}.dmg"
    
    create-dmg \
        --volname "$APP_NAME" \
        --volicon "assets/icon.icns" \
        --window-pos 200 120 \
        --window-size 800 400 \
        --icon-size 100 \
        --icon "$APP_NAME.app" 200 190 \
        --hide-extension "$APP_NAME.app" \
        --app-drop-link 600 185 \
        "$DIST_DIR/$DMG_NAME" \
        "$DIST_DIR/$APP_NAME.app"
    
    print_status "DMG created: $DIST_DIR/$DMG_NAME"
else
    print_warning "create-dmg not installed - skipping DMG creation"
    print_warning "Install with: brew install create-dmg"
fi

# Verify the app
print_status "Verifying application bundle..."
if [ -d "$DIST_DIR/$APP_NAME.app/Contents/MacOS/$APP_NAME" ]; then
    print_status "✓ Executable found"
fi

if [ -f "$DIST_DIR/$APP_NAME.app/Contents/Info.plist" ]; then
    print_status "✓ Info.plist found"
fi

echo ""
echo "============================================"
echo "Build Summary"
echo "============================================"
echo "App Bundle: $DIST_DIR/$APP_NAME.app"
echo "Version: $VERSION"
echo "Bundle ID: $BUNDLE_ID"
echo ""

if [ -n "$CODESIGN_IDENTITY" ]; then
    echo "Signed: ✓"
    codesign -dv "$DIST_DIR/$APP_NAME.app" 2>&1 | grep -E "(Authority|Signature)" || true
else
    echo "Signed: ✗ (unsigned)"
fi

if [ -f "$DIST_DIR/$DMG_NAME" ]; then
    echo "DMG: ✓ $DMG_NAME"
else
    echo "DMG: ✗ (not created)"
fi

echo ""
echo "To run the app:"
echo "  open \"$DIST_DIR/$APP_NAME.app\""
echo ""
echo "To distribute:"
echo "  - Zip the .app bundle: zip -r '$APP_NAME.app.zip' '$DIST_DIR/$APP_NAME.app'"
echo "  - Or use the DMG file if created"
echo ""

print_status "Build complete!"
