"""
Cache Tracking Widget for displaying prompt caching performance metrics.

This module provides the CacheTrackingWidget class for visualizing
prompt cache usage, savings, and optimization recommendations.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QProgressBar, QTabWidget, QScrollArea,
    QGroupBox, QLineEdit, QComboBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QPalette

from src.core.cache_models import (
    CachePerformanceReport, ModelCacheStats, CacheOptimizationRecommendation
)
from src.core.cache_tracking_worker import CacheTrackingWorker
from src.core.model_cache import ModelCacheManager
from src.config.config import Config

logger = logging.getLogger(__name__)


class CacheTrackingWidget(QWidget):
    """
    Widget for displaying prompt cache performance metrics and analytics.

    Features:
    - Summary statistics (total savings, cache hit rate)
    - Model-level cache performance table
    - Daily cache trends
    - Optimization recommendations
    """

    def __init__(self, parent=None):
        """Initialize the cache tracking widget."""
        super().__init__(parent)
        self.cache_worker: Optional[CacheTrackingWorker] = None
        self.current_report: Optional[CachePerformanceReport] = None
        self.model_stats: Dict[str, ModelCacheStats] = {}
        self.recommendations: List[CacheOptimizationRecommendation] = []
        self.model_cache = ModelCacheManager()

        self._setup_ui()
        self._connect_signals()
        self._start_cache_worker()

    def _setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)

        title_label = QLabel("Prompt Cache Performance")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        summary_frame = self._create_summary_section()
        main_layout.addWidget(summary_frame)

        tabs = QTabWidget()

        performance_tab = self._create_performance_tab()
        tabs.addTab(performance_tab, "Model Performance")

        trends_tab = self._create_trends_tab()
        tabs.addTab(trends_tab, "Daily Trends")

        recommendations_tab = self._create_recommendations_tab()
        tabs.addTab(recommendations_tab, "Optimizations")

        main_layout.addWidget(tabs)

        control_layout = QHBoxLayout()
        control_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._start_cache_worker)
        control_layout.addWidget(refresh_btn)

        main_layout.addLayout(control_layout)

    def _create_summary_section(self) -> QFrame:
        """Create the summary statistics section."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border-radius: 8px;
                padding: 16px;
            }
        """)

        layout = QGridLayout(frame)
        layout.setSpacing(16)

        self.summary_labels = {}

        metrics = [
            ("Total Savings", "total_savings", "$0.00", "Total cost savings from caching"),
            ("Cache Hit Rate", "cache_hit_rate", "0%", "Percentage of tokens served from cache"),
            ("Requests Analyzed", "total_requests", "0", "Total requests in period"),
            ("Models Tracked", "models_count", "0", "Models with caching activity"),
        ]

        for i, (title, key, default, tooltip) in enumerate(metrics):
            container = QVBoxLayout()

            label = QLabel(default)
            label.setAlignment(Qt.AlignCenter)
            label.setMinimumWidth(150)
            label.setObjectName(f"summary_{key}")
            label.setToolTip(tooltip)
            
            # Store reference directly
            self.summary_labels[key] = label

            title_label = QLabel(title)
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet("color: #888; font-size: 12px;")

            container.addWidget(label)
            container.addWidget(title_label)

            layout.addLayout(container, 0, i)

        return frame

    def _create_performance_tab(self) -> QWidget:
        """Create the model performance tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QWidget {
                background-color: transparent;
            }
        """)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)

        table_group = QGroupBox("Cache Performance by Model")
        table_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
        """)
        table_layout = QVBoxLayout()

        self.model_table = QTableWidget(0, 8)
        self.model_table.setObjectName("model_performance_table")
        self.model_table.setHorizontalHeaderLabels([
            "Model",
            "Requests",
            "Cache Hits",
            "Hit Rate",
            "Tokens",
            "Cached",
            "Savings",
            "Discount"
        ])

        self.model_table.horizontalHeader().setStretchLastSection(False)
        self.model_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 8):
            self.model_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        self.model_table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a3e;
                border: 1px solid #3a3a4e;
                border-radius: 4px;
                gridline-color: #3a3a4e;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3a3a4e;
            }
            QTableWidget::item:selected {
                background-color: #4a4a5e;
            }
            QHeaderView::section {
                background-color: #1e1e2e;
                color: #aaa;
                padding: 8px;
                border: 1px solid #3a3a4e;
            }
        """)

        table_layout.addWidget(self.model_table)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)

        scroll.setWidget(content)
        return scroll

    def _create_trends_tab(self) -> QWidget:
        """Create the daily trends tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)

        trends_group = QGroupBox("Daily Cache Performance")
        trends_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }
        """)
        trends_layout = QVBoxLayout()

        self.trends_table = QTableWidget(0, 6)
        self.trends_table.setObjectName("trends_table")
        self.trends_table.setHorizontalHeaderLabels([
            "Date",
            "Requests",
            "Prompt Tokens",
            "Cached Tokens",
            "Hit Rate",
            "Savings"
        ])

        self.trends_table.horizontalHeader().setStretchLastSection(False)
        self.trends_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for i in range(1, 6):
            self.trends_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        self.trends_table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a3e;
                border: 1px solid #3a3a4e;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 8px;
            }
        """)

        trends_layout.addWidget(self.trends_table)
        trends_group.setLayout(trends_layout)
        layout.addWidget(trends_group)

        scroll.setWidget(content)
        return scroll

    def _create_recommendations_tab(self) -> QWidget:
        """Create the optimization recommendations tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)

        recommendations_group = QGroupBox("Cache Optimization Recommendations")
        recommendations_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }
        """)
        recs_layout = QVBoxLayout()

        self.recommendations_table = QTableWidget(0, 5)
        self.recommendations_table.setObjectName("recommendations_table")
        self.recommendations_table.setHorizontalHeaderLabels([
            "Priority",
            "Model",
            "Issue",
            "Current",
            "Savings Potential"
        ])

        self.recommendations_table.horizontalHeader().setStretchLastSection(False)
        self.recommendations_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for i in range(1, 5):
            self.recommendations_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        self.recommendations_table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a3e;
                border: 1px solid #3a3a4e;
                border-radius: 4px;
            }
        """)

        recs_layout.addWidget(self.recommendations_table)
        recommendations_group.setLayout(recs_layout)
        layout.addWidget(recommendations_group)

        scroll.setWidget(content)
        return scroll

    def _connect_signals(self):
        """Connect signals for cache worker."""
        pass

    def _start_cache_worker(self):
        """Start the cache tracking worker thread."""
        if self.cache_worker and self.cache_worker.isRunning():
            self.cache_worker.terminate()
            self.cache_worker.wait()

        self.cache_worker = CacheTrackingWorker(
            admin_key=Config.VENICE_ADMIN_KEY,
            analysis_days=7
        )

        self.cache_worker.cache_data_ready.connect(self._on_cache_data_ready)
        self.cache_worker.error_occurred.connect(self._on_cache_error)
        self.cache_worker.status_update.connect(self._on_status_update)

        self.cache_worker.start()

    def _on_cache_data_ready(self, bundle):
        """Handle cache data ready signal."""
        if hasattr(bundle, 'report') and hasattr(bundle, 'model_stats'):
            report = bundle.report
            model_stats = bundle.model_stats
        else:
            report = bundle
            model_stats = {}
        self.current_report = report
        self.model_stats = model_stats

        self._update_summary_display(report)
        self._update_model_table(model_stats)
        self._update_trends_table(report.daily_stats)
        self._generate_and_update_recommendations(model_stats)

    def _on_cache_error(self, error_msg: str):
        """Handle cache tracking error."""
        logger.error(f"Cache tracking error: {error_msg}")

    def _on_status_update(self, status: str):
        """Handle status update from worker."""
        logger.info(f"Cache tracking: {status}")

    def _update_summary_display(self, report: CachePerformanceReport):
        """Update the summary statistics display."""
        if not report:
            return

        if self.summary_labels.get("total_savings"):
            self.summary_labels["total_savings"].setText(f"${report.total_savings_usd:.4f}")

        if self.summary_labels.get("cache_hit_rate"):
            self.summary_labels["cache_hit_rate"].setText(f"{report.overall_cache_hit_rate:.1f}%")

        if self.summary_labels.get("total_requests"):
            self.summary_labels["total_requests"].setText(f"{report.total_requests:,}")

        if self.summary_labels.get("models_count"):
            self.summary_labels["models_count"].setText(f"{len(report.model_stats)}")

    def _update_model_table(self, model_stats: Dict[str, ModelCacheStats]):
        """Update the model performance table."""
        self.model_table.setRowCount(0)

        sorted_models = sorted(
            model_stats.values(),
            key=lambda x: x.total_savings_usd,
            reverse=True
        )

        for stats in sorted_models:
            row = self.model_table.rowCount()
            self.model_table.insertRow(row)

            self.model_table.setItem(row, 0, QTableWidgetItem(stats.model_name))
            self.model_table.setItem(row, 1, QTableWidgetItem(str(stats.total_requests)))
            self.model_table.setItem(row, 2, QTableWidgetItem(str(stats.cache_hit_requests)))
            self.model_table.setItem(row, 3, QTableWidgetItem(f"{stats.cache_hit_rate:.1f}%"))
            self.model_table.setItem(row, 4, QTableWidgetItem(f"{stats.total_prompt_tokens:,}"))
            self.model_table.setItem(row, 5, QTableWidgetItem(f"{stats.total_cached_tokens:,}"))
            self.model_table.setItem(row, 6, QTableWidgetItem(f"${stats.total_savings_usd:.4f}"))

            model = self.model_cache.get_model(stats.model_id) if hasattr(self, 'model_cache') else None
            discount = 0
            if model and model.cache_input_price_usd and model.input_price_usd:
                discount = (1 - model.cache_input_price_usd / model.input_price_usd) * 100
            self.model_table.setItem(row, 7, QTableWidgetItem(f"{discount:.0f}%"))

    def _update_trends_table(self, daily_stats: List):
        """Update the daily trends table."""
        self.trends_table.setRowCount(0)

        for day in daily_stats:
            row = self.trends_table.rowCount()
            self.trends_table.insertRow(row)

            self.trends_table.setItem(row, 0, QTableWidgetItem(day.date))
            self.trends_table.setItem(row, 1, QTableWidgetItem(str(day.total_requests)))
            self.trends_table.setItem(row, 2, QTableWidgetItem(f"{day.total_prompt_tokens:,}"))
            self.trends_table.setItem(row, 3, QTableWidgetItem(f"{day.total_cached_tokens:,}"))
            self.trends_table.setItem(row, 4, QTableWidgetItem(f"{day.cache_hit_rate:.1f}%"))
            self.trends_table.setItem(row, 5, QTableWidgetItem(f"${day.total_savings_usd:.4f}"))

    def _generate_and_update_recommendations(self, model_stats: Dict[str, ModelCacheStats]):
        """Generate and display optimization recommendations."""
        from src.core.cache_analytics import CacheAnalytics

        analytics = CacheAnalytics()
        self.recommendations = analytics.generate_optimization_recommendations(model_stats)

        self.recommendations_table.setRowCount(0)

        priority_colors = {
            "high": QColor("#e74c3c"),
            "medium": QColor("#f39c12"),
            "low": QColor("#27ae60")
        }

        for rec in self.recommendations[:20]:
            row = self.recommendations_table.rowCount()
            self.recommendations_table.insertRow(row)

            priority_item = QTableWidgetItem(rec.priority.upper())
            priority_item.setForeground(priority_colors.get(rec.priority, QColor("#888")))
            self.recommendations_table.setItem(row, 0, priority_item)

            self.recommendations_table.setItem(row, 1, QTableWidgetItem(rec.model_name))
            self.recommendations_table.setItem(row, 2, QTableWidgetItem(rec.title))
            self.recommendations_table.setItem(row, 3, QTableWidgetItem(rec.current_value))

            savings_text = f"${rec.potential_savings_usd:.4f}" if rec.potential_savings_usd > 0 else "N/A"
            self.recommendations_table.setItem(row, 4, QTableWidgetItem(savings_text))

    def refresh(self):
        """Refresh cache data."""
        self._start_cache_worker()

    def close(self):
        """Clean up worker thread on widget close."""
        if hasattr(self, 'cache_worker') and self.cache_worker:
            try:
                if self.cache_worker.isRunning():
                    self.cache_worker.quit()
                    self.cache_worker.wait(2000)
                self.cache_worker.deleteLater()
            except (RuntimeError, Exception):
                pass
            self.cache_worker = None
