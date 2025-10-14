"""
Action button widget with specific, context-aware buttons and loading states.

This module provides enhanced action buttons that replace generic "Connect" buttons
with specific, clear actions and visual feedback.
"""

from typing import Dict, Optional, Callable
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                                QLabel, QProgressBar, QSizePolicy, QSpacerItem)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter
try:
    from .status_indicator import StatusIndicator
except ImportError:
    from status_indicator import StatusIndicator


class ActionButton(QPushButton):
    """
    Enhanced action button with loading states, icons, and clear purpose.
    
    Features:
    - Loading state with spinner
    - Success/error state feedback
    - Icon support
    - Disabled state handling
    - Action-specific styling
    """
    
    def __init__(self, text: str, action_type: str, 
                 theme_colors: Dict[str, str], parent=None):
        """
        Initialize the action button.
        
        Args:
            text: Button text
            action_type: Type of action ('connect', 'refresh', 'load', 'topup')
            theme_colors: Theme colors dictionary
            parent: Parent widget
        """
        super().__init__(text, parent)
        
        self.action_type = action_type
        self.theme_colors = theme_colors
        self.original_text = text
        self.is_loading = False
        
        self.setup_button()
        self.apply_styling()
    
    def setup_button(self):
        """Setup button properties and behavior."""
        self.setMinimumHeight(36)
        self.setMinimumWidth(120)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        # Add icon based on action type
        icon_text = self.get_icon_for_action()
        if icon_text:
            self.setText(f"{icon_text} {self.original_text}")
        
        # Setup loading timer for animation
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.update_loading_animation)
        self.loading_dots = 0
    
    def get_icon_for_action(self) -> str:
        """Get emoji icon for action type."""
        icons = {
            'connect': '🔗',
            'refresh': '🔄',
            'load': '📊',
            'topup': '💰',
            'connect_models': '🔗',
            'refresh_balance': '💰',
            'load_usage': '📊',
            'refresh_all': '🔄'
        }
        return icons.get(self.action_type, '')
    
    def apply_styling(self):
        """Apply action-specific styling."""
        # Base colors
        bg_color = self.theme_colors.get('primary', '#0078d7')
        text_color = '#ffffff'
        border_color = self.theme_colors.get('accent', '#005a9e')
        
        # Action-specific color overrides
        if self.action_type in ['topup', 'refresh_balance']:
            bg_color = self.theme_colors.get('success', '#00c853')
            border_color = self.theme_colors.get('positive', '#00994d')
        elif self.action_type in ['refresh', 'refresh_all']:
            bg_color = self.theme_colors.get('accent', '#0078d7')
        
        # Disabled colors
        disabled_bg = self.theme_colors.get('text_secondary', '#bbbbbb')
        disabled_text = self.theme_colors.get('background', '#ffffff')
        
        # Hover colors
        hover_bg = self.adjust_color_brightness(bg_color, 1.1)
        
        self.setStyleSheet(f"""
            ActionButton {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 11px;
            }}
            ActionButton:hover {{
                background-color: {hover_bg};
            }}
            ActionButton:pressed {{
                background-color: {border_color};
            }}
            ActionButton:disabled {{
                background-color: {disabled_bg};
                color: {disabled_text};
                border-color: {disabled_bg};
            }}
        """)
    
    def adjust_color_brightness(self, color: str, factor: float) -> str:
        """Adjust color brightness by a factor."""
        try:
            # Simple hex color brightness adjustment
            if color.startswith('#'):
                hex_color = color[1:]
                if len(hex_color) == 6:
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)
                    
                    r = min(255, int(r * factor))
                    g = min(255, int(g * factor))
                    b = min(255, int(b * factor))
                    
                    return f"#{r:02x}{g:02x}{b:02x}"
            return color
        except:
            return color
    
    def set_loading_state(self, is_loading: bool, message: str = ""):
        """
        Set the loading state of the button.
        
        Args:
            is_loading: Whether button is in loading state
            message: Optional loading message
        """
        self.is_loading = is_loading
        
        if is_loading:
            self.setEnabled(False)
            self.loading_dots = 0
            self.loading_timer.start(500)  # Update every 500ms
            self.update_loading_animation()
        else:
            self.loading_timer.stop()
            self.setEnabled(True)
            icon_text = self.get_icon_for_action()
            display_text = f"{icon_text} {self.original_text}" if icon_text else self.original_text
            self.setText(display_text)
    
    def update_loading_animation(self):
        """Update loading animation text."""
        if not self.is_loading:
            return
        
        dots = "." * (self.loading_dots % 4)
        loading_text = f"Loading{dots}"
        self.setText(loading_text)
        self.loading_dots += 1
    
    def set_success_state(self, message: str = "Success", duration: int = 2000):
        """
        Show success state temporarily.
        
        Args:
            message: Success message
            duration: Duration to show success state (ms)
        """
        original_style = self.styleSheet()
        success_color = self.theme_colors.get('success', '#00c853')
        
        # Temporarily change to success styling
        self.setStyleSheet(f"""
            ActionButton {{
                background-color: {success_color};
                color: white;
                border: 1px solid {success_color};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 11px;
            }}
        """)
        
        self.setText(f"✓ {message}")
        
        # Revert after duration
        QTimer.singleShot(duration, lambda: [
            self.setStyleSheet(original_style),
            self.setText(f"{self.get_icon_for_action()} {self.original_text}")
        ])
    
    def set_error_state(self, message: str = "Error", duration: int = 3000):
        """
        Show error state temporarily.
        
        Args:
            message: Error message
            duration: Duration to show error state (ms)
        """
        original_style = self.styleSheet()
        error_color = self.theme_colors.get('error', '#ff4444')
        
        # Temporarily change to error styling
        self.setStyleSheet(f"""
            ActionButton {{
                background-color: {error_color};
                color: white;
                border: 1px solid {error_color};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 11px;
            }}
        """)
        
        self.setText(f"✗ {message}")
        
        # Revert after duration
        QTimer.singleShot(duration, lambda: [
            self.setStyleSheet(original_style),
            self.setText(f"{self.get_icon_for_action()} {self.original_text}")
        ])


class ActionButtonWidget(QWidget):
    """
    Container widget for multiple action buttons with coordinated behavior.
    
    Provides specific action buttons to replace generic "Connect" button:
    - Connect to Venice API
    - Refresh Balance
    - Load API Usage
    - Refresh All Data
    """
    
    # Signals for different actions
    connect_models_requested = Signal()
    refresh_balance_requested = Signal()
    load_usage_requested = Signal()
    refresh_all_requested = Signal()
    
    def __init__(self, theme_colors: Dict[str, str], parent=None):
        """
        Initialize the action button widget.
        
        Args:
            theme_colors: Theme colors dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.theme_colors = theme_colors
        self.buttons = {}
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Connect to Venice API button
        self.connect_button = ActionButton(
            "Connect to Venice API", 
            "connect_models",
            self.theme_colors
        )
        self.connect_button.clicked.connect(self.connect_models_requested.emit)
        self.buttons['connect'] = self.connect_button
        layout.addWidget(self.connect_button)
        
        # Refresh Balance button
        self.refresh_balance_button = ActionButton(
            "Refresh Balance",
            "refresh_balance", 
            self.theme_colors
        )
        self.refresh_balance_button.clicked.connect(self.refresh_balance_requested.emit)
        self.buttons['refresh_balance'] = self.refresh_balance_button
        layout.addWidget(self.refresh_balance_button)
        
        # Load API Usage button
        self.load_usage_button = ActionButton(
            "Load API Usage",
            "load_usage",
            self.theme_colors
        )
        self.load_usage_button.clicked.connect(self.load_usage_requested.emit)
        self.buttons['load_usage'] = self.load_usage_button
        layout.addWidget(self.load_usage_button)
        
        # Refresh All button
        self.refresh_all_button = ActionButton(
            "Refresh All Data",
            "refresh_all",
            self.theme_colors
        )
        self.refresh_all_button.clicked.connect(self.refresh_all_requested.emit)
        self.buttons['refresh_all'] = self.refresh_all_button
        layout.addWidget(self.refresh_all_button)
        
        # Add stretch to prevent buttons from expanding too much
        layout.addStretch()
    
    def set_button_loading(self, button_type: str, is_loading: bool, message: str = ""):
        """
        Set loading state for a specific button.
        
        Args:
            button_type: Type of button ('connect', 'refresh_balance', 'load_usage', 'refresh_all')
            is_loading: Whether button is loading
            message: Optional loading message
        """
        if button_type in self.buttons:
            self.buttons[button_type].set_loading_state(is_loading, message)
    
    def set_button_success(self, button_type: str, message: str = "Success"):
        """
        Set success state for a specific button.
        
        Args:
            button_type: Type of button
            message: Success message
        """
        if button_type in self.buttons:
            self.buttons[button_type].set_success_state(message)
    
    def set_button_error(self, button_type: str, message: str = "Error"):
        """
        Set error state for a specific button.
        
        Args:
            button_type: Type of button
            message: Error message
        """
        if button_type in self.buttons:
            self.buttons[button_type].set_error_state(message)
    
    def set_buttons_enabled(self, enabled: bool, exclude: list = None):
        """
        Enable or disable all buttons.
        
        Args:
            enabled: Whether to enable buttons
            exclude: List of button types to exclude from change
        """
        exclude = exclude or []
        for button_type, button in self.buttons.items():
            if button_type not in exclude:
                button.setEnabled(enabled)
    
    def set_theme_colors(self, theme_colors: Dict[str, str]):
        """
        Update theme colors for all buttons.
        
        Args:
            theme_colors: New theme colors dictionary
        """
        self.theme_colors = theme_colors
        for button in self.buttons.values():
            button.theme_colors = theme_colors
            button.apply_styling()