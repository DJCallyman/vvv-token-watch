#!/bin/bash
#
# Debug build script for VVV Token Watch macOS app
# Builds with console output visible for debugging
#

set -e

echo "============================================"
echo "VVV Token Watch - Debug Build Script"
echo "============================================"

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "Error: This script must be run on macOS"
    exit 1
fi

# Create a debug version of the spec file
cat > VVV-Token-Watch-debug.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

# Get the project root
if getattr(sys, 'frozen', False):
    project_root = Path(sys.executable).parent
else:
    try:
        project_root = Path(__file__).parent
    except NameError:
        project_root = Path(os.getcwd())

# Determine which env files to bundle
bundle_datas = [
    ('src', 'src'),
    ('data', 'data'),
    ('.env.example', '.'),
]

if (project_root / '.env').exists():
    bundle_datas.append(('.env', '.'))

a = Analysis(
    ['run.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=bundle_datas,
    hiddenimports=[
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'requests',
        'urllib3',
        'matplotlib',
        'matplotlib.backends.backend_qt5agg',
        'tenacity',
        'python-dotenv',
        'venice-ai',
        'logging.handlers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'pytest',
        'pdb',
        'difflib',
        'wave',
        'tty',
        'pwd',
        'grp',
        '_pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

icon_path = None
if (project_root / 'assets' / 'icon.icns').exists():
    icon_path = str(project_root / 'assets' / 'icon.icns')

# DEBUG BUILD: console=True to see errors
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VVV Token Watch',
    debug=True,  # Enable debug mode
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # SHOW CONSOLE for debugging
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

app = BUNDLE(
    exe,
    name='VVV Token Watch Debug.app',
    icon=icon_path,
    bundle_identifier='com.djcallyman.vvvtokenwatch.debug',
    version='1.0.0',
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': 'False',
        'NSRequiresAquaSystemAppearance': 'False',
        'CFBundleDocumentTypes': [],
        'NSAppTransportSecurity': {
            'NSAllowsArbitraryLoads': True
        },
    },
)
EOF

echo "Building debug version with console output..."
pyinstaller VVV-Token-Watch-debug.spec --clean --noconfirm

echo ""
echo "============================================"
echo "Debug build complete!"
echo "============================================"
echo ""
echo "Test the debug build by double-clicking:"
echo "  dist/VVV Token Watch Debug.app"
echo ""
echo "A console window will appear showing any errors."
echo ""
echo "To test from terminal and see output:"
echo "  ./dist/VVV\ Token\ Watch\ Debug.app/Contents/MacOS/VVV\ Token\ Watch"
