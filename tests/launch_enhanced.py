#!/usr/bin/env python3
"""
Launcher script for the enhanced Venice AI Dashboard.

This script demonstrates the Phase 1 enhancements to the application.
"""

import sys
import os

def check_dependencies():
    """Check if required dependencies are available."""
    try:
        import PySide6
        print("✓ PySide6 available")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Please install required packages:")
        print("pip install PySide6 requests urllib3")
        return False

def main():
    """Launch the enhanced application."""
    print("=" * 60)
    print("🚀 VENICE AI DASHBOARD - ENHANCED VERSION")
    print("=" * 60)
    print()
    print("Phase 1 Enhancements:")
    print("• Hero-style balance card with gradient background")
    print("• Enhanced action buttons with loading states")
    print("• Status indicators with color coding")
    print("• Human-friendly date formatting")
    print("• Improved theme system")
    print()
    
    if not check_dependencies():
        return False
    
    print("Launching enhanced application...")
    print("=" * 60)
    print()
    
    # Launch the main application
    try:
        from combined_app import CombinedViewerApp
        from PySide6.QtWidgets import QApplication
        
        app = QApplication(sys.argv)
        window = CombinedViewerApp()
        window.show()
        
        print("✅ Application launched successfully!")
        print()
        print("🔍 What to look for:")
        print("1. Hero balance card at the top of the API Balance tab")
        print("2. Four specific action buttons instead of generic 'Connect'")
        print("3. Loading animations when you click buttons")
        print("4. Color-coded status indicators")
        print("5. Enhanced theme switching")
        print()
        
        return app.exec()
        
    except Exception as e:
        print(f"❌ Error launching application: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)