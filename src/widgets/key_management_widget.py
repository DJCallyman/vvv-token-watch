"""
API Key Management Widget for Phase 3 enhancements.
Provides interactive management with dropdown menus and actions.
"""

from functools import partial

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QMenu, QDialog, QLineEdit, QTextEdit, QDialogButtonBox,
                              QMessageBox, QFrame)
from PySide6.QtCore import Signal, QTimer
from PySide6.QtGui import QFont, QAction
from typing import Dict, Optional

from src.core.usage_tracker import APIKeyUsage, BalanceInfo
from src.utils.date_utils import DateFormatter


class KeyActionMenu(QMenu):
    """Dropdown menu for API key actions"""
    
    usage_report_requested = Signal(str) # key_id
    revoke_requested = Signal(str)       # key_id
    
    def __init__(self, key_id: str, key_name: str, parent=None):
        super().__init__(parent)
        self.key_id = key_id
        self.key_name = key_name
        self.setup_actions()
    
    def setup_actions(self):
        """Setup the action menu items"""
        # Usage Report action
        usage_action = QAction("📊 Usage Report", self)
        usage_action.setStatusTip("View detailed usage analytics for this key")
        usage_action.triggered.connect(partial(self.emit_usage_report))
        self.addAction(usage_action)
        
        self.addSeparator()
        
        # Revoke Key action (dangerous)
        revoke_action = QAction("🗑️ Revoke Key", self)
        revoke_action.setStatusTip("Permanently disable this API key (irreversible)")
        revoke_action.triggered.connect(partial(self.emit_revoke_request))
        self.addAction(revoke_action)
    
    def emit_usage_report(self):
        """Emit usage report request signal for this key"""
        self.usage_report_requested.emit(self.key_id)
    
    def emit_revoke_request(self):
        """Emit revoke request signal for this key"""
        self.revoke_requested.emit(self.key_id)


class RenameKeyDialog(QDialog):
    """Dialog for renaming an API key"""
    
    def __init__(self, current_name: str, parent=None):
        super().__init__(parent)
        self.current_name = current_name
        self.new_name = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Rename API Key")
        self.setModal(True)
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("Rename API Key")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title_label)
        
        # Current name
        current_label = QLabel(f"Current name: {self.current_name}")
        current_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(current_label)
        
        # New name input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter new name...")
        self.name_input.setText(self.current_name)
        self.name_input.selectAll()
        layout.addWidget(self.name_input)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_rename)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        self.name_input.setFocus()
    
    def accept_rename(self):
        """Accept the rename if valid"""
        new_name = self.name_input.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a valid name.")
            return
        
        if new_name == self.current_name:
            self.reject()  # No change
            return
        
        self.new_name = new_name

class UsageReportDialog(QDialog):
    """Dialog showing detailed usage report for an API key"""
    
    def __init__(self, api_key_usage: APIKeyUsage, parent=None):
        super().__init__(parent)
        self.api_key_usage = api_key_usage
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the usage report dialog UI"""
        self.setWindowTitle(f"Usage Report - {self.api_key_usage.name}")
        self.setModal(True)
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel(f"Usage Report: {self.api_key_usage.name}")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title_label)
        
        # Created date
        try:
            formatted_date = DateFormatter.human_friendly(self.api_key_usage.created_at)
        except (ValueError, TypeError, AttributeError, KeyError):
            formatted_date = self.api_key_usage.created_at
        
        created_label = QLabel(f"Created: {formatted_date}")
        created_label.setStyleSheet("color: #666; margin-bottom: 20px;")
        layout.addWidget(created_label)
        
        # Usage summary
        usage_text = QTextEdit()
        usage_text.setReadOnly(True)
        usage_content = self.generate_usage_report()
        usage_text.setPlainText(usage_content)
        layout.addWidget(usage_text)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
    
    def generate_usage_report(self) -> str:
        """Generate detailed usage report text"""
        usage = self.api_key_usage.usage
        
        report = f"""USAGE SUMMARY (7-day trailing)
=====================================

DIEM Usage: {usage.diem:.4f} DIEM"""

        # Only show USD if > 0
        if usage.usd > 0:
            report += f"""
USD Equivalent: ${usage.usd:.2f}"""

        report += f"""

USAGE BREAKDOWN
=====================================

DIEM Daily Average: {usage.diem / 7:.4f} DIEM/day
DIEM Weekly Total: {usage.diem:.4f} DIEM
DIEM Monthly Projection: {usage.diem * 4.3:.4f} DIEM"""

        # Only show USD breakdown if > 0
        if usage.usd > 0:
            report += f"""

USD Daily Average: ${usage.usd / 7:.2f} USD/day
USD Weekly Total: ${usage.usd:.2f} USD
USD Monthly Projection: ${usage.usd * 4.3:.2f} USD"""

        report += f"""

RECOMMENDATIONS
=====================================

"""

        # Check if key was used recently (within last 24 hours)
        recently_used = False
        if self.api_key_usage.last_used_at:
            try:
                from datetime import datetime, timezone
                last_used = datetime.fromisoformat(self.api_key_usage.last_used_at.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                hours_since_used = (now - last_used).total_seconds() / 3600
                recently_used = hours_since_used < 24
            except (ValueError, TypeError, AttributeError):
                recently_used = False
        
        if recently_used:
            if usage.usd < 1:
                report += "• Low usage key - suitable for testing.\n"
            elif usage.usd < 10:
                report += "• Moderate usage - good for development.\n"
            else:
                report += "• High usage key - monitor closely.\n"
        elif usage.usd > 0:
            report += "• Key has usage but not recently active.\n"
            report += "• Consider reviewing usage patterns.\n"
        else:
            report += "• This key has no recent usage.\n"
            report += "• Consider removing if no longer needed.\n"
        
        return report


class APIKeyManagementWidget(QWidget):
    """Enhanced API Key widget with management actions"""
    
    # Signals for management actions
    key_revoked = Signal(str)               # key_id
    
    def __init__(self, api_key_usage: APIKeyUsage, theme_colors: Dict[str, str], balance_info: BalanceInfo = None, parent=None):
        super().__init__(parent)
        self.api_key_usage = api_key_usage
        self.theme_colors = theme_colors
        self.balance_info = balance_info  # Daily limits information
        self.last_used_at = None  # Will be populated with security monitoring data
        
        # Action menu
        self.action_menu = None
        
        self.init_ui()
        self.setup_connections()
    
    def init_ui(self):
        """Initialize the user interface components"""
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Header with key info and actions
        header_layout = QHBoxLayout()
        
        # Key name and info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Key name
        self.name_label = QLabel(self.api_key_usage.name)
        self.name_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.name_label.setStyleSheet(f"color: {self.theme_colors['text_primary']};")
        info_layout.addWidget(self.name_label)
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        # Action button (three dots)
        self.action_button = QPushButton("⋮")
        self.action_button.setFixedSize(24, 24)
        self.action_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme_colors['button_background']};
                border: 1px solid {self.theme_colors['border']};
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
                color: {self.theme_colors['text_secondary']};
            }}
            QPushButton:hover {{
                background-color: {self.theme_colors['button_hover']};
                color: {self.theme_colors['text_primary']};
            }}
            QPushButton:pressed {{
                background-color: {self.theme_colors['button_pressed']};
            }}
        """)
        self.action_button.clicked.connect(self.show_action_menu)
        header_layout.addWidget(self.action_button)
        
        layout.addLayout(header_layout)
        
        # Status and security info
        status_layout = QHBoxLayout()
        
        # Active status indicator
        self.active_status = QFrame()
        self.active_status.setFixedSize(10, 10)
        color = self.theme_colors['positive'] if self.api_key_usage.is_active else self.theme_colors['negative']
        self.active_status.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        status_layout.addWidget(self.active_status)
        
        self.active_label = QLabel("Active" if self.api_key_usage.is_active else "Inactive")
        self.active_label.setFont(QFont("Arial", 8))
        self.active_label.setStyleSheet(f"color: {self.theme_colors['text_secondary']};")
        status_layout.addWidget(self.active_label)
        
        status_layout.addWidget(QLabel("•"))  # Separator
        
        # Created date
        try:
            formatted_date = DateFormatter.relative_time(self.api_key_usage.created_at)
        except (ValueError, TypeError, AttributeError, KeyError):
            formatted_date = self.api_key_usage.created_at[:10]
        
        self.created_label = QLabel(f"Created {formatted_date}")
        self.created_label.setFont(QFont("Arial", 8))
        self.created_label.setStyleSheet(f"color: {self.theme_colors['text_secondary']};")
        status_layout.addWidget(self.created_label)
        
        status_layout.addWidget(QLabel("•"))  # Separator
        
        # Last used timestamp (Phase 3 security monitoring)
        self.last_used_label = QLabel("Last used: Never")
        self.last_used_label.setFont(QFont("Arial", 8))
        self.last_used_label.setStyleSheet(f"color: {self.theme_colors['error']};")
        status_layout.addWidget(self.last_used_label)
        
        status_layout.addStretch()
        
        layout.addLayout(status_layout)
        
        # Usage metrics - showing 7-day trailing usage
        usage_layout = QVBoxLayout()
        usage_layout.setSpacing(4)
        
        # DIEM usage (always show)
        diem_layout = QHBoxLayout()
        diem_label = QLabel("DIEM 7d:")
        diem_label.setFont(QFont("Arial", 9))
        diem_label.setStyleSheet(f"color: {self.theme_colors['text_secondary']};")
        diem_layout.addWidget(diem_label)

        # Always show DIEM value
        diem_value = self.api_key_usage.usage.diem
        self.diem_usage_label = QLabel(f"{diem_value:.4f}")
        self.diem_usage_label.setFont(QFont("Arial", 9, QFont.Bold))
        self.diem_usage_label.setStyleSheet(f"color: {self.theme_colors['text_primary']};")
        diem_layout.addWidget(self.diem_usage_label)

        diem_layout.addStretch()

        usage_layout.addLayout(diem_layout)
        
        # USD usage (only show if > 0)
        usd_value = self.api_key_usage.usage.usd
        if usd_value > 0:
            self.usd_layout = QHBoxLayout()
            usd_label = QLabel("USD 7d:")
            usd_label.setFont(QFont("Arial", 9))
            usd_label.setStyleSheet(f"color: {self.theme_colors['text_secondary']};")
            self.usd_layout.addWidget(usd_label)
            
            self.usd_usage_label = QLabel(f"${usd_value:.2f}")
            self.usd_usage_label.setFont(QFont("Arial", 9, QFont.Bold))
            self.usd_usage_label.setStyleSheet(f"color: {self.theme_colors['text_primary']};")
            self.usd_layout.addWidget(self.usd_usage_label)
            
            self.usd_layout.addStretch()
            
            usage_layout.addLayout(self.usd_layout)
        else:
            # Keep references as None for widgets that aren't created
            self.usd_layout = None
            self.usd_usage_label = None
        
        layout.addLayout(usage_layout)
        
        self.setLayout(layout)
        
        # Apply styling
        self.setStyleSheet(f"""
            APIKeyManagementWidget {{
                background-color: {self.theme_colors['card_background']};
                border-radius: 10px;
                border: 1px solid {self.theme_colors['border']};
            }}
        """)
    
    def setup_connections(self):
        """Setup signal connections"""
        pass  # Connections will be made when action menu is created
    
    def show_action_menu(self):
        """Show the action menu"""
        if not self.action_menu:
            self.action_menu = KeyActionMenu(self.api_key_usage.id, self.api_key_usage.name, self)
            
            # Connect action menu signals
            self.action_menu.usage_report_requested.connect(self.handle_usage_report_request)
            self.action_menu.revoke_requested.connect(self.handle_revoke_request)
        
        # Show menu at button position
        button_pos = self.action_button.mapToGlobal(self.action_button.rect().bottomLeft())
        self.action_menu.exec_(button_pos)
    
    def handle_rename_request(self, key_id: str):
        """Handle rename key request"""
        dialog = RenameKeyDialog(self.api_key_usage.name, self)
        if dialog.exec_() == QDialog.Accepted and dialog.new_name:
            self.api_key_usage.name = dialog.new_name
            self.name_label.setText(dialog.new_name)
            self.key_renamed.emit(key_id, dialog.new_name)
            
            # Show success message
    def handle_usage_report_request(self, key_id: str):
        """Handle usage report request"""
        dialog = UsageReportDialog(self.api_key_usage, self)
        dialog.exec_()
    
    def handle_revoke_request(self, key_id: str):
        """Handle revoke key request"""
        reply = QMessageBox.question(
            self,
            "Revoke API Key",
            f"Are you sure you want to revoke the key '{self.api_key_usage.name}'?\n\n"
            "This action cannot be undone and the key will be permanently disabled.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.key_revoked.emit(key_id)
            
            # Update UI to show revoked state
            self.api_key_usage.is_active = False
            self.update_active_status()
            self.show_temporary_status("Key revoked successfully!", "warning")
    
    def show_temporary_status(self, message: str, status_type: str = "positive"):
        """Show a temporary status message"""
        original_text = self.last_used_label.text()
        original_color = self.last_used_label.styleSheet()
        
        # Update with status message
        color = self.theme_colors.get(status_type, self.theme_colors['text_primary'])
        self.last_used_label.setText(message)
        self.last_used_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        
        # Restore original text after 3 seconds
        QTimer.singleShot(3000, lambda: (
            self.last_used_label.setText(original_text),
            self.last_used_label.setStyleSheet(original_color)
        ))
    
    def update_last_used(self, last_used_at: Optional[str]):
        """Update the last used timestamp (Phase 3 security monitoring)"""
        self.last_used_at = last_used_at
        
        if not last_used_at:
            self.last_used_label.setText("Last used: Never")
            self.last_used_label.setStyleSheet(f"color: {self.theme_colors['error']};")
        else:
            try:
                formatted_time = DateFormatter.relative_time(last_used_at)
                self.last_used_label.setText(f"Last used: {formatted_time}")
                
                # Color code based on recency
                from datetime import datetime
                last_used = datetime.fromisoformat(last_used_at.replace('Z', '+00:00'))
                now = datetime.now(last_used.tzinfo)
                days_ago = (now - last_used).days
                
                if days_ago <= 1:
                    color = self.theme_colors['positive']  # Recent usage
                elif days_ago <= 7:
                    color = self.theme_colors['text_secondary']  # Moderate
                else:
                    color = self.theme_colors['warning']  # Old usage
                    
                self.last_used_label.setStyleSheet(f"color: {color};")
            except (ValueError, TypeError, AttributeError):
                self.last_used_label.setText(f"Last used: {last_used_at[:10]}")
                self.last_used_label.setStyleSheet(f"color: {self.theme_colors['text_secondary']};")
    
    def update_active_status(self):
        """Update the active status indicator"""
        color = self.theme_colors['positive'] if self.api_key_usage.is_active else self.theme_colors['negative']
        self.active_status.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        self.active_label.setText("Active" if self.api_key_usage.is_active else "Inactive")
    
    def _update_progress_bars(self):
        """
        Update usage display values (no longer uses progress bars).
        Kept for backward compatibility with existing code that calls this method.
        """
        # This method is now a no-op since we removed progress bars
        # The labels are updated directly in update_usage() method
    
    def update_usage(self, api_key_usage: APIKeyUsage):
        """Update the widget with new API key usage data"""
        self.api_key_usage = api_key_usage
        
        # Update labels
        self.name_label.setText(api_key_usage.name)
        
        # Update active status
        self.update_active_status()
        
        # Update DIEM usage value
        self.diem_usage_label.setText(f"{api_key_usage.usage.diem:.4f}")
        
        # Update USD usage value only if it exists and value > 0
        if self.usd_usage_label is not None:
            if api_key_usage.usage.usd > 0:
                self.usd_usage_label.setText(f"${api_key_usage.usage.usd:.2f}")
            else:
                # Hide the USD layout if it drops to 0
                if self.usd_layout is not None:
                    # Remove USD layout from display
                    while self.usd_layout.count():
                        item = self.usd_layout.takeAt(0)
                        if item.widget():
                            item.widget().deleteLater()
                    self.usd_layout.deleteLater()
                    self.usd_layout = None
                    self.usd_usage_label = None
    
    def update_balance_info(self, balance_info: BalanceInfo):
        """Update the widget with new balance/limit information"""
        self.balance_info = balance_info
        # No longer used for progress bars, kept for compatibility
    
    def set_theme_colors(self, theme_colors: Dict[str, str]):
        """Update theme colors and refresh styling"""
        self.theme_colors = theme_colors
        
        # Reapply styling
        self.name_label.setStyleSheet(f"color: {theme_colors['text_primary']};")
        self.active_label.setStyleSheet(f"color: {theme_colors['text_secondary']};")
        self.created_label.setStyleSheet(f"color: {theme_colors['text_secondary']};")
        self.diem_usage_label.setStyleSheet(f"color: {theme_colors['text_primary']};")
        if self.usd_usage_label:
            self.usd_usage_label.setStyleSheet(f"color: {theme_colors['text_primary']};")
        
        # Update status colors
        self.update_active_status()
        
        # Update action button
        self.action_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_colors['button_background']};
                border: 1px solid {theme_colors['border']};
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
                color: {theme_colors['text_secondary']};
            }}
            QPushButton:hover {{
                background-color: {theme_colors['button_hover']};
                color: {theme_colors['text_primary']};
            }}
            QPushButton:pressed {{
                background-color: {theme_colors['button_pressed']};
            }}
        """)
        
        # Update main widget styling
        self.setStyleSheet(f"""
            APIKeyManagementWidget {{
                background-color: {theme_colors['card_background']};
                border-radius: 10px;
                border: 1px solid {theme_colors['border']};
            }}
        """)