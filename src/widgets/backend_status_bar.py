"""
Comprehensive backend status bar widget for tracking multiple background processes.

This module provides a complete status dashboard that shows:
- Animated status icons for each running process
- Progress bar for overall activity
- Operation queue with timestamps and status
- Expandable details panel
- Error notifications
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import deque
from enum import Enum

from PySide6.QtWidgets import (
    QStatusBar, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QToolButton, QScrollArea, QSizePolicy,
    QGraphicsOpacityEffect, QApplication
)
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, Signal, QTimer,
    QParallelAnimationGroup, Property
)
from PySide6.QtGui import QFont, QIcon, QPainter, QColor, QBrush

from src.config.theme import Theme


logger = logging.getLogger(__name__)


class ProcessStatus(Enum):
    """Status states for backend processes."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class ProcessInfo:
    """Information about a single backend process."""
    
    def __init__(self, process_id: str, name: str, status: ProcessStatus = ProcessStatus.IDLE,
                 message: str = "", progress: int = 0, timestamp: datetime = None):
        self.process_id = process_id
        self.name = name
        self.status = status
        self.message = message
        self.progress = progress
        self.timestamp = timestamp or datetime.now()
        self.details = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for display."""
        return {
            'id': self.process_id,
            'name': self.name,
            'status': self.status.value,
            'message': self.message,
            'progress': self.progress,
            'timestamp': self.timestamp.strftime('%H:%M:%S'),
            'details': self.details
        }


class AnimatedStatusIcon(QWidget):
    """Animated status icon with pulsing/spinning effects."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.current_status = ProcessStatus.IDLE
        self.animation_group = None
        self.pulse_value = 1.0
        self._setup_animations()
    
    def _setup_animations(self):
        """Setup pulse animation for running status."""
        self.pulse_animation = QPropertyAnimation(self, b"pulse_opacity")
        self.pulse_animation.setDuration(1000)
        self.pulse_animation.setStartValue(1.0)
        self.pulse_animation.setEndValue(0.3)
        self.pulse_animation.setLoopCount(-1)  # Infinite loop
    
    @Property(float)
    def pulse_opacity(self):
        return self.pulse_value
    
    @pulse_opacity.setter
    def pulse_opacity(self, value):
        self.pulse_value = value
        self.update()
    
    def set_status(self, status: ProcessStatus):
        """Set the status and update animation."""
        self.current_status = status
        
        if status == ProcessStatus.RUNNING:
            self.pulse_animation.start()
        else:
            self.pulse_animation.stop()
            self.pulse_value = 1.0
            self.update()
    
    def paintEvent(self, event):
        """Paint the status icon."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get colors based on status
        colors = {
            ProcessStatus.IDLE: QColor(128, 128, 128),
            ProcessStatus.RUNNING: QColor(59, 130, 246),    # Blue
            ProcessStatus.SUCCESS: QColor(34, 197, 94),     # Green
            ProcessStatus.ERROR: QColor(239, 68, 68),       # Red
            ProcessStatus.WARNING: QColor(234, 179, 8),     # Yellow
        }
        
        color = colors.get(self.current_status, QColor(128, 128, 128))
        
        # Apply pulse effect for running status
        if self.current_status == ProcessStatus.RUNNING:
            color = QColor(color.red(), color.green(), color.blue(), int(255 * self.pulse_value))
        
        # Draw circle background
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 16, 16)
        
        # Draw symbol
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        
        symbols = {
            ProcessStatus.IDLE: "○",
            ProcessStatus.RUNNING: "↻",
            ProcessStatus.SUCCESS: "✓",
            ProcessStatus.ERROR: "✗",
            ProcessStatus.WARNING: "!",
        }
        
        symbol = symbols.get(self.current_status, "?")
        painter.drawText(self.rect(), Qt.AlignCenter, symbol)


class ProcessStatusWidget(QWidget):
    """Individual process status display with icon and info."""
    
    clicked = Signal(str)  # process_id
    
    def __init__(self, process_info: ProcessInfo, parent=None):
        super().__init__(parent)
        self.process_info = process_info
        self._setup_ui()
        self._update_display()
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 8, 2)
        layout.setSpacing(6)
        layout.addStretch()
        
        # Status icon
        self.status_icon = AnimatedStatusIcon()
        layout.addWidget(self.status_icon)
        
        # Process name
        self.name_label = QLabel()
        self.name_label.setFont(QFont("Arial", 9))
        layout.addWidget(self.name_label)
        
        # Status message
        self.message_label = QLabel()
        self.message_label.setFont(QFont("Arial", 8))
        self.message_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.message_label)
        
        # Progress bar (only shown when running)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(60)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Make clickable
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            ProcessStatusWidget {
                background-color: transparent;
                border-radius: 4px;
                padding: 2px;
            }
            ProcessStatusWidget:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
    
    def _update_display(self):
        """Update the display with current process info."""
        self.status_icon.set_status(self.process_info.status)
        self.name_label.setText(self.process_info.name)
        
        # Update message
        if self.process_info.message:
            self.message_label.setText(self.process_info.message)
            self.message_label.setVisible(True)
        else:
            self.message_label.setVisible(False)
        
        # Update progress bar
        if self.process_info.status == ProcessStatus.RUNNING:
            self.progress_bar.setValue(self.process_info.progress)
            self.progress_bar.setVisible(True)
        else:
            self.progress_bar.setVisible(False)
        
        # Update tooltip
        info = self.process_info.to_dict()
        tooltip = f"""
        <b>{info['name']}</b><br>
        Status: {info['status'].upper()}<br>
        Time: {info['timestamp']}<br>
        {f"Progress: {info['progress']}%" if info['progress'] > 0 else ""}
        {f"<br>Message: {info['message']}" if info['message'] else ""}
        """
        self.setToolTip(tooltip)
    
    def update_info(self, process_info: ProcessInfo):
        """Update the process info and refresh display."""
        self.process_info = process_info
        self._update_display()
    
    def mousePressEvent(self, event):
        """Handle click to emit signal."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.process_info.process_id)


class OperationHistoryWidget(QWidget):
    """Widget showing recent operation history."""
    
    MAX_ITEMS = 10
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = deque(maxlen=self.MAX_ITEMS)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Header
        header = QLabel("Recent Operations")
        header.setFont(QFont("Arial", 9, QFont.Bold))
        header.setStyleSheet("color: #AAAAAA;")
        layout.addWidget(header)
        
        # History list
        self.history_list = QVBoxLayout()
        self.history_list.setSpacing(1)
        layout.addLayout(self.history_list)
        
        # Add stretch
        layout.addStretch()
    
    def add_entry(self, process_info: ProcessInfo):
        """Add a new entry to the history, deduplicating similar entries."""
        # Check if we already have a similar recent entry (same process, same status)
        for existing in self.history:
            if (existing.process_id == process_info.process_id and
                existing.status == process_info.status):
                # Update the timestamp and message instead of adding duplicate
                process_info.timestamp = existing.timestamp  # Keep original timestamp
                self.history.remove(existing)
                break
        
        self.history.append(process_info)
        self._update_display()
    
    def _update_display(self):
        """Update the history display."""
        # Clear existing items
        while self.history_list.count():
            item = self.history_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add recent items in reverse order (newest first)
        for process_info in reversed(list(self.history)):
            entry = self._create_history_entry(process_info)
            self.history_list.addWidget(entry)
    
    def _create_history_entry(self, process_info: ProcessInfo) -> QWidget:
        """Create a single history entry widget."""
        entry = QWidget()
        layout = QHBoxLayout(entry)
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(6)
        
        # Status icon
        icon = AnimatedStatusIcon()
        icon.set_status(process_info.status)
        icon.setFixedSize(14, 14)
        layout.addWidget(icon)
        
        # Name and message
        text = process_info.name
        if process_info.message:
            text += f" - {process_info.message}"
        
        label = QLabel(text)
        label.setFont(QFont("Arial", 8))
        label.setStyleSheet("color: #888888;")
        layout.addWidget(label)
        
        # Timestamp
        time_label = QLabel(process_info.timestamp.strftime('%H:%M:%S'))
        time_label.setFont(QFont("Arial", 7))
        time_label.setStyleSheet("color: #666666;")
        layout.addWidget(time_label)
        
        return entry
    
    def clear(self):
        """Clear the history."""
        self.history.clear()
        self._update_display()


class BackendStatusBar(QStatusBar):
    """
    Comprehensive backend status bar dashboard.
    
    Features:
    - Animated status icons for each running process
    - Progress bar for overall activity
    - Operation queue with timestamps and status
    - Expandable details panel
    - Error notifications
    - QStatusBar compatibility (showMessage method)
    """
    
    # Signals
    process_clicked = Signal(str)  # process_id
    clear_errors_requested = Signal()
    refresh_all_requested = Signal()
    
    # Default process IDs for common backend operations
    PROCESS_MODELS = "models_fetch"
    PROCESS_USAGE = "usage_fetch"
    PROCESS_PRICES = "prices_fetch"
    PROCESS_DIEM_PRICES = "diem_prices_fetch"
    PROCESS_WEB_USAGE = "web_usage_fetch"
    PROCESS_COST_ANALYSIS = "cost_analysis"
    PROCESS_BALANCE = "balance_fetch"
    PROCESS_EXCHANGE_RATE = "exchange_rate"
    PROCESS_VIDEO_QUOTES = "video_quotes"
    
    def __init__(self, theme: Theme = None, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.processes: Dict[str, ProcessInfo] = {}
        self.error_count = 0
        self._setup_ui()
        self._setup_animations()
        self._setup_timers()
        self._initialize_default_processes()
    
    def _setup_ui(self):
        """Setup the main UI layout."""
        # Create a container widget for our custom layout
        self.central_widget = QWidget()
        self.central_widget.setObjectName("BackendStatusBarContainer")
        
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(2)
        
        # Add the container to the status bar
        self.addWidget(self.central_widget, 1)  # Stretch factor of 1
        
        # Top row: Status icons and process info
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        
        # Process status container (scrollable if many processes)
        self.process_container = QWidget()
        self.process_layout = QHBoxLayout(self.process_container)
        self.process_layout.setContentsMargins(0, 0, 0, 0)
        self.process_layout.setSpacing(4)
        self.process_layout.addStretch()
        
        # Wrap in scroll area for horizontal scrolling
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.process_container)
        self.scroll_area.setMaximumHeight(30)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea QWidget {
                background: transparent;
            }
            QScrollBar:horizontal {
                height: 6px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 3px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 3px;
                min-width: 20px;
            }
        """)
        top_row.addWidget(self.scroll_area, 1)
        
        # Activity summary
        self.activity_summary = QLabel("Idle")
        self.activity_summary.setFont(QFont("Arial", 9))
        self.activity_summary.setStyleSheet("color: #888888; min-width: 120px;")
        self.activity_summary.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top_row.addWidget(self.activity_summary)
        
        # Error counter
        self.error_button = QPushButton("✓ 0")
        self.error_button.setFixedSize(45, 22)
        self.error_button.setFont(QFont("Arial", 8))
        self.error_button.setStyleSheet("""
            QPushButton {
                background-color: #22C55E;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #16A34A;
            }
        """)
        self.error_button.clicked.connect(self._on_error_button_clicked)
        top_row.addWidget(self.error_button)
        
        # Details toggle button
        self.details_button = QPushButton("▼")
        self.details_button.setFixedSize(30, 22)
        self.details_button.setFont(QFont("Arial", 8))
        self.details_button.setCheckable(True)
        self.details_button.setChecked(False)
        self.details_button.toggled.connect(self._on_details_toggled)
        top_row.addWidget(self.details_button)
        
        # Refresh button
        self.refresh_button = QPushButton("↻")
        self.refresh_button.setFixedSize(22, 22)
        self.refresh_button.setFont(QFont("Arial", 10))
        self.refresh_button.setToolTip("Refresh all processes")
        self.refresh_button.clicked.connect(self.refresh_all_requested.emit)
        top_row.addWidget(self.refresh_button)
        
        main_layout.addLayout(top_row)
        
        # Progress bar (compact)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #3B82F6;
                border-radius: 2px;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # Details panel (expandable)
        self.details_widget = QWidget()
        self.details_layout = QVBoxLayout(self.details_widget)
        self.details_layout.setContentsMargins(0, 2, 0, 0)
        self.details_widget.setVisible(False)
        main_layout.addWidget(self.details_widget)
        
        # Add operation history to details
        self.history_widget = OperationHistoryWidget()
        self.details_layout.addWidget(self.history_widget)
    
    # QStatusBar compatibility methods
    def showMessage(self, message: str, timeout: int = 0):
        """
        Show a temporary message in the status bar (compatibility with QStatusBar).
        
        Args:
            message: Message to display
            timeout: Milliseconds before message disappears (0 = no timeout)
        """
        # For our comprehensive status bar, we set the activity summary
        # and optionally show in details panel
        self.activity_summary.setText(message)
        
        if timeout > 0:
            # Auto-clear after timeout
            QTimer.singleShot(timeout, lambda: self.activity_summary.setText("Idle"))
    
    def clearMessage(self):
        """Clear the current message (compatibility with QStatusBar)."""
        self.activity_summary.setText("Idle")
    
    def _setup_animations(self):
        """Setup animations for smooth transitions."""
        self.opacity_effect = QGraphicsOpacityEffect(self.details_widget)
        self.details_widget.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(200)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)
    
    def _setup_timers(self):
        """Setup timers for periodic updates."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_activity_summary)
        self.update_timer.start(1000)  # Update every second
    
    def _initialize_default_processes(self):
        """Initialize default backend processes."""
        default_processes = [
            (self.PROCESS_MODELS, "Models", "Fetching model data"),
            (self.PROCESS_USAGE, "Usage", "Loading API usage"),
            (self.PROCESS_PRICES, "Prices", "Updating token prices"),
            (self.PROCESS_DIEM_PRICES, "DIEM", "Updating DIEM prices"),
            (self.PROCESS_WEB_USAGE, "Web Usage", "Loading web app usage"),
            (self.PROCESS_COST_ANALYSIS, "Cost Analysis", "Analyzing costs"),
            (self.PROCESS_BALANCE, "Balance", "Refreshing balance"),
            (self.PROCESS_EXCHANGE_RATE, "Exchange", "Updating rates"),
            (self.PROCESS_VIDEO_QUOTES, "Video Quotes", "Fetching quotes"),
        ]
        
        for process_id, name, default_message in default_processes:
            self.register_process(process_id, name, default_message)
    
    def register_process(self, process_id: str, name: str, default_message: str = ""):
        """
        Register a new backend process to track.
        
        Args:
            process_id: Unique identifier for the process
            name: Display name for the process
            default_message: Default status message
        """
        if process_id in self.processes:
            return  # Already registered
        
        process_info = ProcessInfo(
            process_id=process_id,
            name=name,
            status=ProcessStatus.IDLE,
            message=default_message
        )
        self.processes[process_id] = process_info
        
        # Create UI widget
        widget = ProcessStatusWidget(process_info)
        widget.clicked.connect(self.process_clicked.emit)
        self.process_layout.insertWidget(self.process_layout.count() - 1, widget)
    
    def unregister_process(self, process_id: str):
        """Unregister a process and remove its UI widget."""
        if process_id not in self.processes:
            return
        
        del self.processes[process_id]
        
        # Remove UI widget
        for i in range(self.process_layout.count()):
            item = self.process_layout.itemAt(i)
            if item.widget() and hasattr(item.widget(), 'process_info'):
                if item.widget().process_info.process_id == process_id:
                    item.widget().deleteLater()
                    break
    
    def set_process_status(self, process_id: str, status: ProcessStatus, 
                           message: str = "", progress: int = 0):
        """
        Update the status of a tracked process.
        
        Args:
            process_id: Process identifier
            status: New status
            message: Status message
            progress: Progress percentage (0-100)
        """
        if process_id not in self.processes:
            logger.warning(f"Process {process_id} not registered")
            return
        
        process_info = self.processes[process_id]
        old_status = process_info.status
        process_info.status = status
        process_info.message = message
        process_info.progress = progress
        process_info.timestamp = datetime.now()
        
        # Update UI widget
        for i in range(self.process_layout.count()):
            item = self.process_layout.itemAt(i)
            if item.widget() and hasattr(item.widget(), 'process_info'):
                if item.widget().process_info.process_id == process_id:
                    item.widget().update_info(process_info)
                    break
        
        # Add to history on status change
        if old_status != status:
            self.history_widget.add_entry(process_info)
        
        # Update error count
        self._update_error_count()
        
        # Update progress bar
        self._update_progress_bar()
        
        # Update activity summary
        self._update_activity_summary()
    
    def set_process_success(self, process_id: str, message: str = "Completed"):
        """Mark a process as completed successfully."""
        self.set_process_status(process_id, ProcessStatus.SUCCESS, message, 100)
    
    def set_process_error(self, process_id: str, message: str = "Error"):
        """Mark a process as errored."""
        self.set_process_status(process_id, ProcessStatus.ERROR, message)
        self.error_count += 1
        self._update_error_count()
    
    def set_process_running(self, process_id: str, message: str = "Running...", progress: int = 0):
        """Mark a process as running."""
        self.set_process_status(process_id, ProcessStatus.RUNNING, message, progress)
    
    def set_process_idle(self, process_id: str, message: str = ""):
        """Mark a process as idle."""
        self.set_process_status(process_id, ProcessStatus.IDLE, message)
    
    def set_process_warning(self, process_id: str, message: str = "Warning"):
        """Mark a process with a warning status."""
        self.set_process_status(process_id, ProcessStatus.WARNING, message)
        self._update_error_count()
    
    def get_process_status(self, process_id: str) -> Optional[ProcessInfo]:
        """Get the current status of a process."""
        return self.processes.get(process_id)
    
    def get_all_processes(self) -> List[ProcessInfo]:
        """Get all registered processes."""
        return list(self.processes.values())
    
    def get_running_processes(self) -> List[ProcessInfo]:
        """Get all currently running processes."""
        return [p for p in self.processes.values() if p.status == ProcessStatus.RUNNING]
    
    def has_running_processes(self) -> bool:
        """Check if any processes are currently running."""
        return any(p.status == ProcessStatus.RUNNING for p in self.processes.values())
    
    def _update_error_count(self):
        """Update the error counter display."""
        error_count = sum(1 for p in self.processes.values() if p.status == ProcessStatus.ERROR)
        warning_count = sum(1 for p in self.processes.values() if p.status == ProcessStatus.WARNING)
        
        total = error_count + warning_count
        
        if total == 0:
            self.error_button.setText("✓ 0")
            self.error_button.setStyleSheet("""
                QPushButton {
                    background-color: #22C55E;
                    color: white;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #16A34A;
                }
            """)
        elif error_count > 0:
            self.error_button.setText(f"✗ {error_count}")
            self.error_button.setStyleSheet("""
                QPushButton {
                    background-color: #EF4444;
                    color: white;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #DC2626;
                }
            """)
        else:
            self.error_button.setText(f"⚠ {warning_count}")
            self.error_button.setStyleSheet("""
                QPushButton {
                    background-color: #EAB308;
                    color: white;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #CA8A04;
                }
            """)
    
    def _update_progress_bar(self):
        """Update the progress bar based on running processes."""
        running = self.get_running_processes()
        
        if not running:
            self.progress_bar.setValue(0)
            return
        
        # Calculate average progress
        total_progress = sum(p.progress for p in running)
        avg_progress = total_progress // len(running)
        self.progress_bar.setValue(avg_progress)
    
    def _update_activity_summary(self):
        """Update the activity summary label."""
        running = self.get_running_processes()
        
        if not running:
            self.activity_summary.setText("Idle")
            return
        
        # Count processes by status
        running_count = len(running)
        error_count = sum(1 for p in self.processes.values() if p.status == ProcessStatus.ERROR)
        
        # Get most recent message
        latest_process = max(running, key=lambda p: p.timestamp)
        time_diff = (datetime.now() - latest_process.timestamp).total_seconds()
        
        # Format time ago
        if time_diff < 1:
            time_ago = "just now"
        elif time_diff < 60:
            time_ago = f"{int(time_diff)}s ago"
        else:
            time_ago = f"{int(time_diff // 60)}m ago"
        
        # Build summary text
        if error_count > 0:
            self.activity_summary.setText(f"Running: {running_count} • {error_count} errors • {time_ago}")
        else:
            self.activity_summary.setText(f"Running: {running_count} • {time_ago}")
    
    def _on_details_toggled(self, checked):
        """Handle details panel toggle."""
        if checked:
            self.details_widget.setVisible(True)
            self.fade_animation.setStartValue(0.0)
            self.fade_animation.setEndValue(1.0)
            self.fade_animation.start()
            self.details_button.setText("▲ Details")
        else:
            self.fade_animation.finished.connect(self._hide_details)
            self.fade_animation.setStartValue(1.0)
            self.fade_animation.setEndValue(0.0)
            self.fade_animation.start()
    
    def _hide_details(self):
        """Hide the details panel after animation."""
        self.fade_animation.finished.disconnect()
        self.details_widget.setVisible(False)
        self.details_button.setText("▼ Details")
    
    def _on_error_button_clicked(self):
        """Handle error button click."""
        # Show errors in details and expand
        if not self.details_button.isChecked():
            self.details_button.setChecked(True)
        
        # Clear errors after viewing
        self.clear_errors_requested.emit()
    
    def clear_all_errors(self):
        """Clear all error statuses."""
        for process_id in self.processes:
            if self.processes[process_id].status == ProcessStatus.ERROR:
                self.set_process_idle(process_id)
            elif self.processes[process_id].status == ProcessStatus.WARNING:
                self.set_process_idle(process_id)
        self.error_count = 0
        self._update_error_count()
    
    def set_theme(self, theme: Theme):
        """Apply theme to the status bar."""
        self.theme = theme
        
        # Update styles
        bg_color = theme.background
        text_color = theme.text
        accent_color = theme.accent
        
        self.setStyleSheet(f"""
            BackendStatusBar {{
                background-color: {bg_color};
                border-top: 1px solid {theme.border};
            }}
        """)
    
    def reset_all(self):
        """Reset all processes to idle state."""
        for process_id in self.processes:
            self.set_process_idle(process_id)
        self.history_widget.clear()
        self.error_count = 0
        self._update_error_count()
