#!/usr/bin/env python3
"""
VVV Token Watch - Main entry point.

This is the main entry point for the VVV Token Watch application.
It launches the GUI application from the src module.
"""

import sys
import os
import traceback
from pathlib import Path
import logging

# Suppress OpenSSL 3.x / Python 3.13 hashlib initialization warnings (blake2 compatibility)
# These errors occur during Python's internal hashlib module initialization with OpenSSL 3.6.0+
# and don't affect application functionality.
class HashLibFilter(logging.Filter):
    """Suppress non-critical blake2 hash initialization warnings from OpenSSL 3.6.0+"""
    def filter(self, record):
        return 'blake2' not in record.getMessage()

logging.getLogger().addFilter(HashLibFilter())

# Set up logging first thing
if getattr(sys, 'frozen', False):
    # Running as bundled app
    if hasattr(sys, '_MEIPASS'):
        bundle_dir = Path(sys._MEIPASS)
    else:
        bundle_dir = Path(sys.executable).parent.parent / 'Resources'
    
    log_dir = Path.home() / 'Library' / 'Logs' / 'VVV-Token-Watch'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'startup.log'
    
    # Redirect stderr to log file
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info(f"=== App Starting ===")
    logger.info(f"Bundle dir: {bundle_dir}")
    logger.info(f"Working dir: {os.getcwd()}")
    logger.info(f"Frozen: {getattr(sys, 'frozen', False)}")
    logger.info(f"_MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")
    logger.info(f"Executable: {sys.executable}")
    logger.info(f"sys.path: {sys.path}")

try:
    # Handle frozen vs non-frozen paths
    if getattr(sys, 'frozen', False):
        # Bundled app - src should be in Resources
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller onefile mode
            base_path = Path(sys._MEIPASS)
        else:
            # PyInstaller onedir mode
            base_path = Path(sys.executable).parent.parent / 'Resources'
        
        src_path = base_path / 'src'
        if src_path.exists():
            sys.path.insert(0, str(src_path))
            if getattr(sys, 'frozen', False):
                logger.info(f"Added to path: {src_path}")
    else:
        # Running from source
        sys.path.insert(0, str(Path(__file__).parent / 'src'))

    # Import and run the main application
    from src.main import main
    
    if getattr(sys, 'frozen', False):
        logger.info("Successfully imported main module")
    
    if __name__ == '__main__':
        sys.exit(main())
        
except Exception as e:
    error_msg = f"Startup Error: {str(e)}\n{traceback.format_exc()}"
    
    if getattr(sys, 'frozen', False):
        logger.error(error_msg)
    else:
        print(error_msg, file=sys.stderr)
    
    # Show error dialog if possible
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("VVV Token Watch - Error")
        msg.setText(f"Failed to start:\n{str(e)}")
        msg.setDetailedText(traceback.format_exc())
        msg.exec()
    except:
        pass
    
    sys.exit(1)
