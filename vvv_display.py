"""
Display components for the vvv_token_watch application.
Contains widgets for showing token prices, model information, and API usage metrics.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QScrollArea, QFrame, QProgressBar)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
import sys
from typing import List, Dict, Any

# Import the data models and worker from usage_tracker
from usage_tracker import APIKeyUsage, BalanceInfo

class TokenDisplayWidget(QWidget):
    """
    Widget for displaying token price information.
    Can display both cryptocurrency prices and Venice Credit Units (VCU).
    """
    
    def __init__(self, token_name: str, theme_colors: Dict[str, str], is_vcu: bool = False):
        """
        Initialize the TokenDisplayWidget.
        
        Args:
            token_name: Name of the token to display
            theme_colors: Dictionary containing theme color values
            is_vcu: Whether this widget is displaying VCU instead of cryptocurrency
        """
        super().__init__()
        self.token_name = token_name
        self.theme_colors = theme_colors
        self.is_vcu = is_vcu
        self.current_price = 0.0
        self.price_change = 0.0
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface components."""
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Token name label
        self.name_label = QLabel(self.token_name)
        self.name_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.name_label.setStyleSheet(f"color: {self.theme_colors['text_primary']};")
        self.name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.name_label)
        
        # Price display
        self.price_label = QLabel("$0.00")
        self.price_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.price_label.setStyleSheet(f"color: {self.theme_colors['text_primary']};")
        self.price_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.price_label)
        
        # Price change indicator
        self.change_label = QLabel("0.00%")
        self.change_label.setFont(QFont("Arial", 9))
        self.change_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.change_label)
        
        self.setLayout(layout)
        
        # Apply styling
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.theme_colors['card_background']};
                border-radius: 8px;
                border: 1px solid {self.theme_colors['border']};
            }}
        """)
    
    def update_price(self, price: float, change: float = 0.0):
        """
        Update the displayed price and price change.
        
        Args:
            price: Current price of the token
            change: Percentage change in price
        """
        self.current_price = price
        self.price_change = change
        
        # Format price display
        if self.is_vcu:
            # VCU typically has more decimal places
            price_text = f"{price:.4f}"
        else:
            # Cryptocurrency prices
            if price >= 1:
                price_text = f"${price:.2f}"
            else:
                price_text = f"${price:.6f}"
                
        self.price_label.setText(price_text)
        
        # Update change indicator
        change_text = f"{change:+.2f}%"
        self.change_label.setText(change_text)
        
        # Color coding for price change
        if change > 0:
            self.change_label.setStyleSheet(f"color: {self.theme_colors['positive']};")
        elif change < 0:
            self.change_label.setStyleSheet(f"color: {self.theme_colors['negative']};")
        else:
            self.change_label.setStyleSheet(f"color: {self.theme_colors['text_secondary']};")

class ModelDisplayWidget(QWidget):
    """
    Widget for displaying model information and status.
    Shows model name, provider, and current status indicators.
    """
    
    def __init__(self, model_info: Dict[str, Any], theme_colors: Dict[str, str]):
        """
        Initialize the ModelDisplayWidget.
        
        Args:
            model_info: Dictionary containing model information
            theme_colors: Dictionary containing theme color values
        """
        super().__init__()
        self.model_info = model_info
        self.theme_colors = theme_colors
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface components."""
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Model name
        self.name_label = QLabel(self.model_info.get('name', 'Unknown Model'))
        self.name_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.name_label.setStyleSheet(f"color: {self.theme_colors['text_primary']};")
        self.name_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.name_label)
        
        # Provider information
        provider = self.model_info.get('provider', 'Unknown')
        self.provider_label = QLabel(f"Provider: {provider}")
        self.provider_label.setFont(QFont("Arial", 9))
        self.provider_label.setStyleSheet(f"color: {self.theme_colors['text_secondary']};")
        layout.addWidget(self.provider_label)
        
        # Status indicators
        status_layout = QHBoxLayout()
        
        # Online status
        self.online_status = QFrame()
        self.online_status.setFixedSize(12, 12)
        self.online_status.setStyleSheet(f"background-color: {self.theme_colors['negative']}; border-radius: 6px;")
        status_layout.addWidget(self.online_status)
        
        self.online_label = QLabel("Offline")
        self.online_label.setFont(QFont("Arial", 9))
        self.online_label.setStyleSheet(f"color: {self.theme_colors['text_secondary']};")
        status_layout.addWidget(self.online_label)
        
        # GPU status
        self.gpu_status = QFrame()
        self.gpu_status.setFixedSize(12, 12)
        self.gpu_status.setStyleSheet(f"background-color: {self.theme_colors['negative']}; border-radius: 6px;")
        status_layout.addWidget(self.gpu_status)
        
        self.gpu_label = QLabel("GPU: N/A")
        self.gpu_label.setFont(QFont("Arial", 9))
        self.gpu_label.setStyleSheet(f"color: {self.theme_colors['text_secondary']};")
        status_layout.addWidget(self.gpu_label)
        
        layout.addLayout(status_layout)
        
        self.setLayout(layout)
        
        # Apply styling
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.theme_colors['card_background']};
                border-radius: 8px;
                border: 1px solid {self.theme_colors['border']};
            }}
        """)
    
    def update_status(self, is_online: bool, gpu_info: str = "N/A"):
        """
        Update the model status indicators.
        
        Args:
            is_online: Whether the model is currently online
            gpu_info: Current GPU usage information
        """
        # Update online status
        color = self.theme_colors['positive'] if is_online else self.theme_colors['negative']
        self.online_status.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
        self.online_label.setText("Online" if is_online else "Offline")
        self.online_label.setStyleSheet(f"color: {self.theme_colors['text_primary']};")
        
        # Update GPU status
        self.gpu_label.setText(f"GPU: {gpu_info}")

class BalanceDisplayWidget(QWidget):
    """
    Widget for displaying overall Venice API balance information.
    Shows current DIEM/USD balance in a clean, simple format.
    """

    def __init__(self, theme_colors: Dict[str, str]):
        """
        Initialize the BalanceDisplayWidget.

        Args:
            theme_colors: Dictionary containing theme color values
        """
        super().__init__()
        self.theme_colors = theme_colors
        self.balance_info = None

        self.init_ui()

    def init_ui(self):
        """Initialize the user interface components."""
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Title
        title_label = QLabel("API Balance")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        title_label.setStyleSheet(f"color: {self.theme_colors['text_primary']};")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Balance display
        balance_layout = QHBoxLayout()

        # DIEM balance
        diem_layout = QVBoxLayout()
        diem_label = QLabel("DIEM")
        diem_label.setFont(QFont("Arial", 10))
        diem_label.setStyleSheet(f"color: {self.theme_colors['text_secondary']};")
        diem_layout.addWidget(diem_label)

        self.diem_balance_label = QLabel("0.0000")
        self.diem_balance_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.diem_balance_label.setStyleSheet(f"color: {self.theme_colors['text_primary']};")
        diem_layout.addWidget(self.diem_balance_label)

        balance_layout.addLayout(diem_layout)
        balance_layout.addSpacing(30)

        # USD balance
        usd_layout = QVBoxLayout()
        usd_label = QLabel("USD")
        usd_label.setFont(QFont("Arial", 10))
        usd_label.setStyleSheet(f"color: {self.theme_colors['text_secondary']};")
        usd_layout.addWidget(usd_label)

        self.usd_balance_label = QLabel("$0.00")
        self.usd_balance_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.usd_balance_label.setStyleSheet(f"color: {self.theme_colors['text_primary']};")
        usd_layout.addWidget(self.usd_balance_label)

        balance_layout.addLayout(usd_layout)

        layout.addLayout(balance_layout)

        # Add some spacing at the bottom
        layout.addStretch()

        self.setLayout(layout)

        # Apply styling
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.theme_colors['card_background']};
                border-radius: 8px;
                border: 1px solid {self.theme_colors['border']};
            }}
        """)

    def update_balance(self, balance_info: BalanceInfo):
        """
        Update the displayed balance information.

        Args:
            balance_info: BalanceInfo object containing current balance data
        """
        self.balance_info = balance_info

        # Update balance displays
        self.diem_balance_label.setText(f"{balance_info.diem:.4f}")
        self.usd_balance_label.setText(f"${balance_info.usd:.2f}")

class APIKeyUsageWidget(QWidget):
    """
    Widget for displaying usage information for a single API key.
    Shows key name, ID, and usage bars for VCU/USD consumption.
    """
    
    def __init__(self, api_key_usage: APIKeyUsage, theme_colors: Dict[str, str]):
        """
        Initialize the APIKeyUsageWidget.
        
        Args:
            api_key_usage: APIKeyUsage object containing key usage data
            theme_colors: Dictionary containing theme color values
        """
        super().__init__()
        self.api_key_usage = api_key_usage
        self.theme_colors = theme_colors
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface components."""
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Key information
        info_layout = QHBoxLayout()
        
        # Key name
        self.name_label = QLabel(self.api_key_usage.name)
        self.name_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.name_label.setStyleSheet(f"color: {self.theme_colors['text_primary']};")
        info_layout.addWidget(self.name_label)
        
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        
        # Status indicator
        status_layout = QHBoxLayout()
        
        # Active status
        self.active_status = QFrame()
        self.active_status.setFixedSize(10, 10)
        color = self.theme_colors['positive'] if self.api_key_usage.is_active else self.theme_colors['negative']
        self.active_status.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        status_layout.addWidget(self.active_status)
        
        self.active_label = QLabel("Active" if self.api_key_usage.is_active else "Inactive")
        self.active_label.setFont(QFont("Arial", 8))
        self.active_label.setStyleSheet(f"color: {self.theme_colors['text_secondary']};")
        status_layout.addWidget(self.active_label)
        
        # Created date
        self.created_label = QLabel(f"Created: {self.api_key_usage.created_at[:10]}")
        self.created_label.setFont(QFont("Arial", 8))
        self.created_label.setStyleSheet(f"color: {self.theme_colors['text_secondary']};")
        status_layout.addWidget(self.created_label)
        
        status_layout.addStretch()
        
        layout.addLayout(status_layout)
        
        # Usage metrics - 7-day trailing usage
        usage_layout = QVBoxLayout()
        
        # DIEM usage (always show)
        diem_layout = QHBoxLayout()
        diem_label = QLabel("DIEM 7d:")
        diem_label.setFont(QFont("Arial", 9))
        diem_label.setStyleSheet(f"color: {self.theme_colors['text_secondary']};")
        diem_layout.addWidget(diem_label)

        self.diem_usage_label = QLabel(f"{self.api_key_usage.usage.diem:.4f}")
        self.diem_usage_label.setFont(QFont("Arial", 9, QFont.Bold))
        self.diem_usage_label.setStyleSheet(f"color: {self.theme_colors['text_primary']};")
        diem_layout.addWidget(self.diem_usage_label)

        diem_layout.addStretch()

        usage_layout.addLayout(diem_layout)
        
        # USD usage (only show if > 0)
        usd_value = self.api_key_usage.usage.usd
        if usd_value > 0:
            usd_layout = QHBoxLayout()
            usd_label = QLabel("USD 7d:")
            usd_label.setFont(QFont("Arial", 9))
            usd_label.setStyleSheet(f"color: {self.theme_colors['text_secondary']};")
            usd_layout.addWidget(usd_label)
            
            self.usd_usage_label = QLabel(f"${usd_value:.2f}")
            self.usd_usage_label.setFont(QFont("Arial", 9, QFont.Bold))
            self.usd_usage_label.setStyleSheet(f"color: {self.theme_colors['text_primary']};")
            usd_layout.addWidget(self.usd_usage_label)
            
            usd_layout.addStretch()
            
            usage_layout.addLayout(usd_layout)
        else:
            self.usd_usage_label = None
        
        layout.addLayout(usage_layout)
        
        self.setLayout(layout)
        
        # Apply styling
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.theme_colors['card_background']};
                border-radius: 8px;
                border: 1px solid {self.theme_colors['border']};
            }}
        """)
    
    def _update_progress_bars(self):
        """Deprecated: Progress bars removed. Kept for compatibility."""
        pass
    
    def update_usage(self, api_key_usage: APIKeyUsage):
        """
        Update the widget with new API key usage data.
        
        Args:
            api_key_usage: New APIKeyUsage object with updated data
        """
        self.api_key_usage = api_key_usage
        
        # Update labels
        self.name_label.setText(api_key_usage.name)
        
        # Update active status
        color = self.theme_colors['positive'] if api_key_usage.is_active else self.theme_colors['negative']
        self.active_status.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        self.active_label.setText("Active" if api_key_usage.is_active else "Inactive")
        
        # Update DIEM usage value
        self.diem_usage_label.setText(f"{api_key_usage.usage.diem:.4f}")
        
        # Update USD usage value only if label exists
        if self.usd_usage_label is not None:
            self.usd_usage_label.setText(f"${api_key_usage.usage.usd:.2f}")
        
        # Set initial progress values
        self._update_progress_bars()
    
    def _update_progress_bars(self):
        """Update the progress bars based on usage values."""
        # For demonstration, we'll use arbitrary thresholds for coloring
        # In a real implementation, these might be configurable or based on organization policies

        diem_usage = self.api_key_usage.usage.diem
        # Assuming a high usage threshold of 100 DIEM for coloring
        diem_percent = min(100, (diem_usage / 100.0) * 100)
        self.diem_progress.setValue(int(diem_percent))

        # Color coding for DIEM usage
        if diem_usage < 25:
            diem_color = self.theme_colors['positive']
        elif diem_usage < 75:
            diem_color = self.theme_colors['warning']
        else:
            diem_color = self.theme_colors['negative']

        self.diem_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {self.theme_colors['border']};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {diem_color};
                border-radius: 4px;
            }}
        """)

        usd_usage = self.api_key_usage.usage.usd
        # Assuming a high usage threshold of $25 for coloring
        usd_percent = min(100, (usd_usage / 25.0) * 100)
        self.usd_progress.setValue(int(usd_percent))

        # Color coding for USD usage
        if usd_usage < 5:
            usd_color = self.theme_colors['positive']
        elif usd_usage < 20:
            usd_color = self.theme_colors['warning']
        else:
            usd_color = self.theme_colors['negative']

        self.usd_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {self.theme_colors['border']};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {usd_color};
                border-radius: 4px;
            }}
        """)
    
    def update_usage(self, api_key_usage: APIKeyUsage):
        """
        Update the widget with new API key usage data.
        
        Args:
            api_key_usage: New APIKeyUsage object with updated data
        """
        self.api_key_usage = api_key_usage
        
        # Update labels
        self.name_label.setText(api_key_usage.name)
        
        # Update active status
        color = self.theme_colors['positive'] if api_key_usage.is_active else self.theme_colors['negative']
        self.active_status.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        self.active_label.setText("Active" if api_key_usage.is_active else "Inactive")
        
        # Update usage values
        self.diem_usage_label.setText(f"{api_key_usage.usage.diem:.4f}")
        self.usd_usage_label.setText(f"${api_key_usage.usage.usd:.2f}")
        
        # Update progress bars
        self._update_progress_bars()
