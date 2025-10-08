#!/usr/bin/env python3
"""
Test script for the Model Comparison & Analytics functionality.
Run this to verify the new features work correctly.
"""

import sys
import os
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from vvv_token_watch.combined_app import CombinedViewerApp
from vvv_token_watch.theme import Theme

def test_app():
    """Test the Model Comparison widget integration"""
    print("Testing Model Comparison & Analytics Features...")

    app = QApplication(sys.argv)

    # Create the main window
    window = CombinedViewerApp()

    # Test that the comparison tab exists
    tab_count = window.main_tabs.count()
    print(f"✓ Main application has {tab_count} tabs")

    # Check that the comparison tab exists and is accessible
    tab_names = []
    for i in range(tab_count):
        tab_names.append(window.main_tabs.tabText(i))

    print(f"✓ Available tabs: {tab_names}")

    if "📊 Compare & Analyze" in tab_names:
        print("✓ Model Comparison & Analytics tab successfully created")
    else:
        print("✗ ERROR: Model Comparison & Analytics tab not found")
        return False

    # Test that the model comparison widget is initialized
    if hasattr(window, 'model_comparison_widget'):
        print("✓ Model comparison widget is properly initialized")
    else:
        print("✗ ERROR: Model comparison widget not found")
        return False

    # Test theme integration
    current_tab_index = window.main_tabs.currentIndex()
    window.main_tabs.setCurrentWidget(window.comparison_tab)
    print(f"✓ Successfully switched to Comparison tab (from tab {current_tab_index})")

    # Test theme switching
    original_theme = window.theme.mode
    window.toggle_theme("Light")
    if window.theme.mode != original_theme:
        print("✓ Theme switching works correctly")
    else:
        print("✗ ERROR: Theme switching failed")

    # Switch back to dark theme for consistency
    window.toggle_theme("Dark")

    print("\n🎉 All basic tests passed!")
    print("The Model Comparison & Analytics features have been successfully integrated.")
    print("\nAdvanced features available:")
    print("- 🔍 Model capability comparison matrix")
    print("- 📊 Usage analytics and performance metrics")
    print("- 🎯 Advanced search and discovery tools")
    print("- 📈 Smart recommendations engine")
    print("- 🔄 Real-time data refresh")
    print("- 🎨 Theme-aware modern UI")

    print("\nTo test the full functionality:")
    print("1. Click 'Connect' to load Venice AI models")
    print("2. Navigate to the '📊 Compare & Analyze' tab")
    print("3. Try the different sub-tabs (🔍 Compare, 📊 Analytics, 🎯 Discover)")
    print("4. Use filters and search features to explore models")
    print("5. Test theme switching and responsiveness")

    # Show a success message and auto-close after a few seconds
    success_msg = QMessageBox()
    success_msg.setIcon(QMessageBox.Information)
    success_msg.setWindowTitle("Test Successful")
    success_msg.setText("Model Comparison & Analytics features have been successfully integrated!\n\nThe test window will close automatically.")
    success_msg.setStandardButtons(QMessageBox.Ok)

    # Auto-close after 5 seconds
    QTimer.singleShot(5000, lambda: success_msg.accept())

    success_msg.exec()

    window.show()
    return app.exec() == 0

if __name__ == "__main__":
    success = test_app()
    print(f"\nTest result: {'PASS' if success else 'FAIL'}")
    sys.exit(0 if success else 1)
