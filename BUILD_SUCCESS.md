# macOS App Build - Success Guide

## Build Status: ✅ WORKING

The macOS app bundle has been successfully built and tested!

### What Was Fixed

**Issue**: The app wasn't launching when double-clicked because PyInstaller was using the system Python instead of the virtual environment Python.

**Solution**: Updated the build script (`rebuild_macos.sh`) to:
1. Detect and use the virtual environment Python
2. Install PyInstaller in the venv if not present
3. Verify PySide6 is available before building

## How to Build

### Quick Build (Using Fixed Script)

```bash
# Run the rebuild script (uses venv automatically)
./rebuild_macos.sh
```

### Manual Build (If Needed)

```bash
# Activate virtual environment
source venv/bin/activate

# Build with venv Python
venv/bin/pyinstaller VVV-Token-Watch.spec --clean --noconfirm
```

## Test Results

✅ **Terminal Launch**: `./dist/VVV\ Token\ Watch.app/Contents/MacOS/VVVTokenWatch`
✅ **Double-Click Launch**: `open "dist/VVV Token Watch.app"`  
✅ **Dock Icon**: App appears in dock
✅ **Process**: Stays running (not crashing)

## App Location

After building:
```
dist/VVV Token Watch.app
```

## Distributing the App

### Method 1: Zip File (Easiest)
```bash
cd dist
zip -r "VVV Token Watch.zip" "VVV Token Watch.app"
```

### Method 2: DMG (Professional)
```bash
# Install create-dmg if not already
brew install create-dmg

# Create DMG
create-dmg \
  --volname "VVV Token Watch" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --app-drop-link 600 185 \
  "VVV Token Watch.dmg" \
  "dist/VVV Token Watch.app"
```

## First Launch Issues

When users first launch the app, macOS may show security warnings:

**"Cannot open because it's from an unidentified developer"**
- Right-click the app → Open → Click "Open" in dialog

**"App is damaged"**
- This is incorrect - the app is fine
- Go to System Preferences → Security & Privacy → General → Click "Open Anyway"
- Or run: `xattr -cr "VVV Token Watch.app"`

## Troubleshooting

If the app doesn't work:

1. **Check it was built with venv**:
   ```bash
   ./rebuild_macos.sh
   ```

2. **Test from terminal**:
   ```bash
   ./dist/VVV\ Token\ Watch.app/Contents/MacOS/VVVTokenWatch
   ```
   
3. **Check logs**:
   ```bash
   ls ~/Library/Logs/VVV-Token-Watch/
   ```

4. **Ensure .env is bundled**:
   The build script should copy `.env` file. Check:
   ```bash
   ls dist/VVV\ Token\ Watch.app/Contents/Resources/.env
   ```

## File Summary

After successful build:
```
dist/
└── VVV Token Watch.app/
    └── Contents/
        ├── Info.plist
        ├── MacOS/
        │   └── VVVTokenWatch (executable)
        └── Resources/
            ├── .env (your config)
            ├── src/ (source code)
            └── data/ (data files)
```

## Version Info

Current build details:
- **App Name**: VVV Token Watch
- **Bundle ID**: com.djcallyman.vvvtokenwatch
- **Version**: 1.0.0
- **Executable**: VVVTokenWatch (no spaces for better compatibility)

---

**Ready to distribute!** The app is now fully functional on macOS.
