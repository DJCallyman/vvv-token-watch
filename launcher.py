#!/usr/bin/env python3
"""
Launcher script for VVV Token Watch macOS app.
This wrapper helps capture and log startup errors.
"""

import sys
import os
import traceback
from pathlib import Path

# Set up logging to file for debugging
log_dir = Path.home() / "Library" / "Logs" / "VVV-Token-Watch"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "startup.log"

def log_message(msg):
    """Write message to log file"""
    with open(log_file, 'a') as f:
        f.write(f"{msg}\n")
    print(msg, file=sys.stderr)

try:
    # Log startup info
    log_message(f"=== VVV Token Watch Launcher ===")
    log_message(f"Python: {sys.executable}")
    log_message(f"Args: {sys.argv}")
    log_message(f"Working dir: {os.getcwd()}")
    log_message(f"Frozen: {getattr(sys, 'frozen', False)}")
    
    # Check for _MEIPASS (PyInstaller temp dir)
    if hasattr(sys, '_MEIPASS'):
        log_message(f"_MEIPASS: {sys._MEIPASS}")
    
    # Import and run the main application
    log_message("Importing run module...")
    import run
    
    log_message("Application started successfully")
    
except Exception as e:
    error_msg = f"ERROR: {str(e)}\n{traceback.format_exc()}"
    log_message(error_msg)
    
    # Show error dialog on macOS
    try:
        import subprocess
        subprocess.run([
            'osascript', '-e',
            f'display dialog "VVV Token Watch failed to start: {str(e)}" buttons {{"OK"}} default button "OK" with icon stop'
        ])
    except Exception:
        pass
    
    sys.exit(1)
