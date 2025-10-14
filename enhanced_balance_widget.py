"""
Enhanced balance widget with hero card styling and visual prominence.

This module provides a redesigned balance display widget with gradient backgrounds,
drop shadows, enhanced typography, and prominent visual design.

Phase 2 enhancements:
- Usage analytics integration
- Exchange rate display
- Top-up CTA integration
- Enhanced trend analysis
"""

from typing import Dict, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QFrame, QGraphicsDropShadowEffect, QSizePolicy)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal, QTimer
from PySide6.QtGui import QFont, QPalette, QLinearGradient, QBrush, QColor, QPainter

try:
    from .status_indicator import StatusIndicator, UsageStatusIndicator
    from .usage_analytics import UsageAnalytics, UsageTrend, format_trend_display, format_days_remaining
    from .exchange_rate_service import ExchangeRateData, format_rate_display
    from .date_utils import DateFormatter
except ImportError:
    from status_indicator import StatusIndicator, UsageStatusIndicator
    from usage_analytics import UsageAnalytics, UsageTrend, format_trend_display, format_days_remaining
    from exchange_rate_service import ExchangeRateData, format_rate_display
    from date_utils import DateFormatter


class HeroBalanceWidget(QWidget):
    """
    Hero-style balance display with prominent positioning and visual emphasis.
    
    Features:
    - Gradient background with theme-appropriate colors
    - Drop shadow effect for depth
    - Bold typography hierarchy
    - Status indicators for usage trends
    - Animated value updates
    - Enhanced visual separation from other elements
    """
    
    balance_clicked = Signal()
    refresh_requested = Signal()
    
    def __init__(self, theme_colors: Dict[str, str], parent=None):
        """
        Initialize the hero balance widget.
        
        Args:
            theme_colors: Dictionary of theme colors
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.theme_colors = theme_colors
        self.current_balance_diem = 0.0
        self.current_balance_usd = 0.0
        self.current_rate = 0.0
        self.daily_average = 0.0
        self.usage_trend = "stable"
        self.days_remaining_estimate = None
        self.last_updated = None
        
        # Analytics and rate data
        self.current_trend: Optional[UsageTrend] = None
        self.current_rate_data: Optional[ExchangeRateData] = None
        
        self.init_ui()
        self.apply_hero_styling()
    
    def paintEvent(self, event):
        """Custom paint method to draw gradient background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create gradient
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        start_color = QColor(self.theme_colors.get('hero_gradient_start', '#2d5aa0'))
        end_color = QColor(self.theme_colors.get('hero_gradient_end', '#1e3a5f'))
        gradient.setColorAt(0, start_color)
        gradient.setColorAt(1, end_color)
        
        # Draw rounded rectangle with gradient
        painter.setBrush(QBrush(gradient))
        painter.setPen(QColor(self.theme_colors.get('accent', '#0078d7')))
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 12, 12)
        
        super().paintEvent(event)
    
    def init_ui(self):
        """Initialize the user interface."""
        # Set minimum height for hero card
        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)
        
        # Header section with title and status
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        # Title
        self.title_label = QLabel("API Balance")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        header_layout.addWidget(self.title_label)
        
        # Status indicator
        self.status_indicator = StatusIndicator(
            status_type="neutral", 
            message="Ready",
            theme_colors=self.theme_colors,
            show_dot=True
        )
        header_layout.addWidget(self.status_indicator)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # Balance section
        balance_layout = QHBoxLayout()
        balance_layout.setSpacing(20)
        
        # DIEM balance
        diem_container = self.create_balance_container("DIEM Balance", "Loading...", "DIEM")
        self.diem_amount_label = diem_container['amount']
        balance_layout.addWidget(diem_container['widget'])
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet(f"color: {self.theme_colors.get('border', '#333333')};")
        balance_layout.addWidget(separator)
        
        # USD equivalent
        usd_container = self.create_balance_container("USD Equivalent", "Loading...", "USD")
        self.usd_amount_label = usd_container['amount']
        balance_layout.addWidget(usd_container['widget'])
        
        main_layout.addLayout(balance_layout)
        
        # Enhanced footer with analytics and CTA
        footer_layout = QVBoxLayout()
        footer_layout.setSpacing(8)
        
        # Top row: Rate and days remaining
        top_row = QHBoxLayout()
        top_row.setSpacing(15)
        
        # Exchange rate display (enhanced)
        self.rate_label = QLabel("Rate: Loading...")
        rate_font = QFont()
        rate_font.setPointSize(9)
        self.rate_label.setFont(rate_font)
        self.rate_label.setStyleSheet("color: #e0e0e0 !important; background-color: transparent !important;")
        top_row.addWidget(self.rate_label)
        
        top_row.addStretch()
        
        # Days remaining estimate
        self.days_remaining_label = QLabel("")
        self.days_remaining_label.setStyleSheet("color: #e0e0e0 !important; background-color: transparent !important; font-size: 9px;")
        top_row.addWidget(self.days_remaining_label)
        
        footer_layout.addLayout(top_row)
        
        # Bottom row: Usage trend indicator
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(15)
        
        # Usage trend indicator (enhanced)
        self.usage_indicator = UsageStatusIndicator(
            theme_colors=self.theme_colors
        )
        bottom_row.addWidget(self.usage_indicator)
        
        bottom_row.addStretch()
        
        footer_layout.addLayout(bottom_row)
        
        main_layout.addLayout(footer_layout)
        
        # Apply initial styling after all components are created
        QTimer.singleShot(100, self.apply_hero_styling)
    
    def create_balance_container(self, title: str, amount: str, currency: str) -> Dict:
        """
        Create a balance display container.
        
        Args:
            title: Container title (e.g., "DIEM Balance")
            amount: Initial amount value
            currency: Currency symbol or code
            
        Returns:
            Dictionary with 'widget' and 'amount' label references
        """
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # CRITICAL: Make container transparent to show gradient background
        container.setStyleSheet("background-color: transparent !important;")
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Title
        title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setWeight(QFont.Medium)
        title_label.setFont(title_font)
        # Force white text on transparent background
        title_label.setStyleSheet("color: #ffffff !important; background-color: transparent !important;")
        layout.addWidget(title_label)
        
        # Amount
        amount_label = QLabel(amount)
        amount_label.setObjectName("amount_label")  # Set object name for styling
        amount_font = QFont()
        amount_font.setPointSize(18)
        amount_font.setBold(True)
        amount_label.setFont(amount_font)
        # Force white text on transparent background - this is the main balance text
        amount_label.setStyleSheet("color: #ffffff !important; background-color: transparent !important; font-weight: bold !important;")
        layout.addWidget(amount_label)
        
        # Currency label
        currency_label = QLabel(currency)
        currency_font = QFont()
        currency_font.setPointSize(8)
        currency_label.setFont(currency_font)
        # Force light gray text on transparent background
        currency_label.setStyleSheet("color: #e0e0e0 !important; background-color: transparent !important;")
        layout.addWidget(currency_label)
        
        return {
            'widget': container,
            'title': title_label,
            'amount': amount_label,
            'currency': currency_label
        }
    
    def apply_hero_styling(self):
        """Apply hero card styling with gradient background and shadow."""
        # Set base styling (background will be drawn by paintEvent)
        self.setStyleSheet(f"""
            HeroBalanceWidget {{
                border: 2px solid {self.theme_colors.get('accent', '#0078d7')};
                border-radius: 12px;
                margin: 5px;
                padding: 10px;
                background-color: transparent;
            }}
        """)
        
        # Apply drop shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
        # Apply text colors
        text_color = "#ffffff"  # White text on gradient background
        secondary_color = "#e0e0e0"
        
        # Style specific components directly
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"color: {text_color}; font-weight: bold; background-color: transparent;")
        
        if hasattr(self, 'diem_amount_label'):
            self.diem_amount_label.setStyleSheet(f"color: {text_color}; font-weight: bold; background-color: transparent;")
        
        if hasattr(self, 'usd_amount_label'):
            self.usd_amount_label.setStyleSheet(f"color: {text_color}; font-weight: bold; background-color: transparent;")
        
        if hasattr(self, 'rate_label'):
            self.rate_label.setStyleSheet(f"color: {secondary_color}; background-color: transparent;")
        
        # Update all other labels with appropriate colors
        for label in self.findChildren(QLabel):
            # Skip labels we've already styled directly
            if label in [getattr(self, attr, None) for attr in ['title_label', 'diem_amount_label', 'usd_amount_label', 'rate_label']]:
                continue
                
            if hasattr(label, 'objectName') and "amount" in str(label.objectName()):
                label.setStyleSheet(f"color: {text_color}; font-weight: bold; background-color: transparent;")
            else:
                label.setStyleSheet(f"color: {secondary_color}; background-color: transparent;")
        
        # Force repaint to show gradient
        self.update()
    
    def update_balance(self, diem_balance: float, usd_balance: float, 
                      exchange_rate: float = None, animate: bool = True):
        """
        Update the balance display with new values.
        
        Args:
            diem_balance: DIEM balance amount
            usd_balance: USD equivalent amount
            exchange_rate: Current DIEM to USD exchange rate
            animate: Whether to animate the value change
        """
        # Store current values
        self.current_balance_diem = diem_balance
        self.current_balance_usd = usd_balance
        if exchange_rate is not None:
            self.current_rate = exchange_rate
        
        # Update DIEM amount
        diem_text = f"{diem_balance:.4f}"
        if animate and self.diem_amount_label.text() != diem_text:
            self._animate_value_change(self.diem_amount_label, diem_text)
        else:
            self.diem_amount_label.setText(diem_text)
        
        # Update USD amount
        usd_text = f"${usd_balance:.2f}"
        if animate and self.usd_amount_label.text() != usd_text:
            self._animate_value_change(self.usd_amount_label, usd_text)
        else:
            self.usd_amount_label.setText(usd_text)
        
        # Update exchange rate if provided
        if exchange_rate is not None:
            rate_text = f"Rate: 1 DIEM = ${exchange_rate:.4f}"
            self.rate_label.setText(rate_text)
        
        # Reapply text styling to ensure white text is visible
        self._reapply_text_styling()
        
        # Also force styling after a brief delay to override any parent styling
        QTimer.singleShot(10, self._reapply_text_styling)

        # Update status
        if diem_balance > 0:
            self.status_indicator.update_status("active", "Balance loaded")
        else:
            self.status_indicator.update_status("warning", "Low balance")
    
    def update_usage_info(self, daily_average: float, trend: str, 
                         days_remaining: int = None):
        """
        Update usage information and trend indicators.
        
        Args:
            daily_average: Average daily spending amount
            trend: Usage trend ('increasing', 'decreasing', 'stable')
            days_remaining: Estimated days remaining (optional)
        """
        self.daily_average = daily_average
        self.usage_trend = trend
        
        # Update usage indicator
        self.usage_indicator.set_usage_trend(trend, daily_average)
        
        # Add days remaining to status if available
        if days_remaining is not None:
            if days_remaining < 7:
                self.status_indicator.update_status("warning", f"~{days_remaining} days remaining")
            elif days_remaining < 30:
                self.status_indicator.update_status("neutral", f"~{days_remaining} days remaining")
    
    def set_loading_state(self, is_loading: bool, message: str = ""):
        """
        Set the loading state of the widget.
        
        Args:
            is_loading: Whether the widget is in loading state
            message: Optional loading message
        """
        if is_loading:
            self.status_indicator.update_status("loading", message or "Loading balance...")
            # Optionally disable interaction
            self.setEnabled(False)
        else:
            self.setEnabled(True)
            # Status will be updated by update_balance method
    
    def set_error_state(self, error_message: str):
        """
        Set the widget to error state.
        
        Args:
            error_message: Error message to display
        """
        self.status_indicator.update_status("error", error_message)
        
        # Show error styling
        self.diem_amount_label.setText("Error")
        self.usd_amount_label.setText("Error")
        self.rate_label.setText("Rate: Error loading")
    
    def _reapply_text_styling(self):
        """Reapply text styling to ensure proper colors on gradient background."""
        # CRITICAL: Hero widget ALWAYS uses white text on dark gradient, regardless of theme
        text_color = "#ffffff"  # White text - NEVER changes
        secondary_color = "#e0e0e0"  # Light gray - NEVER changes
        important_suffix = " !important"  # Force override any parent styling
        
        # Style ALL text elements to ensure they're visible on gradient
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"color: {text_color}{important_suffix}; font-weight: bold{important_suffix}; background-color: transparent{important_suffix}; font-size: 14px{important_suffix};")
        
        if hasattr(self, 'diem_amount_label'):
            self.diem_amount_label.setStyleSheet(f"color: {text_color}{important_suffix}; font-weight: bold{important_suffix}; background-color: transparent{important_suffix}; font-size: 28px{important_suffix};")
        
        if hasattr(self, 'usd_amount_label'):
            self.usd_amount_label.setStyleSheet(f"color: {text_color}{important_suffix}; font-weight: bold{important_suffix}; background-color: transparent{important_suffix}; font-size: 28px{important_suffix};")
        
        if hasattr(self, 'rate_label'):
            self.rate_label.setStyleSheet(f"color: {secondary_color}{important_suffix}; background-color: transparent{important_suffix}; font-size: 9px{important_suffix};")
            
        # Force style ALL other labels to be white as well (defensive approach)
        for label in self.findChildren(QLabel):
            current_style = label.styleSheet()
            # Always override with white text - no exceptions
            if label == getattr(self, 'rate_label', None):
                # Rate label uses secondary color
                label.setStyleSheet(f"color: {secondary_color}{important_suffix}; background-color: transparent{important_suffix};")
            else:
                # All other labels use primary white color
                label.setStyleSheet(f"color: {text_color}{important_suffix}; background-color: transparent{important_suffix};")
    
    def _animate_value_change(self, label: QLabel, new_value: str):
        """
        Animate a value change with a subtle fade effect.
        
        Args:
            label: Label to animate
            new_value: New value to display
        """
        # Simple opacity animation
        label.setText(new_value)
        # Reapply styling after text change
        self._reapply_text_styling()
        # Could add more sophisticated number rolling animation here
    
    def set_theme_colors(self, theme_colors: Dict[str, str]):
        """
        Update theme colors and refresh styling.
        NOTE: Hero widget always uses white text on gradient regardless of theme.
        
        Args:
            theme_colors: New theme colors dictionary
        """
        self.theme_colors = theme_colors
        self.status_indicator.set_theme_colors(theme_colors)
        self.usage_indicator.set_theme_colors(theme_colors)
        
        # Apply styling but IGNORE theme text colors - always use white on gradient
        self.apply_hero_styling()
        self.update()  # Force repaint with new colors
        
        # CRITICAL: Force white text styling regardless of theme
        QTimer.singleShot(50, self.force_text_styling)
        QTimer.singleShot(100, self.force_text_styling)  # Double application for safety
    
    def force_text_styling(self):
        """Force reapplication of text styling - call this after widget is fully integrated."""
        self._reapply_text_styling()
        
        # Also force an update to ensure the styling takes effect
        self.update()
        self.repaint()
    
    def mousePressEvent(self, event):
        """Handle mouse click events."""
        if event.button() == Qt.LeftButton:
            self.balance_clicked.emit()
        super().mousePressEvent(event)
    
    # Phase 2 Enhancement Methods
    
    def update_with_analytics(self, balance_info, trend: UsageTrend, rate_data: Optional[ExchangeRateData] = None):
        """
        Update balance display with analytics and trend data.
        
        Args:
            balance_info: Balance information (BalanceInfo object)
            trend: Usage trend analysis results
            rate_data: Optional exchange rate data
        """
        # Store analytics data
        self.current_trend = trend
        self.current_rate_data = rate_data
        
        # Update basic balance
        self.update_balance(balance_info.diem, balance_info.usd, rate_data.rate if rate_data else 0.72)
        
        # Update trend display
        trend_text = format_trend_display(trend)
        self.usage_indicator.set_usage_trend(trend.trend_direction, trend.daily_average_usd)
        
        # Update days remaining estimate
        if trend.days_remaining_estimate is not None:
            days_text = format_days_remaining(trend.days_remaining_estimate)
            self.days_remaining_label.setText(days_text)
            self.days_remaining_estimate = trend.days_remaining_estimate
        else:
            self.days_remaining_label.setText("")
        
        # Update exchange rate display
        if rate_data:
            self.update_exchange_rate_display(rate_data)
        
        # Update status based on analytics
        self._update_status_from_analytics(trend, balance_info)
    
    def update_exchange_rate_display(self, rate_data: ExchangeRateData):
        """
        Update the exchange rate display with new rate data.
        
        Args:
            rate_data: Exchange rate information
        """
        self.current_rate_data = rate_data
        
        # Format rate display
        rate_text = format_rate_display(rate_data.rate)
        
        # Add 24h change if available
        if rate_data.change_24h is not None:
            change = rate_data.change_24h
            if change > 0:
                rate_text += f" (↗️ +{change:.2f}%)"
            elif change < 0:
                rate_text += f" (↘️ {change:.2f}%)"
        
        # Add age indicator
        if rate_data.source in ["cached", "cached_stale", "fallback"]:
            rate_text += " ⚠️"
        
        self.rate_label.setText(rate_text)
        self.current_rate = rate_data.rate
    
    def update_usage_estimate(self, daily_average_usd: float, current_balance_usd: float):
        """
        Update the usage estimate and days remaining calculation.
        
        Args:
            daily_average_usd: Average daily spending in USD
            current_balance_usd: Current balance in USD
        """
        self.daily_average = daily_average_usd
        
        # Calculate days remaining
        if daily_average_usd > 0 and current_balance_usd > 0:
            days_remaining = int(current_balance_usd / daily_average_usd)
            self.days_remaining_estimate = max(0, days_remaining)
            
            # Update display
            days_text = format_days_remaining(self.days_remaining_estimate)
            self.days_remaining_label.setText(days_text)
        else:
            self.days_remaining_label.setText("")
    
    def set_trend_data(self, trend: UsageTrend):
        """
        Set usage trend data and update displays.
        
        Args:
            trend: Usage trend analysis results
        """
        self.current_trend = trend
        
        # Update usage indicator
        trend_text = format_trend_display(trend)
        self.usage_indicator.set_usage_trend(trend.trend_direction, trend.daily_average_usd)
        
        # Update days remaining if we have current balance
        if hasattr(self, 'current_balance_usd') and self.current_balance_usd > 0:
            self.update_usage_estimate(trend.daily_average_usd, self.current_balance_usd)
    
    def get_analytics_summary(self) -> Dict[str, any]:
        """
        Get a summary of current analytics data.
        
        Returns:
            Dictionary with current analytics information
        """
        return {
            "balance_diem": self.current_balance_diem,
            "balance_usd": self.current_balance_usd,
            "exchange_rate": self.current_rate,
            "daily_average": self.daily_average,
            "usage_trend": self.usage_trend,
            "days_remaining": self.days_remaining_estimate,
            "trend_data": self.current_trend.__dict__ if self.current_trend else None,
            "rate_data": self.current_rate_data.__dict__ if self.current_rate_data else None,
            "last_updated": self.last_updated
        }
    
    def _update_status_from_analytics(self, trend: UsageTrend, balance_info):
        """
        Update status indicator based on analytics data.
        
        Args:
            trend: Usage trend data
            balance_info: Balance information
        """
        # Determine status based on balance and trend
        if balance_info.usd <= 0:
            self.status_indicator.update_status("error", "No balance remaining")
        elif self.days_remaining_estimate is not None:
            if self.days_remaining_estimate <= 1:
                self.status_indicator.update_status("error", "Balance running out")
            elif self.days_remaining_estimate <= 7:
                self.status_indicator.update_status("warning", f"~{self.days_remaining_estimate} days left")
            elif trend.trend_direction == "increasing":
                self.status_indicator.update_status("warning", "Usage increasing")
            else:
                self.status_indicator.update_status("active", "Balance healthy")
        else:
            if balance_info.diem > 0:
                self.status_indicator.update_status("active", "Balance loaded")
            else:
                self.status_indicator.update_status("neutral", "Ready")
    
    def refresh_analytics(self):
        """Trigger analytics refresh by emitting refresh signal."""
        self.refresh_requested.emit()