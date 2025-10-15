"""
Test script to verify chart rendering functionality
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTabWidget
from PySide6.QtCore import QTimer

# Import the necessary components
from model_comparison import ModelComparisonWidget
from theme import Theme


def main():
    """Test the chart rendering"""
    app = QApplication(sys.argv)
    
    # Create a simple window
    window = QMainWindow()
    window.setWindowTitle("Chart Rendering Test")
    window.setGeometry(100, 100, 1200, 800)
    
    # Create theme
    theme = Theme()
    
    # Create mock model data
    mock_models_data = {
        'data': [
            {
                'id': 'llama-3.3-70b',
                'type': 'text',
                'model_spec': {
                    'availableContextTokens': 128000,
                    'capabilities': {
                        'supportsVision': True,
                        'supportsFunctionCalling': True,
                        'supportsWebSearch': True,
                        'supportsReasoning': False
                    },
                    'pricing': {
                        'input': {'usd': 0.0003},
                        'output': {'usd': 0.0004}
                    },
                    'traits': ['reasoning', 'long-context']
                }
            },
            {
                'id': 'llama-3.2-3b',
                'type': 'text',
                'model_spec': {
                    'availableContextTokens': 128000,
                    'capabilities': {
                        'supportsVision': False,
                        'supportsFunctionCalling': True,
                        'supportsWebSearch': False,
                        'supportsReasoning': False
                    },
                    'pricing': {
                        'input': {'usd': 0.00001},
                        'output': {'usd': 0.00002}
                    },
                    'traits': ['fast', 'efficient']
                }
            }
        ]
    }
    
    # Create the comparison widget
    comparison_widget = ModelComparisonWidget(theme, mock_models_data)
    
    # Set as central widget
    window.setCentralWidget(comparison_widget)
    
    # Switch to analytics tab after a short delay
    def switch_to_analytics():
        comparison_widget.tab_widget.setCurrentIndex(1)  # Analytics tab
        print("✓ Switched to Analytics tab")
        print("✓ Charts should be visible now")
        print("✓ You should see:")
        print("  - Usage by Model chart (bar charts)")
        print("  - Cost Breakdown chart (pie chart)")
        print("  - Performance Metrics table")
        print("  - Smart Recommendations")
    
    QTimer.singleShot(1000, switch_to_analytics)
    
    # Show the window
    window.show()
    print("✓ Test window opened")
    print("✓ Chart rendering test initialized")
    print("  Waiting for analytics worker to generate mock data...")
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
