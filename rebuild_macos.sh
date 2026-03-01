#!/bin/bash
#
# Complete rebuild script with optimizations
#

set -e

echo "============================================"
echo "VVV Token Watch - Complete Rebuild"
echo "============================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect Python and virtual environment
if [ -d "venv" ]; then
    print_status "Using virtual environment..."
    PYTHON="venv/bin/python"
    PIP="venv/bin/pip"
    PYINSTALLER="venv/bin/pyinstaller"
    
    # Ensure PyInstaller is installed in venv
    if [ ! -f "$PYINSTALLER" ]; then
        print_status "Installing PyInstaller in virtual environment..."
        $PIP install pyinstaller
    fi
elif [ -d ".venv" ]; then
    print_status "Using .venv virtual environment..."
    PYTHON=".venv/bin/python"
    PIP=".venv/bin/pip"
    PYINSTALLER=".venv/bin/pyinstaller"
else
    print_warning "No virtual environment found, using system Python..."
    PYTHON="python3"
    PIP="pip3"
    PYINSTALLER="pyinstaller"
fi

print_status "Python: $PYTHON"
print_status "PyInstaller: $PYINSTALLER"

# Verify PySide6 is available
print_status "Checking PySide6 installation..."
$PYTHON -c "import PySide6; print(f'PySide6: {PySide6.__version__}')" || {
    print_error "PySide6 not found! Installing requirements..."
    $PIP install -r requirements.txt
}

# Step 1: Pre-build matplotlib font cache
print_status "Pre-building matplotlib font cache..."
$PYTHON << 'EOF'
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.figure()
plt.close()
print("Matplotlib cache built")
EOF

# Step 2: Clean previous builds
print_status "Cleaning previous builds..."
rm -rf dist build __pycache__
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Step 3: Check for .env file
if [ ! -f ".env" ]; then
    print_warning ".env file not found! Copying from example..."
    cp .env.example .env
    print_warning "Please edit .env file with your API keys"
fi

# Step 4: Build the app using the venv Python
print_status "Building macOS app bundle..."
$PYINSTALLER VVV-Token-Watch.spec --clean --noconfirm

# Step 5: Verify the build
print_status "Verifying build..."
if [ -f "dist/VVV Token Watch.app/Contents/MacOS/VVVTokenWatch" ]; then
    print_status "✓ Executable found"
else
    print_error "✗ Executable not found"
    exit 1
fi

if [ -d "dist/VVV Token Watch.app/Contents/MacOS/src" ]; then
    print_status "✓ Source files bundled"
else
    print_warning "⚠ Source files in different location (check Resources)"
fi

if [ -f "dist/VVV Token Watch.app/Contents/Resources/.env" ]; then
    print_status "✓ .env file bundled"
elif [ -f "dist/VVV Token Watch.app/Contents/Resources/.env.example" ]; then
    print_warning "⚠ Only .env.example bundled"
fi

# Step 6: Set permissions
print_status "Setting permissions..."
chmod +x "dist/VVV Token Watch.app/Contents/MacOS/VVVTokenWatch"

# Step 7: Quick test
echo ""
print_status "Testing app launch..."
timeout 5 ./dist/VVV\ Token\ Watch.app/Contents/MacOS/VVVTokenWatch 2>&1 | head -20 || true

# Show info
echo ""
echo "============================================"
echo "Build Complete!"
echo "============================================"
echo ""
echo "App: dist/VVV Token Watch.app"
echo ""
echo "To test:"
echo "  Terminal: ./dist/VVV\\ Token\\ Watch.app/Contents/MacOS/VVVTokenWatch"
echo "  Double-click: open \"dist/VVV Token Watch.app\""
echo ""
