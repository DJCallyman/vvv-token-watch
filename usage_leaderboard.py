"""
Usage Leaderboard Widget - Interactive API Key Usage Visualization
Provides a sortable, filterable leaderboard view of API token consumption with logarithmic scaling
"""

import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from enum import Enum

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QComboBox, QRadioButton, QButtonGroup, QTableView, 
                               QHeaderView, QStyledItemDelegate, QStyle, QStyleOptionViewItem)
from PySide6.QtCore import (Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, 
                           Signal, QRectF, QPointF)
from PySide6.QtGui import (QPalette, QFont, QColor, QBrush, QPen, QPainter, QIcon, QPixmap)

from usage_tracker import APIKeyUsage


class SortMode(Enum):
    """Sort modes for the leaderboard"""
    USAGE_HIGH_TO_LOW = "Usage (High to Low)"
    USAGE_LOW_TO_HIGH = "Usage (Low to High)"
    NAME_A_TO_Z = "Name (A-Z)"
    LAST_ACTIVE = "Last Active (Recent)"


class FilterStatus(Enum):
    """Filter status for API keys"""
    ALL = "All"
    ACTIVE = "Active"
    IDLE = "Idle"


class UsageBarDelegate(QStyledItemDelegate):
    """Custom delegate for rendering logarithmic usage bars"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_log_value = 1.0  # Will be updated dynamically
    
    def set_max_log_value(self, value: float):
        """Set the maximum logarithmic value for scaling"""
        self.max_log_value = max(value, 1.0)
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        """Paint the usage bar with logarithmic scaling"""
        # Get the usage value
        usage_value = index.data(Qt.UserRole)
        if usage_value is None or usage_value < 0:
            super().paint(painter, option, index)
            return
        
        # Calculate logarithmic value
        log_value = math.log10(usage_value + 1)
        
        # Calculate bar width (proportional to log value)
        if self.max_log_value > 0:
            bar_width_ratio = log_value / self.max_log_value
        else:
            bar_width_ratio = 0
        
        bar_width = int(option.rect.width() * 0.8 * bar_width_ratio)
        bar_height = option.rect.height() - 8
        
        # Draw background
        painter.save()
        
        # Draw the bar
        bar_rect = option.rect.adjusted(4, 4, -4, -4)
        bar_rect.setWidth(max(bar_width, 2))  # Minimum width of 2 pixels
        
        # Determine bar color based on value percentile
        percentile = index.data(Qt.UserRole + 1)
        if percentile is not None and percentile >= 0.75:
            bar_color = QColor(220, 100, 100, 200)  # High usage - red
        elif percentile is not None and percentile >= 0.50:
            bar_color = QColor(220, 180, 100, 200)  # Medium usage - orange
        elif percentile is not None and percentile >= 0.25:
            bar_color = QColor(180, 180, 100, 200)  # Low-medium usage - yellow
        else:
            bar_color = QColor(120, 180, 120, 200)  # Low usage - green
        
        painter.fillRect(bar_rect, bar_color)
        
        # Draw text (usage value)
        text = index.data(Qt.DisplayRole)
        if text:
            painter.setPen(option.palette.text().color())
            text_rect = option.rect.adjusted(bar_width + 8, 0, 0, 0)
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, text)
        
        painter.restore()
    
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex):
        """Provide size hint for the item"""
        size = super().sizeHint(option, index)
        size.setHeight(max(size.height(), 30))
        return size


class UsageLeaderboardModel(QAbstractTableModel):
    """Table model for API key usage leaderboard"""
    
    # Column definitions
    COL_IDENTIFIER = 0
    COL_USAGE = 1
    COL_STATUS = 2
    COL_VISUAL_BAR_7DAY = 3
    COL_VISUAL_BAR_DAILY = 4
    
    COLUMN_COUNT = 5
    
    HEADERS = ["API Key", "7-Day Usage", "Status", "DIEM 7 Day Usage", "DIEM Avg Daily Usage"]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[APIKeyUsage] = []
        self._sort_mode = SortMode.USAGE_HIGH_TO_LOW
        self._filter_status = FilterStatus.ALL
        self._search_text = ""
        self._filtered_data: List[APIKeyUsage] = []
        self._max_usage = 0.0
        self._max_log_value = 1.0
    
    def set_data(self, api_keys: List[APIKeyUsage]):
        """Set the data for the model"""
        self._data = api_keys if api_keys else []
        self._update_max_usage()
        self._apply_filters_and_sort()
    
    def _update_max_usage(self):
        """Update maximum usage value for scaling"""
        if self._data:
            self._max_usage = max(key.usage.diem for key in self._data)
            self._max_log_value = math.log10(self._max_usage + 1) if self._max_usage > 0 else 1.0
        else:
            self._max_usage = 0.0
            self._max_log_value = 1.0
    
    def get_max_log_value(self) -> float:
        """Get the maximum logarithmic value for delegate scaling"""
        return self._max_log_value
    
    def set_sort_mode(self, mode: SortMode):
        """Set the sort mode and re-sort data"""
        self._sort_mode = mode
        self._apply_filters_and_sort()
    
    def set_filter_status(self, status: FilterStatus):
        """Set the filter status and re-filter data"""
        self._filter_status = status
        self._apply_filters_and_sort()
    
    def set_search_text(self, text: str):
        """Set the search text and re-filter data"""
        self._search_text = text.lower()
        self._apply_filters_and_sort()
    
    def _apply_filters_and_sort(self):
        """Apply filters and sorting to the data"""
        self.beginResetModel()
        
        # Start with all data
        filtered = list(self._data)
        
        # Apply search filter
        if self._search_text:
            filtered = [
                key for key in filtered
                if self._search_text in key.name.lower() or 
                   self._search_text in key.id.lower()
            ]
        
        # Apply status filter
        if self._filter_status == FilterStatus.ACTIVE:
            filtered = [key for key in filtered if self._is_active(key)]
        elif self._filter_status == FilterStatus.IDLE:
            filtered = [key for key in filtered if not self._is_active(key)]
        
        # Apply sorting
        if self._sort_mode == SortMode.USAGE_HIGH_TO_LOW:
            # Sort by active status first (active=1, idle=0), then by usage descending
            filtered.sort(key=lambda k: (self._is_active(k), k.usage.diem), reverse=True)
        elif self._sort_mode == SortMode.USAGE_LOW_TO_HIGH:
            # Sort by active status first (active=1, idle=0), then by usage ascending
            filtered.sort(key=lambda k: (self._is_active(k), k.usage.diem), reverse=False)
        elif self._sort_mode == SortMode.NAME_A_TO_Z:
            filtered.sort(key=lambda k: k.name.lower())
        elif self._sort_mode == SortMode.LAST_ACTIVE:
            filtered.sort(key=lambda k: k.last_used_at or "", reverse=True)
        
        self._filtered_data = filtered
        self.endResetModel()
    
    def _is_active(self, key: APIKeyUsage) -> bool:
        """Check if a key is active (used within last 7 days)"""
        # If there's any usage in the 7-day period, consider it active
        if key.usage.diem > 0:
            return True
        
        # Otherwise check the last_used_at timestamp
        if not key.last_used_at:
            return False
        
        try:
            last_used = datetime.fromisoformat(key.last_used_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            delta = now - last_used
            return delta < timedelta(days=7)
        except (ValueError, AttributeError):
            return False
    
    def _get_usage_percentile(self, usage_value: float) -> float:
        """Calculate the percentile rank of a usage value"""
        if not self._data or self._max_usage == 0:
            return 0.0
        return usage_value / self._max_usage
    
    def rowCount(self, parent=QModelIndex()) -> int:
        """Return the number of rows"""
        if parent.isValid():
            return 0
        return len(self._filtered_data)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        """Return the number of columns"""
        if parent.isValid():
            return 0
        return self.COLUMN_COUNT
    
    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        """Return data for the given index and role"""
        if not index.isValid() or index.row() >= len(self._filtered_data):
            return None
        
        key = self._filtered_data[index.row()]
        col = index.column()
        
        # Display role - what text to show
        if role == Qt.DisplayRole:
            if col == self.COL_IDENTIFIER:
                # Return name or truncated ID
                if key.name and key.name.strip() and not key.name.startswith("Key "):
                    return key.name
                else:
                    # Truncate ID: first 8 and last 4 characters
                    if len(key.id) > 12:
                        return f"{key.id[:8]}...{key.id[-4:]}"
                    return key.id
            
            elif col == self.COL_USAGE:
                return f"{key.usage.diem:.4f} DIEM"
            
            elif col == self.COL_STATUS:
                return "Active" if self._is_active(key) else "Idle"
            
            elif col == self.COL_VISUAL_BAR_7DAY:
                return f"{key.usage.diem:.4f}"
            
            elif col == self.COL_VISUAL_BAR_DAILY:
                daily_avg = key.usage.diem / 7.0
                return f"{daily_avg:.4f}"
        
        # Tooltip role - show full ID on hover
        elif role == Qt.ToolTipRole:
            if col == self.COL_IDENTIFIER:
                return f"Full ID: {key.id}"
            elif col == self.COL_USAGE:
                daily_avg = key.usage.diem / 7.0
                return f"7-Day Usage: {key.usage.diem:.4f} DIEM (${key.usage.usd:.2f} USD)\nDaily Average: {daily_avg:.4f} DIEM/day"
            elif col == self.COL_STATUS:
                if key.last_used_at:
                    return f"Last used: {key.last_used_at}"
                return "Never used"
            elif col == self.COL_VISUAL_BAR_7DAY:
                percentile = self._get_usage_percentile(key.usage.diem)
                return f"7-Day Total: {key.usage.diem:.4f} DIEM ({percentile*100:.1f}th percentile)"
            elif col == self.COL_VISUAL_BAR_DAILY:
                daily_avg = key.usage.diem / 7.0
                percentile = self._get_usage_percentile(key.usage.diem)
                return f"Daily Average: {daily_avg:.4f} DIEM/day ({percentile*100:.1f}th percentile)"
        
        # Background role - heat map coloring
        elif role == Qt.BackgroundRole:
            percentile = self._get_usage_percentile(key.usage.diem)
            
            if percentile >= 0.75:
                return QBrush(QColor(255, 200, 200, 30))  # Light red
            elif percentile >= 0.50:
                return QBrush(QColor(255, 240, 200, 30))  # Light orange
            elif percentile >= 0.25:
                return QBrush(QColor(255, 255, 200, 30))  # Light yellow
        
        # Decoration role - status indicator icon
        elif role == Qt.DecorationRole:
            if col == self.COL_STATUS:
                # Create a colored dot icon
                pixmap = QPixmap(16, 16)
                pixmap.fill(Qt.transparent)
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                
                if self._is_active(key):
                    painter.setBrush(QColor(100, 200, 100))  # Green
                else:
                    painter.setBrush(QColor(150, 150, 150))  # Grey
                
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(4, 4, 8, 8)
                painter.end()
                
                return QIcon(pixmap)
        
        # User role - store raw usage value for delegate
        elif role == Qt.UserRole:
            if col == self.COL_VISUAL_BAR_7DAY:
                return key.usage.diem
            elif col == self.COL_VISUAL_BAR_DAILY:
                return key.usage.diem / 7.0
        
        # User role + 1 - store percentile for delegate
        elif role == Qt.UserRole + 1:
            if col == self.COL_VISUAL_BAR_7DAY:
                return self._get_usage_percentile(key.usage.diem)
            elif col == self.COL_VISUAL_BAR_DAILY:
                return self._get_usage_percentile(key.usage.diem)
        
        # User role + 2 - store full key object for details panel
        elif role == Qt.UserRole + 2:
            return key
        
        return None
    
    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        """Return header data"""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            if 0 <= section < len(self.HEADERS):
                return self.HEADERS[section]
        return None


class UsageLeaderboardWidget(QWidget):
    """Interactive leaderboard widget for API key usage visualization"""
    
    # Signals
    row_clicked = Signal(object)  # Emits APIKeyUsage object when row is clicked
    
    def __init__(self, theme_colors: dict, parent=None):
        super().__init__(parent)
        self.theme_colors = theme_colors
        self.model = UsageLeaderboardModel()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Header widget
        header_widget = self.create_header()
        main_layout.addWidget(header_widget)
        
        # Table view
        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        
        # Set column widths
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        
        self.table_view.setColumnWidth(0, 200)
        
        # Install custom delegates for visual bar columns
        self.bar_delegate_7day = UsageBarDelegate()
        self.bar_delegate_daily = UsageBarDelegate()
        self.table_view.setItemDelegateForColumn(UsageLeaderboardModel.COL_VISUAL_BAR_7DAY, self.bar_delegate_7day)
        self.table_view.setItemDelegateForColumn(UsageLeaderboardModel.COL_VISUAL_BAR_DAILY, self.bar_delegate_daily)
        
        # Connect click signal
        self.table_view.clicked.connect(self._on_row_clicked)
        
        # Apply styling
        self.apply_theme()
        
        main_layout.addWidget(self.table_view)
        
        # Empty state label (hidden by default)
        self.empty_label = QLabel("No API keys configured...")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {self.theme_colors.get('text', '#ffffff')}; font-size: 14px;")
        self.empty_label.hide()
        main_layout.addWidget(self.empty_label)
    
    def create_header(self) -> QWidget:
        """Create the header widget with controls"""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title = QLabel("API Usage Leaderboard")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet(f"color: {self.theme_colors.get('text', '#ffffff')};")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Filter by name or ID...")
        self.search_bar.setFixedWidth(200)
        self.search_bar.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.search_bar)
        
        # Sort dropdown
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([mode.value for mode in SortMode])
        self.sort_combo.setCurrentText(SortMode.USAGE_HIGH_TO_LOW.value)
        self.sort_combo.currentTextChanged.connect(self._on_sort_changed)
        layout.addWidget(self.sort_combo)
        
        # Status filter buttons
        filter_label = QLabel("Show:")
        filter_label.setStyleSheet(f"color: {self.theme_colors.get('text', '#ffffff')};")
        layout.addWidget(filter_label)
        
        self.filter_button_group = QButtonGroup()
        self.filter_all = QRadioButton("All")
        self.filter_active = QRadioButton("Active")
        self.filter_idle = QRadioButton("Idle")
        
        self.filter_all.setChecked(True)
        
        self.filter_button_group.addButton(self.filter_all, 0)
        self.filter_button_group.addButton(self.filter_active, 1)
        self.filter_button_group.addButton(self.filter_idle, 2)
        
        self.filter_button_group.buttonClicked.connect(self._on_filter_changed)
        
        layout.addWidget(self.filter_all)
        layout.addWidget(self.filter_active)
        layout.addWidget(self.filter_idle)
        
        return header
    
    def _on_search_changed(self, text: str):
        """Handle search text changes"""
        self.model.set_search_text(text)
        self._update_empty_state()
    
    def _on_sort_changed(self, text: str):
        """Handle sort mode changes"""
        for mode in SortMode:
            if mode.value == text:
                self.model.set_sort_mode(mode)
                # Update delegates with new max log values
                max_log = self.model.get_max_log_value()
                self.bar_delegate_7day.set_max_log_value(max_log)
                max_log_daily = math.log10(self.model._max_usage / 7.0 + 1) if self.model._max_usage > 0 else 1.0
                self.bar_delegate_daily.set_max_log_value(max_log_daily)
                self.table_view.viewport().update()
                break
    
    def _on_filter_changed(self):
        """Handle filter status changes"""
        if self.filter_all.isChecked():
            self.model.set_filter_status(FilterStatus.ALL)
        elif self.filter_active.isChecked():
            self.model.set_filter_status(FilterStatus.ACTIVE)
        elif self.filter_idle.isChecked():
            self.model.set_filter_status(FilterStatus.IDLE)
        
        self._update_empty_state()
    
    def _on_row_clicked(self, index: QModelIndex):
        """Handle row click events"""
        if index.isValid():
            # Get the full key object
            key = self.model.data(self.model.index(index.row(), 0), Qt.UserRole + 2)
            if key:
                self.row_clicked.emit(key)
    
    def set_data(self, api_keys: List[APIKeyUsage]):
        """Update the leaderboard with new data"""
        self.model.set_data(api_keys)
        max_log = self.model.get_max_log_value()
        self.bar_delegate_7day.set_max_log_value(max_log)
        # For daily average, calculate max from daily values
        max_log_daily = math.log10(self.model._max_usage / 7.0 + 1) if self.model._max_usage > 0 else 1.0
        self.bar_delegate_daily.set_max_log_value(max_log_daily)
        self._update_empty_state()
        self.table_view.viewport().update()
    
    def _update_empty_state(self):
        """Update visibility of empty state message"""
        has_data = self.model.rowCount() > 0
        self.table_view.setVisible(has_data)
        self.empty_label.setVisible(not has_data)
    
    def apply_theme(self):
        """Apply theme styling to the widget"""
        bg_color = self.theme_colors.get('background', '#1e1e1e')
        text_color = self.theme_colors.get('text', '#ffffff')
        accent_color = self.theme_colors.get('accent', '#4a9eff')
        
        # Style the table view
        self.table_view.setStyleSheet(f"""
            QTableView {{
                background-color: {bg_color};
                color: {text_color};
                gridline-color: palette(mid);
                border: 1px solid {accent_color};
                border-radius: 5px;
            }}
            QTableView::item {{
                padding: 5px;
            }}
            QTableView::item:selected {{
                background-color: {accent_color};
                color: {text_color};
            }}
            QTableView::item:hover {{
                background-color: palette(dark);
            }}
            QHeaderView::section {{
                background-color: palette(dark);
                color: {text_color};
                padding: 8px;
                border: none;
                border-bottom: 2px solid {accent_color};
                font-weight: bold;
            }}
        """)
        
        # Style search bar
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                background-color: palette(base);
                color: {text_color};
                border: 1px solid {accent_color};
                border-radius: 4px;
                padding: 5px;
            }}
            QLineEdit:focus {{
                border: 2px solid {accent_color};
            }}
        """)
        
        # Style combo box
        self.sort_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: palette(base);
                color: {text_color};
                border: 1px solid {accent_color};
                border-radius: 4px;
                padding: 5px;
                min-width: 150px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: palette(base);
                color: {text_color};
                selection-background-color: {accent_color};
            }}
        """)
        
        # Style radio buttons
        radio_style = f"""
            QRadioButton {{
                color: {text_color};
                spacing: 5px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
            }}
            QRadioButton::indicator:checked {{
                background-color: {accent_color};
                border: 2px solid {accent_color};
                border-radius: 8px;
            }}
            QRadioButton::indicator:unchecked {{
                background-color: transparent;
                border: 2px solid palette(mid);
                border-radius: 8px;
            }}
        """
        
        self.filter_all.setStyleSheet(radio_style)
        self.filter_active.setStyleSheet(radio_style)
        self.filter_idle.setStyleSheet(radio_style)
