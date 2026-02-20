"""
System tray integration for VVV Token Watch.
Provides minimize to tray functionality and notifications.
"""

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QWidget, QApplication
from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QIcon, QAction
import logging

logger = logging.getLogger(__name__)


class TrayManager(QObject):
    """
    Manages system tray icon and notifications.
    
    Signals:
        show_requested: Emitted when user requests to show the main window
        quit_requested: Emitted when user requests to quit the application
        refresh_requested: Emitted when user requests a manual refresh
    """
    show_requested = Signal()
    quit_requested = Signal()
    refresh_requested = Signal()
    
    def __init__(self, parent=None, theme_colors=None):
        super().__init__(parent)
        self.tray_icon = None
        self.tray_menu = None
        self.theme_colors = theme_colors or {}
        self._notification_history = []
        self._max_history = 10
        
        self._setup_tray()
    
    def _setup_tray(self):
        """Initialize the system tray icon and menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available on this system")
            return
        
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self.parent())
        self.tray_icon.setToolTip("VVV Token Watch")
        
        # Try to set an icon (will use default if not found)
        try:
            # For now, use a default icon - can be customized later
            self.tray_icon.setIcon(QIcon.fromTheme("applications-system"))
        except Exception as e:
            logger.debug(f"Could not set tray icon: {e}")
        
        # Create context menu
        self.tray_menu = QMenu()
        
        # Show action
        show_action = QAction("Show VVV Token Watch", self)
        show_action.triggered.connect(self._on_show_triggered)
        self.tray_menu.addAction(show_action)
        
        self.tray_menu.addSeparator()
        
        # Refresh action
        refresh_action = QAction("Refresh Data", self)
        refresh_action.triggered.connect(self._on_refresh_triggered)
        self.tray_menu.addAction(refresh_action)
        
        self.tray_menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._on_quit_triggered)
        self.tray_menu.addAction(quit_action)
        
        # Set menu
        self.tray_icon.setContextMenu(self.tray_menu)
        
        # Connect activated signal (left click)
        self.tray_icon.activated.connect(self._on_activated)
        
        # Show the tray icon
        self.tray_icon.show()
        
        logger.info("System tray initialized successfully")
    
    def _on_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.DoubleClick or reason == QSystemTrayIcon.Trigger:
            self.show_requested.emit()
    
    def _on_show_triggered(self):
        """Handle show action from tray menu."""
        self.show_requested.emit()
    
    def _on_quit_triggered(self):
        """Handle quit action from tray menu."""
        self.quit_requested.emit()
    
    def _on_refresh_triggered(self):
        """Handle refresh action from tray menu."""
        self.refresh_requested.emit()
    
    def show_notification(self, title: str, message: str, icon=QSystemTrayIcon.Information):
        """
        Show a system notification.
        
        Args:
            title: Notification title
            message: Notification message
            icon: Icon type (Information, Warning, Critical)
        """
        if not self.tray_icon or not self.tray_icon.supportsMessages():
            logger.debug(f"Cannot show notification: {title} - {message}")
            return
        
        # Add to history
        self._notification_history.append({
            'title': title,
            'message': message,
            'icon': icon
        })
        
        # Trim history
        if len(self._notification_history) > self._max_history:
            self._notification_history.pop(0)
        
        # Show notification
        try:
            self.tray_icon.showMessage(title, message, icon, 5000)  # 5 seconds
            logger.debug(f"Notification shown: {title}")
        except Exception as e:
            logger.error(f"Failed to show notification: {e}")
    
    def show_price_alert(self, token: str, price: float, change_percent: float):
        """
        Show a price alert notification.
        
        Args:
            token: Token name (e.g., "VVV", "DIEM")
            price: Current price
            change_percent: Price change percentage
        """
        if change_percent > 0:
            icon = QSystemTrayIcon.Information
            direction = "📈"
        else:
            icon = QSystemTrayIcon.Warning
            direction = "📉"
        
        title = f"{token} Price Alert"
        message = f"{token}: ${price:.4f} ({direction} {abs(change_percent):.2f}%)"
        
        self.show_notification(title, message, icon)
    
    def show_usage_alert(self, message: str):
        """Show a usage/billing alert notification."""
        self.show_notification("Usage Alert", message, QSystemTrayIcon.Warning)
    
    def set_tooltip(self, tooltip: str):
        """Update the tray icon tooltip."""
        if self.tray_icon:
            self.tray_icon.setToolTip(tooltip)
    
    def hide(self):
        """Hide the tray icon."""
        if self.tray_icon:
            self.tray_icon.hide()
    
    def show(self):
        """Show the tray icon."""
        if self.tray_icon:
            self.tray_icon.show()
    
    def is_available(self) -> bool:
        """Check if system tray is available and initialized."""
        return self.tray_icon is not None and QSystemTrayIcon.isSystemTrayAvailable()
    
    def get_notification_history(self):
        """Get list of recent notifications."""
        return self._notification_history.copy()
