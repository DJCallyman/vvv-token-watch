"""
Status indicator widget for visual status display with color coding.

This module provides a reusable status indicator component that can display
various states with appropriate colors and animations.
"""

from typing import Dict, Optional
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtGui import QFont


class StatusIndicator(QWidget):
    """
    A visual status indicator widget with color coding and animations.
    
    Supports various status types with appropriate colors:
    - active: Green for active/online states
    - inactive: Red for inactive/offline states  
    - warning: Yellow/orange for warning states
    - neutral: Gray for neutral states
    - loading: Blue for loading states
    - error: Red for error states
    """
    
    status_changed = Signal(str, str)  # status_type, message
    
    def __init__(self, status_type: str = "neutral", 
                 message: str = "", 
                 theme_colors: Dict[str, str] = None,
                 show_dot: bool = True,
                 parent=None):
        """
        Initialize the status indicator.
        
        Args:
            status_type: Type of status ('active', 'inactive', 'warning', 'neutral', 'loading', 'error')
            message: Status message text
            theme_colors: Dictionary of theme colors
            show_dot: Whether to show the colored status dot
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.theme_colors = theme_colors or {}
        self.show_dot = show_dot
        self.current_status = status_type
        self.current_message = message
        
        self.init_ui()
        self.update_status(status_type, message)
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setFixedHeight(24)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Status dot (colored indicator)
        if self.show_dot:
            self.status_dot = QLabel("●")
            font = QFont()
            font.setPointSize(12)
            self.status_dot.setFont(font)
            self.status_dot.setFixedSize(16, 16)
            self.status_dot.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.status_dot)
        
        # Status text
        self.status_label = QLabel()
        font = QFont()
        font.setPointSize(9)
        self.status_label.setFont(font)
        layout.addWidget(self.status_label)
        
        # Add stretch to prevent expansion
        layout.addStretch()
        
        # Animation effect for smooth transitions
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)
    
    def update_status(self, status_type: str, message: str = "", animate: bool = True):
        """
        Update the status indicator with new status and message.
        
        Args:
            status_type: New status type
            message: New status message
            animate: Whether to animate the transition
        """
        if status_type == self.current_status and message == self.current_message:
            return  # No change needed
        
        self.current_status = status_type
        self.current_message = message
        
        # Get appropriate color for status
        color = self._get_status_color(status_type)
        
        # Update status dot color
        if self.show_dot and hasattr(self, 'status_dot'):
            self.status_dot.setStyleSheet(f"color: {color};")
        
        # Update status text
        if message:
            self.status_label.setText(message)
            self.status_label.setStyleSheet(f"color: {self.theme_colors.get('text', '#000000')};")
        else:
            # Default message based on status type
            default_message = self._get_default_message(status_type)
            self.status_label.setText(default_message)
            self.status_label.setStyleSheet(f"color: {color};")
        
        # Set tooltip with detailed information
        tooltip = self._generate_tooltip(status_type, message)
        self.setToolTip(tooltip)
        
        # Animate transition if requested
        if animate:
            self._animate_change()
        
        # Emit signal
        self.status_changed.emit(status_type, message)
    
    def _get_status_color(self, status_type: str) -> str:
        """Get the appropriate color for a status type.
        
        All colors come from theme_colors dictionary, with no hardcoded fallbacks.
        If a color is missing from theme, defaults to text_secondary color.
        """
        # First try direct status color keys
        color = self.theme_colors.get(status_type)
        
        if color:
            return color
        
        # Map status types to theme color keys
        color_key_mapping = {
            'active': 'positive',      # Use theme's positive color
            'inactive': 'negative',    # Use theme's negative color
            'warning': 'warning',      # Use theme's warning color
            'neutral': 'text_secondary',  # Use theme's secondary text color
            'loading': 'primary',      # Use theme's primary color
            'error': 'error',          # Use theme's error color
            'success': 'success',      # Use theme's success color
        }
        
        theme_key = color_key_mapping.get(status_type, 'text_secondary')
        return self.theme_colors.get(theme_key, self.theme_colors.get('text_secondary', '#999999'))
    
    def _get_default_message(self, status_type: str) -> str:
        """Get default message for a status type."""
        default_messages = {
            'active': 'Active',
            'inactive': 'Inactive', 
            'warning': 'Warning',
            'neutral': 'Ready',
            'loading': 'Loading...',
            'error': 'Error',
            'success': 'Success',
        }
        return default_messages.get(status_type, 'Unknown')
    
    def _generate_tooltip(self, status_type: str, message: str) -> str:
        """Generate tooltip text with detailed information."""
        if message:
            return f"Status: {status_type.title()} - {message}"
        else:
            return f"Status: {status_type.title()}"
    
    def _animate_change(self):
        """Animate the status change with a fade effect."""
        # Fade out, then fade back in
        self.fade_animation.finished.connect(self._fade_in)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.7)
        self.fade_animation.start()
    
    def _fade_in(self):
        """Fade back in after fade out."""
        self.fade_animation.finished.disconnect()
        self.fade_animation.setStartValue(0.7)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
    
    def set_theme_colors(self, theme_colors: Dict[str, str]):
        """Update theme colors and refresh display."""
        self.theme_colors = theme_colors
        self.update_status(self.current_status, self.current_message, animate=False)
    
    def get_status(self) -> tuple:
        """Get current status information."""
        return (self.current_status, self.current_message)


class ConnectionStatusIndicator(StatusIndicator):
    """Specialized status indicator for connection states."""
    
    def __init__(self, theme_colors: Dict[str, str] = None, parent=None):
        super().__init__(
            status_type="neutral",
            message="Not connected",
            theme_colors=theme_colors,
            show_dot=True,
            parent=parent
        )
    
    def set_connected(self, is_connected: bool, details: str = ""):
        """Set connection status."""
        if is_connected:
            self.update_status("active", details or "Connected")
        else:
            self.update_status("inactive", details or "Disconnected")
    
    def set_connecting(self, message: str = "Connecting..."):
        """Set connecting status."""
        self.update_status("loading", message)
    
    def set_error(self, error_message: str):
        """Set error status."""
        self.update_status("error", f"Connection error: {error_message}")


class PriceChangeIndicator(StatusIndicator):
    """Specialized status indicator for price changes."""
    
    def __init__(self, theme_colors: Dict[str, str] = None, parent=None):
        super().__init__(
            status_type="neutral",
            message="No data",
            theme_colors=theme_colors,
            show_dot=True,
            parent=parent
        )
    
    def set_price_change(self, change_percentage: float, change_amount: float = None):
        """
        Set price change status based on percentage change.
        
        Args:
            change_percentage: Price change percentage (positive or negative)
            change_amount: Optional absolute change amount
        """
        if change_percentage > 0:
            # Positive change
            arrow = "↗️"
            status_type = "price_positive"
            if change_amount is not None:
                message = f"{arrow} +{change_percentage:.2f}% (+${change_amount:.4f})"
            else:
                message = f"{arrow} +{change_percentage:.2f}%"
        elif change_percentage < 0:
            # Negative change
            arrow = "↘️"
            status_type = "price_negative"
            if change_amount is not None:
                message = f"{arrow} {change_percentage:.2f}% (-${abs(change_amount):.4f})"
            else:
                message = f"{arrow} {change_percentage:.2f}%"
        else:
            # No change
            arrow = "→"
            status_type = "neutral"
            message = f"{arrow} 0.00%"
        
        self.update_status(status_type, message)


class UsageStatusIndicator(StatusIndicator):
    """Specialized status indicator for usage/spending status."""
    
    def __init__(self, theme_colors: Dict[str, str] = None, parent=None):
        super().__init__(
            status_type="neutral",
            message="No usage data",
            theme_colors=theme_colors,
            show_dot=True,
            parent=parent
        )
    
    def set_usage_trend(self, trend: str, daily_average: float = None):
        """
        Set usage trend status.
        
        Args:
            trend: 'increasing', 'decreasing', 'stable'
            daily_average: Optional daily average spending amount
        """
        if trend == "increasing":
            arrow = "↗️"
            status_type = "warning"
            message = f"{arrow} Usage increasing"
        elif trend == "decreasing":
            arrow = "↘️"
            status_type = "success"
            message = f"{arrow} Usage decreasing"
        else:
            arrow = "→"
            status_type = "neutral"
            message = f"{arrow} Usage stable"
        
        if daily_average is not None:
            message += f" (${daily_average:.2f}/day)"
        
        self.update_status(status_type, message)