#!/usr/bin/env python3
"""
Debug launcher for VVV Token Watch - shows errors in a dialog
"""
import sys
import os
import traceback
from pathlib import Path

# Log file
log_dir = Path.home() / "Library" / "Logs" / "VVV-Token-Watch"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "debug_launch.log"

def log(msg):
    with open(log_file, 'a') as f:
        f.write(f"{msg}\n")

try:
    log(f"=== Debug Launch {os.environ.get('__CFBundleIdentifier', 'unknown')} ===")
    log(f"CWD: {os.getcwd()}")
    log(f"Args: {sys.argv}")
    log(f"Python: {sys.executable}")
    log(f"Frozen: {getattr(sys, 'frozen', False)}")
    
    # Try importing key modules
    log("Importing PySide6...")
    from PySide6.QtWidgets import QApplication
    
    log("Importing main...")
    from src.main import main
    
    log("Starting main...")
    sys.exit(main())
    
except Exception as e:
    error_msg = f"ERROR: {str(e)}\n\n{traceback.format_exc()}"
    log(error_msg)
    
    # Show error dialog
    try:
        from PySide6.QtWidgets import QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("VVV Token Watch - Startup Error")
        msg.setText(f"Failed to start:\n\n{str(e)}")
        msg.setDetailedText(traceback.format_exc())
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()
    except Exception:
        # Fallback to osascript
        os.system(f'osascript -e \'display dialog "VVV Token Watch Error: {str(e)}" buttons {{"OK"}} default button "OK" with icon stop\'')
    
    sys.exit(1)
