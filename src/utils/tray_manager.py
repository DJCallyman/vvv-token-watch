"""
System tray integration for VVV Token Watch.
Provides minimize to tray functionality and notifications.
"""

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QWidget, QApplication
from PySide6.QtCore import Signal, QObject, QSize, Qt
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
import logging
import os

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
        
        # Try to set an icon with multiple fallbacks
        icon = self._load_tray_icon()
        if icon and not icon.isNull():
            self.tray_icon.setIcon(icon)
        else:
            logger.warning("Could not load tray icon, tray may not display correctly")
        
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
    
    def _load_tray_icon(self) -> QIcon:
        """
        Load tray icon with multiple fallback options.
        
        Returns:
            QIcon or None if no icon could be loaded
        """
        import sys
        
        resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "resources"))
        logger.info(f"Loading tray icon from: {resource_dir}")
        
        # Try solid icons first (more visible on semi-transparent backgrounds)
        solid_paths = [
            os.path.join(resource_dir, "app_solid_22.png"),
            os.path.join(resource_dir, "app_solid_16.png"),
            os.path.join(resource_dir, "app_solid_32.png"),
            os.path.join(resource_dir, "app_solid_64.png"),
        ]
        for path in solid_paths:
            if os.path.exists(path):
                icon = QIcon(path)
                if icon and not icon.isNull():
                    logger.info(f"Using solid icon: {path}")
                    return icon
        
        # On macOS, try template icons as fallback (black silhouettes)
        if sys.platform == 'darwin':
            template_paths = [
                os.path.join(resource_dir, "app_template_22.png"),
                os.path.join(resource_dir, "app_template_16.png"),
            ]
            for path in template_paths:
                if os.path.exists(path):
                    icon = QIcon(path)
                    if icon and not icon.isNull():
                        icon.setIsMask(True)
                        logger.info(f"Using macOS template icon: {path}")
                        return icon
        
        # Try standard app icons
        icon_paths = [
            os.path.join(resource_dir, "app_22.png"),
            os.path.join(resource_dir, "app_32.png"),
            os.path.join(resource_dir, "app.png"),
        ]
        for path in icon_paths:
            if os.path.exists(path):
                icon = QIcon(path)
                if icon and not icon.isNull():
                    logger.info(f"Using app icon: {path}")
                    return icon
        
        # Try theme icons (common on Linux)
        theme_icons = ["applications-system", "system-run", "preferences-system"]
        for theme_icon in theme_icons:
            icon = QIcon.fromTheme(theme_icon)
            if icon and not icon.isNull():
                logger.info(f"Using theme icon: {theme_icon}")
                return icon
        
        # Create a simple fallback icon programmatically
        icon = self._create_fallback_icon()
        if icon and not icon.isNull():
            logger.info("Using programmatically created fallback icon")
            return icon
        
        logger.error("Could not load any tray icon")
        return None
    
    def _create_fallback_icon(self) -> QIcon:
        """Create a simple fallback icon programmatically."""
        try:
            # Create a 22x22 icon (typical tray icon size on macOS)
            size = 22
            pixmap = QPixmap(size, size)
            pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw a simple "V" letter on a colored circle
            painter.setBrush(QColor(0, 122, 255))  # Blue color
            painter.setPen(QColor(255, 255, 255))  # White pen
            
            # Draw circle background
            painter.drawEllipse(1, 1, size - 2, size - 2)
            
            # Draw "V" text
            font = QFont("Arial", 12, QFont.Bold)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), QPainter.AlignCenter, "V")
            
            painter.end()
            
            return QIcon(pixmap)
        except Exception as e:
            logger.debug(f"Could not create fallback icon: {e}")
            return QIcon()
    
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
