"""
Top-up widget for Venice AI Dashboard - Quick Credit Addition CTA.

This module provides a prominent call-to-action for adding credits to Venice API balance,
including preset amounts and custom input options.
"""

import webbrowser
import logging
from typing import Dict, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                                QLabel, QFrame, QComboBox, QLineEdit, QDialog,
                                QDialogButtonBox, QMessageBox, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QFont, QPalette, QColor

logger = logging.getLogger(__name__)


class CustomTopUpDialog(QDialog):
    """Dialog for entering custom top-up amounts."""
    
    def __init__(self, theme_colors: Dict[str, str], parent=None):
        super().__init__(parent)
        
        self.theme_colors = theme_colors
        self.custom_amount = None
        
        self.setWindowTitle("Add Custom Credit Amount")
        self.setModal(True)
        self.setFixedSize(400, 250)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Dialog styling
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.theme_colors.get('background', '#1a1a1a')};
                border: 2px solid {self.theme_colors.get('accent', '#0066cc')};
                border-radius: 10px;
            }}
        """)
        
        # Title
        title_label = QLabel("Enter Credit Amount")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {self.theme_colors.get('text', '#ffffff')};")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel("Specify the amount of credits you'd like to add to your Venice AI account.")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {self.theme_colors.get('text_secondary', '#cccccc')}; font-size: 12px;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label)
        
        # Amount input frame
        input_frame = QFrame()
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        # Currency label
        currency_label = QLabel("$")
        currency_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme_colors.get('text', '#ffffff')};
                font-size: 16px;
                font-weight: bold;
                padding: 8px;
            }}
        """)
        input_layout.addWidget(currency_label)
        
        # Amount input
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Enter amount (e.g., 25.00)")
        self.amount_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.theme_colors.get('card_background', '#2a2a2a')};
                border: 2px solid {self.theme_colors.get('border', '#444444')};
                border-radius: 6px;
                color: {self.theme_colors.get('text', '#ffffff')};
                font-size: 14px;
                padding: 10px;
                min-width: 150px;
            }}
            QLineEdit:focus {{
                border-color: {self.theme_colors.get('accent', '#0066cc')};
            }}
        """)
        input_layout.addWidget(self.amount_input)
        
        layout.addWidget(input_frame)
        
        # Preset amounts
        preset_label = QLabel("Or select a preset amount:")
        preset_label.setStyleSheet(f"color: {self.theme_colors.get('text_secondary', '#cccccc')}; font-size: 12px;")
        layout.addWidget(preset_label)
        
        # Preset buttons
        preset_layout = QHBoxLayout()
        preset_amounts = ["$10", "$25", "$50", "$100"]
        
        for amount in preset_amounts:
            btn = QPushButton(amount)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme_colors.get('card_background', '#2a2a2a')};
                    border: 1px solid {self.theme_colors.get('border', '#444444')};
                    border-radius: 4px;
                    color: {self.theme_colors.get('text', '#ffffff')};
                    font-size: 12px;
                    padding: 6px 12px;
                    min-width: 60px;
                }}
                QPushButton:hover {{
                    background-color: {self.theme_colors.get('accent', '#0066cc')};
                    border-color: {self.theme_colors.get('accent', '#0066cc')};
                }}
                QPushButton:pressed {{
                    background-color: {self.theme_colors.get('accent_dark', '#004499')};
                }}
            """)
            btn.clicked.connect(lambda checked, amt=amount[1:]: self.set_preset_amount(amt))
            preset_layout.addWidget(btn)
        
        layout.addLayout(preset_layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.setStyleSheet(f"""
            QDialogButtonBox QPushButton {{
                background-color: {self.theme_colors.get('accent', '#0066cc')};
                border: none;
                border-radius: 4px;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                min-width: 80px;
            }}
            QDialogButtonBox QPushButton:hover {{
                background-color: {self.theme_colors.get('accent_light', '#3388dd')};
            }}
            QDialogButtonBox QPushButton:pressed {{
                background-color: {self.theme_colors.get('accent_dark', '#004499')};
            }}
        """)
        
        button_box.accepted.connect(self.accept_amount)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Focus on input
        self.amount_input.setFocus()
    
    def set_preset_amount(self, amount: str):
        """Set preset amount in input field."""
        self.amount_input.setText(amount)
    
    def accept_amount(self):
        """Validate and accept the entered amount."""
        amount_text = self.amount_input.text().strip()
        
        if not amount_text:
            QMessageBox.warning(self, "Invalid Amount", "Please enter an amount.")
            return
        
        try:
            amount = float(amount_text)
            if amount <= 0:
                QMessageBox.warning(self, "Invalid Amount", "Amount must be greater than zero.")
                return
            if amount > 10000:
                QMessageBox.warning(self, "Invalid Amount", "Amount cannot exceed $10,000.")
                return
            
            self.custom_amount = amount
            self.accept()
            
        except ValueError:
            QMessageBox.warning(self, "Invalid Amount", "Please enter a valid number.")


class TopUpWidget(QWidget):
    """
    Top-up widget providing quick credit addition functionality.
    
    Features:
    - Prominent "Add Credit" button
    - Preset amount shortcuts
    - Custom amount input
    - Direct integration with Venice.ai billing
    - Visual feedback and animations
    """
    
    topup_requested = Signal(str, float)  # action_type, amount
    
    def __init__(self, theme_colors: Dict[str, str], parent=None):
        """
        Initialize the top-up widget.
        
        Args:
            theme_colors: Theme color dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.theme_colors = theme_colors
        self.animation = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Widget background
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.theme_colors.get('card_background', '#2a2a2a')};
                border: 1px solid {self.theme_colors.get('border', '#444444')};
                border-radius: 8px;
            }}
        """)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("💳 Add Credits")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {self.theme_colors.get('text', '#ffffff')};")
        header_layout.addWidget(title_label)
        
        header_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        layout.addLayout(header_layout)
        
        # Description
        desc_label = QLabel("Quickly add credits to your Venice AI account for continued API access.")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme_colors.get('text_secondary', '#cccccc')};
                font-size: 11px;
                line-height: 1.3;
            }}
        """)
        layout.addWidget(desc_label)
        
        # Action buttons layout
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        # Main "Add Credit" button
        self.main_add_button = QPushButton("🚀 Add Credit")
        self.main_add_button.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme_colors.get('accent', '#0066cc')},
                    stop:1 {self.theme_colors.get('accent_dark', '#004499')});
                border: none;
                border-radius: 6px;
                color: white;
                font-size: 12px;
                font-weight: bold;
                padding: 10px 16px;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme_colors.get('accent_light', '#3388dd')},
                    stop:1 {self.theme_colors.get('accent', '#0066cc')});
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme_colors.get('accent_dark', '#004499')},
                    stop:1 {self.theme_colors.get('accent_darker', '#002266')});
            }}
        """)
        self.main_add_button.clicked.connect(self.show_custom_topup_dialog)
        actions_layout.addWidget(self.main_add_button)
        
        # Quick amount buttons
        quick_amounts = [("$10", 10), ("$25", 25), ("$50", 50)]
        
        for text, amount in quick_amounts:
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme_colors.get('card_background_light', '#333333')};
                    border: 1px solid {self.theme_colors.get('border', '#444444')};
                    border-radius: 4px;
                    color: {self.theme_colors.get('text', '#ffffff')};
                    font-size: 11px;
                    padding: 8px 12px;
                    min-width: 50px;
                }}
                QPushButton:hover {{
                    background-color: {self.theme_colors.get('accent', '#0066cc')};
                    border-color: {self.theme_colors.get('accent', '#0066cc')};
                }}
                QPushButton:pressed {{
                    background-color: {self.theme_colors.get('accent_dark', '#004499')};
                }}
            """)
            btn.clicked.connect(lambda checked, amt=amount: self.handle_quick_topup(amt))
            actions_layout.addWidget(btn)
        
        layout.addLayout(actions_layout)
        
        # Help text
        help_label = QLabel("Click amounts for quick top-up or 'Add Credit' for custom amounts.")
        help_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme_colors.get('text_muted', '#999999')};
                font-size: 9px;
                font-style: italic;
            }}
        """)
        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(help_label)
    
    def show_custom_topup_dialog(self):
        """Show dialog for custom top-up amount."""
        dialog = CustomTopUpDialog(self.theme_colors, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.custom_amount:
            self.handle_custom_topup(dialog.custom_amount)
    
    def handle_quick_topup(self, amount: float):
        """
        Handle quick top-up button click.
        
        Args:
            amount: Top-up amount in USD
        """
        self.animate_button_click()
        self.topup_requested.emit("quick", amount)
        self.open_venice_billing_page(amount)
    
    def handle_custom_topup(self, amount: float):
        """
        Handle custom top-up amount.
        
        Args:
            amount: Custom top-up amount in USD
        """
        self.animate_button_click()
        self.topup_requested.emit("custom", amount)
        self.open_venice_billing_page(amount)
    
    def open_venice_billing_page(self, amount: float = None):
        """
        Open Venice.ai billing page in browser.
        
        Args:
            amount: Optional amount to pre-fill
        """
        try:
            base_url = "https://venice.ai/billing"
            
            if amount:
                # Add amount as query parameter (if Venice.ai supports this)
                url = f"{base_url}?amount={amount:.2f}"
            else:
                url = base_url
            
            success = webbrowser.open(url)
            
            if success:
                # Show success feedback
                QTimer.singleShot(100, lambda: self.show_feedback("Opening Venice.ai billing page..."))
            else:
                # Show fallback message
                self.show_feedback("Please visit venice.ai/billing to add credits")
                
        except Exception as e:
            logger.error(f"Failed to open billing page: {e}")
            self.show_feedback("Please visit venice.ai/billing to add credits")
    
    def animate_button_click(self):
        """Animate button click for visual feedback."""
        if self.animation:
            self.animation.stop()
        
        # Create a simple scale animation
        original_size = self.main_add_button.size()
        
        # Quick scale down and up
        self.main_add_button.setStyleSheet(self.main_add_button.styleSheet() + """
            QPushButton {
                transform: scale(0.95);
            }
        """)
        
        QTimer.singleShot(100, lambda: self.main_add_button.setStyleSheet(
            self.main_add_button.styleSheet().replace("transform: scale(0.95);", "")
        ))
    
    def show_feedback(self, message: str):
        """
        Show temporary feedback message.
        
        Args:
            message: Feedback message to display
        """
        # For now, log to console. In a full implementation, 
        # this could show a temporary tooltip or status message
        logger.info(f"TopUp Feedback: {message}")
        
        # Could also emit a signal for the main app to show in status bar
        # self.feedback_message.emit(message)
    
    def set_theme_colors(self, theme_colors: Dict[str, str]):
        """
        Update theme colors and refresh UI.
        
        Args:
            theme_colors: New theme color dictionary
        """
        self.theme_colors = theme_colors
        self.init_ui()
    
    def set_enabled_state(self, enabled: bool):
        """
        Enable or disable the top-up functionality.
        
        Args:
            enabled: Whether top-up should be enabled
        """
        self.main_add_button.setEnabled(enabled)
        
        # Find and disable/enable quick amount buttons
        for child in self.findChildren(QPushButton):
            if child != self.main_add_button:
                child.setEnabled(enabled)
        
        if not enabled:
            # Add visual indication of disabled state
            self.setStyleSheet(self.styleSheet() + """
                QWidget {
                    opacity: 0.6;
                }
            """)
        else:
            # Remove disabled styling
            style = self.styleSheet()
            self.setStyleSheet(style.replace("opacity: 0.6;", ""))


def create_compact_topup_button(theme_colors: Dict[str, str], parent=None) -> QPushButton:
    """
    Create a compact top-up button for use in other widgets.
    
    Args:
        theme_colors: Theme color dictionary
        parent: Parent widget
        
    Returns:
        Configured QPushButton
    """
    button = QPushButton("💳 Add Credits", parent)
    button.setStyleSheet(f"""
        QPushButton {{
            background-color: {theme_colors.get('accent', '#0066cc')};
            border: none;
            border-radius: 4px;
            color: white;
            font-size: 11px;
            font-weight: bold;
            padding: 6px 12px;
            min-width: 80px;
        }}
        QPushButton:hover {{
            background-color: {theme_colors.get('accent_light', '#3388dd')};
        }}
        QPushButton:pressed {{
            background-color: {theme_colors.get('accent_dark', '#004499')};
        }}
    """)
    
    def handle_click():
        """Handle compact button click."""
        try:
            webbrowser.open("https://venice.ai/billing")
        except Exception as e:
            logger.error(f"Failed to open billing page: {e}")
    
    button.clicked.connect(handle_click)
    return button