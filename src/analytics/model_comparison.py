"""
Model Comparison and Analytics Widget for Venice AI Model Viewer
Provides comprehensive comparison tools, usage analytics, and enhanced discovery features.
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional, Set, Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableView, QTableWidgetItem, QComboBox,
    QCheckBox, QGroupBox, QScrollArea, QTextEdit,
    QLineEdit, QHeaderView, QTabWidget, QApplication, QDialog
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QThread
from PySide6.QtGui import QFont, QColor

# Matplotlib imports for chart rendering
import matplotlib
import warnings
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Suppress tight layout warnings
warnings.filterwarnings('ignore', message='Tight layout not applied')

# HTTP requests for API calls
from shiboken6 import isValid

logger = logging.getLogger(__name__)

from src.config.config import Config
from src.config.theme import Theme
from src.config.column_config import ColumnDefinition, get_columns_for_type
from src.core.venice_api_client import VeniceAPIClient
from src.core.video_quote_worker import VideoBasePrice
from src.utils.date_utils import DateFormatter
from src.utils.model_utils import ModelNameParser


class ChartCanvas(FigureCanvas):
    """Custom matplotlib canvas for embedding charts in Qt"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Set transparent background
        self.fig.patch.set_alpha(0.0)
        
        # Disable matplotlib's scroll zoom so wheel events pass to parent scroll area
        self.setFocusPolicy(Qt.NoFocus)
        
    def wheelEvent(self, event):
        """Pass wheel events to parent scroll area for scrolling"""
        # Find the parent scroll area and forward the event
        parent = self.parent()
        while parent:
            if isinstance(parent, QScrollArea):
                # Forward to the scroll area's viewport
                QApplication.sendEvent(parent.viewport(), event)
                return
            parent = parent.parent()
        # If no scroll area found, ignore the event (don't let matplotlib zoom)
        event.ignore()
        
    def clear_chart(self):
        """Clear all axes from the figure"""
        self.fig.clear()
        self.draw()


class ComparisonSignals(QObject):
    """Signals for ModelComparisonWidget to communicate with main app"""
    connect_requested = Signal()


class ModelAnalyticsWorker(QThread):
    """Worker thread for fetching and processing model analytics data"""
    analytics_ready = Signal(dict)

    def __init__(self, admin_key: str = None, parent=None):
        super().__init__(parent)
        self.admin_key = admin_key or Config.VENICE_ADMIN_KEY
        self.api_client = VeniceAPIClient(self.admin_key)

    def run(self):
        """Fetch and process analytics data from Venice API"""
        try:
            # Try to fetch real data from billing/usage endpoint
            usage_data = self._fetch_billing_usage(days=7)
            analytics = self._process_usage_data(usage_data)
            # Don't use logger in worker thread - can cause crashes on macOS
            
        except Exception:
            # Fallback to mock data if API call fails
            analytics = self._get_mock_analytics()
        
        self.analytics_ready.emit(analytics)

    def _fetch_billing_usage(self, days: int = 7) -> List[Dict[str, Any]]:
        """Fetch real billing usage data from Venice API"""
        # Use DateFormatter utility for consistent date ranges
        date_params = DateFormatter.create_date_range(days=days)
        
        params = {
            **date_params,
            'limit': 500,  # Get up to 500 recent entries
            'sortOrder': 'desc'
        }
        
        response = self.api_client.get("/billing/usage", params=params)
        
        data = response.json()
        return data.get('data', [])

    def _process_usage_data(self, usage_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process raw billing usage data into analytics format"""
        model_usage = {}
        cost_breakdown = {}
        performance_data = {}
        request_tracker = {}  # Track unique requests per model
        
        logger.debug(f"Processing {len(usage_entries)} usage entries")
        
        for entry in usage_entries:
            sku = entry.get('sku', 'unknown')
            amount = entry.get('amount', 0)
            entry.get('currency', 'USD')
            inference = entry.get('inferenceDetails') or {}  # Handle None values
            
            # Use absolute value (negative amounts represent actual usage costs)
            abs_amount = abs(amount)
            
            # Skip zero amounts
            if abs_amount == 0:
                continue
            
            # Clean up model name using ModelNameParser
            model_name = ModelNameParser.clean_sku_name(sku)
            
            # Initialize model data if not exists
            if model_name not in model_usage:
                model_usage[model_name] = {'requests': 0, 'tokens': 0}
                cost_breakdown[model_name] = 0.0
                performance_data[model_name] = {
                    'response_times': [],
                    'success_count': 0,
                    'total_count': 0
                }
                request_tracker[model_name] = set()
            
            # Count unique requests (only count once per request ID to avoid double-counting input/output)
            request_id = None
            if isinstance(inference, dict):
                request_id = inference.get('requestId')
                # Handle case where requestId might be empty string or None
                if not request_id:
                    request_id = None
            
            if request_id and request_id not in request_tracker[model_name]:
                request_tracker[model_name].add(request_id)
                model_usage[model_name]['requests'] += 1
            elif not request_id:
                # For entries without requestId, we'll still count them but they might be double-counted
                # This is better than missing data entirely
                model_usage[model_name]['requests'] += 1
            
            # Sum tokens (prompt + completion) - these will be counted for both input and output entries
            if isinstance(inference, dict):
                prompt_tokens = inference.get('promptTokens') or 0
                completion_tokens = inference.get('completionTokens') or 0
                total_tokens = prompt_tokens + completion_tokens
                model_usage[model_name]['tokens'] += total_tokens
            
            # Sum costs (use absolute value)
            cost_breakdown[model_name] += abs_amount
            
            # Collect performance data (only once per request)
            if request_id and request_id not in request_tracker[model_name]:
                perf = performance_data[model_name]
                perf['total_count'] += 1
                
                # Assume success if we have inference details
                if isinstance(inference, dict) and inference:
                    perf['success_count'] += 1
                    exec_time = inference.get('inferenceExecutionTime')
                    if exec_time:
                        perf['response_times'].append(exec_time / 1000.0)  # Convert ms to seconds
        
        # Calculate averages and rates
        for model_name, perf in performance_data.items():
            times = perf['response_times']
            perf['avg_response_time'] = sum(times) / len(times) if times else 0.0
            perf['success_rate'] = (perf['success_count'] / perf['total_count']) * 100 if perf['total_count'] > 0 else 0.0
            
            # Remove temporary data
            del perf['response_times']
            del perf['success_count']
            del perf['total_count']
        
        # If no data was found, fall back to mock data
        if not model_usage:
            logger.debug("No valid usage data found, using mock data")
            return self._get_mock_analytics()
        
        logger.debug(f"Processed analytics for {len(model_usage)} models: {list(model_usage.keys())}")
        
        analytics = {
            'model_usage': model_usage,
            'cost_breakdown': cost_breakdown,
            'performance_metrics': performance_data,
            'recommendations': self._generate_recommendations({
                'model_usage': model_usage,
                'cost_breakdown': cost_breakdown,
                'performance_metrics': performance_data
            })
        }
        
        return analytics

    def _get_mock_analytics(self) -> Dict[str, Any]:
        """Fallback mock analytics data"""
        analytics = {
            'model_usage': {},
            'cost_breakdown': {},
            'performance_metrics': {},
            'recommendations': []
        }

        # Mock data for now - in production this would fetch from Venice API
        analytics['model_usage'] = {
            'llama-3.3-70b': {'requests': 1250, 'tokens': 45000},
            'llama-3.2-3b': {'requests': 2100, 'tokens': 32000},
            'qwen-2.5-vl': {'requests': 890, 'tokens': 68000},
            'flux-dev': {'requests': 650, 'tokens': 0}  # Image model
        }

        analytics['cost_breakdown'] = {
            'llama-3.3-70b': 124.50,
            'llama-3.2-3b': 85.40,
            'qwen-2.5-vl': 198.60,
            'flux-dev': 45.20
        }

        analytics['performance_metrics'] = {
            'llama-3.3-70b': {'avg_response_time': 2.4, 'success_rate': 98.5},
            'llama-3.2-3b': {'avg_response_time': 1.2, 'success_rate': 99.2},
            'qwen-2.5-vl': {'avg_response_time': 3.1, 'success_rate': 97.8},
            'flux-dev': {'avg_response_time': 8.5, 'success_rate': 96.1}
        }

        # Generate recommendations
        analytics['recommendations'] = self._generate_recommendations(analytics)

        return analytics

    def _generate_recommendations(self, analytics):
        """Generate intelligent recommendations based on analytics"""
        recommendations = []

        # Find most cost-efficient model
        usage = analytics['model_usage']
        costs = analytics['cost_breakdown']

        efficiency = {}
        for model in usage:
            if usage[model]['tokens'] > 0:
                efficiency[model] = costs.get(model, 0) / (usage[model]['tokens'] / 1000)

        if efficiency:
            most_efficient = min(efficiency.items(), key=lambda x: x[1])
            recommendations.append({
                'type': 'efficiency',
                'message': f"Most cost-efficient: {most_efficient[0]} (${most_efficient[1]:.3f}/1K tokens)",
                'priority': 'high'
            })

        # Performance recommendations
        performance = analytics.get('performance_metrics', {})
        for model, metrics in performance.items():
            if metrics.get('success_rate', 100) < 98:
                recommendations.append({
                    'type': 'reliability',
                    'message': f"{model} has lower reliability ({metrics['success_rate']:.1f}%)",
                    'priority': 'medium'
                })

        return recommendations


class ColumnManager:
    """Manage dynamic columns and visibility for the comparison table."""

    def __init__(self, table: QTableView, model: QStandardItemModel):
        self.table = table
        self.model = model
        self.current_type_key = "all"
        self.all_columns: List[ColumnDefinition] = []
        self.columns: List[ColumnDefinition] = []
        self.hidden_by_type: Dict[str, Set[str]] = {}
        self.key_to_index: Dict[str, int] = {}
        self._load_preferences()

    def set_model_type(self, model_type: Optional[str]) -> None:
        self.current_type_key = model_type.lower() if model_type else "all"
        self.all_columns = get_columns_for_type(model_type)
        hidden = self.hidden_by_type.get(self.current_type_key, set())
        self.columns = [col for col in self.all_columns if col.key not in hidden]
        if not self.columns and self.all_columns:
            self.columns = self.all_columns[:1]
        self._apply_columns()

    def set_column_visibility(self, column_key: str, visible: bool) -> None:
        # Never allow hiding the "model" column as it's essential for identification
        if column_key == "model":
            return
            
        hidden = self.hidden_by_type.setdefault(self.current_type_key, set())
        if visible:
            hidden.discard(column_key)
        else:
            hidden.add(column_key)
        self.hidden_by_type[self.current_type_key] = hidden
        self.columns = [col for col in self.all_columns if col.key not in hidden]
        if not self.columns and self.all_columns:
            hidden.discard("model")
            self.columns = [col for col in self.all_columns if col.key not in hidden]
            self.hidden_by_type[self.current_type_key] = hidden
        self._apply_columns()
        self._save_preferences()
        self._save_preferences()

    def _apply_columns(self) -> None:
        headers = [col.header for col in self.columns]
        self.model.setColumnCount(len(headers))
        self.model.setHorizontalHeaderLabels(headers)

        header = self.table.horizontalHeader()
        # Set sort role to UserRole for numeric sorting
        if hasattr(self.model, 'setSortRole'):
            self.model.setSortRole(Qt.UserRole)
        header.setStretchLastSection(False)
        for idx, col in enumerate(self.columns):
            if col.width_mode == "stretch":
                header.setSectionResizeMode(idx, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(idx, QHeaderView.ResizeToContents)
            header.setMinimumSectionSize(col.min_width)

        self.key_to_index = {col.key: idx for idx, col in enumerate(self.columns)}

    def get_columns(self) -> List[ColumnDefinition]:
        return self.columns

    def get_all_columns(self) -> List[ColumnDefinition]:
        return self.all_columns

    def get_column_index(self, key: str) -> int:
        return self.key_to_index.get(key, -1)

    def _load_preferences(self) -> None:
        """Load user column preferences from storage."""
        prefs_file = os.path.join("data", "column_preferences.json")
        if os.path.exists(prefs_file):
            try:
                with open(prefs_file, 'r') as f:
                    data = json.load(f)
                    # Convert sets back from lists and filter out "model" column
                    self.hidden_by_type = {}
                    for k, v in data.get("hidden_by_type", {}).items():
                        hidden_set = set(v)
                        hidden_set.discard("model")  # Never hide the model column
                        if hidden_set:  # Only keep non-empty sets
                            self.hidden_by_type[k] = hidden_set
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Failed to load column preferences: {e}")

    def _save_preferences(self) -> None:
        """Save user column preferences to storage."""
        prefs_file = os.path.join("data", "column_preferences.json")
        os.makedirs(os.path.dirname(prefs_file), exist_ok=True)
        try:
            # Convert sets to lists for JSON serialization
            data = {
                "hidden_by_type": {k: list(v) for k, v in self.hidden_by_type.items()}
            }
            with open(prefs_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logging.error(f"Failed to save column preferences: {e}")


class ModelComparisonWidget(QWidget):
    """
    Comprehensive model comparison widget with analytics and enhanced discovery.
    Focuses on usability with intuitive layouts, filtering, and visual comparisons.
    """

    def __init__(self, theme: Theme, models_data: Dict[str, Any] = None, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.original_models_data = models_data.copy() if models_data else {}
        self.models_data = models_data or {}
        self.analytics_worker = None
        self.current_analytics = {}
        self.video_base_prices: Dict[str, VideoBasePrice] = {}  # model_id -> base price

        # Initialize signals for communication with main app
        self.signals = ComparisonSignals()

        self.init_ui()
        self.start_analytics_update()

    def init_ui(self):
        """Initialize the modern, usable interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header with title and quick filters
        header_layout = QHBoxLayout()

        title_label = QLabel("Model Comparison & Analytics")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {self.theme.text}; margin-bottom: 5px;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Quick action buttons
        self.connect_btn = QPushButton("🔗 Connect")
        self.connect_btn.clicked.connect(self.connect_from_compare_tab)
        self.connect_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                border: 1px solid {self.theme.accent};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent};
            }}
        """)
        header_layout.addWidget(self.connect_btn)

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        self.refresh_btn.setEnabled(False)  # Disabled until data is loaded
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                border: 1px solid {self.theme.accent};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent};
            }}
        """)
        header_layout.addWidget(self.refresh_btn)

        layout.addLayout(header_layout)

        # Main content area with tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {self.theme.accent};
                background-color: {self.theme.background};
            }}
            QTabBar::tab {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                padding: 8px 16px;
                margin-right: 2px;
                border-radius: 4px 4px 0 0;
            }}
            QTabBar::tab:selected {{
                background-color: {self.theme.accent};
                color: {self.theme.text};
            }}
        """)

        # Unified Model Browser Tab (combines Compare and Discover)
        self.init_comparison_tab()

        # Analytics Dashboard Tab
        self.init_analytics_tab()

        layout.addWidget(self.tab_widget)

    def init_comparison_tab(self):
        """Initialize the unified model browser with comparison, filtering, and discovery"""
        comparison_tab = QWidget()
        layout = QVBoxLayout(comparison_tab)

        # Combined search and filter bar
        controls_group = QGroupBox("🔍 Search & Filter Models")
        controls_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {self.theme.accent};
                border-radius: 4px;
                margin-top: 10px;
                padding: 10px;
                background-color: {self.theme.card_background};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        controls_layout = QVBoxLayout(controls_group)
        
        # Top row: Search bar
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search by model name, trait, or capability...")
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.theme.input_background};
                color: {self.theme.text};
                border: 1px solid {self.theme.accent};
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 2px solid {self.theme.accent};
            }}
        """)
        search_row.addWidget(self.search_input, stretch=1)
        controls_layout.addLayout(search_row)
        
        # Filter row
        filters_layout = QHBoxLayout()

        # Model type filter
        type_layout = QVBoxLayout()
        type_label = QLabel("Type:")
        type_label.setStyleSheet(f"color: {self.theme.text};")
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All", "text", "image", "video", "tts", "asr", "embedding", "upscale", "inpaint"])
        self.type_filter.currentTextChanged.connect(self.apply_filters)
        self.type_filter.setStyleSheet(self._get_combobox_style())
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_filter)
        filters_layout.addLayout(type_layout)

        # Capability filters in a more compact layout
        capabilities_layout = QVBoxLayout()
        cap_label = QLabel("Capabilities:")
        cap_label.setStyleSheet(f"color: {self.theme.text};")
        capabilities_layout.addWidget(cap_label)
        
        cap_row = QHBoxLayout()
        self.vision_chk = QCheckBox("Vision")
        self.web_chk = QCheckBox("Web Search")
        self.function_chk = QCheckBox("Functions")
        self.reasoning_chk = QCheckBox("Reasoning")

        for chk in [self.vision_chk, self.web_chk, self.function_chk, self.reasoning_chk]:
            chk.stateChanged.connect(self.apply_filters)
            chk.setStyleSheet(f"color: {self.theme.text}; margin-right: 10px;")
            cap_row.addWidget(chk)
        
        capabilities_layout.addLayout(cap_row)
        filters_layout.addLayout(capabilities_layout)

        # Price range filter
        price_layout = QVBoxLayout()
        price_label = QLabel("Max Input $/1K:")
        price_label.setStyleSheet(f"color: {self.theme.text};")
        self.price_filter = QLineEdit("10000")
        self.price_filter.textChanged.connect(self.apply_filters)
        self.price_filter.setMaximumWidth(80)
        self.price_filter.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.theme.input_background};
                color: {self.theme.text};
                border: 1px solid {self.theme.accent};
                border-radius: 4px;
                padding: 4px;
            }}
        """)
        price_layout.addWidget(price_label)
        price_layout.addWidget(self.price_filter)
        filters_layout.addLayout(price_layout)

        # Column visibility button
        self.columns_btn = QPushButton("📊 Columns")
        self.columns_btn.clicked.connect(self._show_column_selector)
        self.columns_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                border: 1px solid {self.theme.accent};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent};
            }}
        """)
        filters_layout.addWidget(self.columns_btn)
        
        # Results count
        self.results_count_label = QLabel("0 models")
        self.results_count_label.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 12px;")
        filters_layout.addStretch()
        filters_layout.addWidget(self.results_count_label)

        controls_layout.addLayout(filters_layout)
        layout.addWidget(controls_group)

        # Model comparison table
        self.comparison_table = QTableView()
        self.model = QStandardItemModel()
        self.comparison_table.setModel(self.model)
        self.column_manager = ColumnManager(self.comparison_table, self.model)
        self.setup_comparison_table()
        layout.addWidget(self.comparison_table)

        self.tab_widget.addTab(comparison_tab, "🔍 Browse Models")

    def init_analytics_tab(self):
        """Initialize the analytics dashboard with tabbed charts for better space utilization"""
        analytics_tab = QWidget()
        main_layout = QVBoxLayout(analytics_tab)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Add scroll area to handle overflow
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {self.theme.background};
                border: none;
            }}
        """)
        
        # Content widget
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)

        # Chart tabs for better organization
        self.chart_tabs = QTabWidget()
        self.chart_tabs.setTabPosition(QTabWidget.North)
        self.chart_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {self.theme.accent};
                background-color: {self.theme.background};
            }}
            QTabBar::tab {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                padding: 10px 20px;
                margin-right: 2px;
                border-radius: 4px 4px 0 0;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                background-color: {self.theme.accent};
                color: {self.theme.text};
                font-weight: bold;
            }}
        """)

        # Requests Chart Tab
        requests_tab = QWidget()
        requests_layout = QVBoxLayout(requests_tab)
        requests_layout.setContentsMargins(10, 10, 10, 10)
        
        self.requests_chart = ChartCanvas(self, width=11, height=6, dpi=100)
        self.requests_chart.setStyleSheet(f"background-color: {self.theme.card_background};")
        self.requests_chart.setMinimumHeight(500)
        requests_layout.addWidget(self.requests_chart)
        self.chart_tabs.addTab(requests_tab, "📊 Requests by Model")

        # Tokens Chart Tab
        tokens_tab = QWidget()
        tokens_layout = QVBoxLayout(tokens_tab)
        tokens_layout.setContentsMargins(10, 10, 10, 10)
        
        self.tokens_chart = ChartCanvas(self, width=11, height=6, dpi=100)
        self.tokens_chart.setStyleSheet(f"background-color: {self.theme.card_background};")
        self.tokens_chart.setMinimumHeight(500)
        tokens_layout.addWidget(self.tokens_chart)
        self.chart_tabs.addTab(tokens_tab, "🔢 Tokens by Model")

        # Cost Breakdown Chart Tab
        cost_tab = QWidget()
        cost_layout = QVBoxLayout(cost_tab)
        cost_layout.setContentsMargins(10, 10, 10, 10)
        
        self.cost_chart = ChartCanvas(self, width=11, height=6, dpi=100)
        self.cost_chart.setStyleSheet(f"background-color: {self.theme.card_background};")
        self.cost_chart.setMinimumHeight(500)
        cost_layout.addWidget(self.cost_chart)
        self.chart_tabs.addTab(cost_tab, "💰 Cost Breakdown")

        layout.addWidget(self.chart_tabs)

        # Recommendations panel (keep this for insights)
        rec_group = QGroupBox("Smart Recommendations")
        rec_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {self.theme.accent};
                border-radius: 4px;
                margin-top: 10px;
                padding: 10px;
                background-color: {self.theme.card_background};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        rec_layout = QVBoxLayout(rec_group)
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setReadOnly(True)
        self.recommendations_text.setMaximumHeight(350)
        self.recommendations_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                border: 1px solid {self.theme.accent};
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }}
        """)
        rec_layout.addWidget(self.recommendations_text)
        layout.addWidget(rec_group)
        
        # Set the content widget in scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        self.tab_widget.addTab(analytics_tab, "📊 Analytics")
    
    def _on_search_changed(self, text: str):
        """Handle search input changes"""
        self.apply_filters()
    
    def _update_results_count(self, count: int):
        """Update the results count label"""
        if hasattr(self, 'results_count_label'):
            self.results_count_label.setText(f"{count} models")

    def _show_column_selector(self) -> None:
        """Show a dialog to toggle column visibility for the current type."""
        if not hasattr(self, 'column_manager'):
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Select Columns")
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {self.theme.card_background};
            }}
            QLabel {{
                color: {self.theme.text};
            }}
            QCheckBox {{
                color: {self.theme.text};
            }}
        """)

        layout = QVBoxLayout(dialog)
        
        # Add checkboxes for each column
        self._column_checkboxes = []
        for col in self.column_manager.get_all_columns():
            # Skip the model column as it should always be visible
            if col.key == "model":
                continue
                
            checkbox = QCheckBox(col.header)
            hidden = col.key in self.column_manager.hidden_by_type.get(self.column_manager.current_type_key, set())
            checkbox.setChecked(not hidden)
            checkbox.stateChanged.connect(
                lambda state, key=col.key: self.column_manager.set_column_visibility(
                    key, state == Qt.Checked
                )
            )
            self._column_checkboxes.append((checkbox, col.key))
            layout.addWidget(checkbox)

        # Button layout
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_columns_to_defaults)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)

        dialog.exec()

    def _reset_columns_to_defaults(self) -> None:
        """Reset column visibility to defaults for the current model type."""
        if hasattr(self, 'column_manager'):
            # Clear hidden columns for current type
            self.column_manager.hidden_by_type.pop(self.column_manager.current_type_key, None)
            self.column_manager.set_model_type(self.column_manager.current_type_key)
            self.column_manager._save_preferences()
            
            # Update checkboxes in the dialog
            if hasattr(self, '_column_checkboxes'):
                for checkbox, key in self._column_checkboxes:
                    # All columns should be visible after reset (assuming defaults show all)
                    # Note: model column is not in _column_checkboxes so no need to handle it
                    checkbox.setChecked(True)

    def setup_comparison_table(self):
        """Setup the comparative table with proper styling"""
        self.comparison_table.setSortingEnabled(True)
        self.comparison_table.setStyleSheet(f"""
            QTableView {{
                background-color: {self.theme.background};
                color: {self.theme.text};
                border: 1px solid {self.theme.accent};
                border-radius: 4px;
                gridline-color: {self.theme.accent};
            }}
            QTableView::item {{
                color: {self.theme.text};
                padding: 5px;
            }}
            QTableView::item:selected {{
                background-color: {self.theme.accent};
                color: {self.theme.text};
            }}
            QHeaderView::section {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                padding: 8px;
                border: 1px solid {self.theme.accent};
                font-weight: bold;
            }}
        """)

        self.column_manager.set_model_type(self.type_filter.currentText())
        self.populate_comparison_table()

    def _get_cell_value(self, column_key: str, model: Dict, model_spec: Dict,
                        capabilities: Dict, pricing: Dict, constraints: Dict) -> Tuple[QTableWidgetItem, Any]:
        """Get formatted cell value and sort key for a column."""
        model_type = model.get('type', 'unknown')
        
        # Default values
        sort_key = 0.0
        item = QTableWidgetItem("—")
        
        # Model name column
        if column_key == "model":
            model_id = model.get('id', 'Unknown')
            item = QTableWidgetItem(model_id)
            item.setToolTip(f"Model: {model_id}")
            return item, model_id
        
        # Type column
        if column_key == "type":
            type_icons = {'text': '💬', 'image': '🖼️', 'video': '🎬', 'tts': '🔊',
                         'asr': '🎙️', 'embedding': '🔢', 'upscale': '📈', 'inpaint': '🎨'}
            type_icon = type_icons.get(model_type, '❓')
            item = QTableWidgetItem(f"{type_icon} {model_type}")
            return item, model_type
        
        # Context/Specs column - different content based on model type
        if column_key in ("context", "specs"):
            if model_type == 'text':
                context = model_spec.get('availableContextTokens', 'N/A')
                context_text = f"{context:,}" if isinstance(context, int) else str(context) if context else 'N/A'
                item = QTableWidgetItem(context_text)
                item.setToolTip(f"Context window: {context_text} tokens")
                sort_key = context if isinstance(context, int) else 0
            elif model_type in ('image', 'upscale', 'inpaint'):
                specs_parts = []
                if constraints:
                    steps = constraints.get('steps', {})
                    if steps:
                        max_steps = steps.get('max', steps.get('default', 'N/A'))
                        if max_steps != 'N/A':
                            specs_parts.append(f"Steps: {max_steps}")
                    prompt_limit = constraints.get('promptCharacterLimit')
                    if prompt_limit:
                        specs_parts.append(f"Prompt: {prompt_limit}")
                context_text = ", ".join(specs_parts) if specs_parts else "Standard"
                item = QTableWidgetItem(context_text)
                item.setToolTip(f"Image specs: {context_text}")
            elif model_type in ('tts', 'asr'):
                voices = model_spec.get('voices', model_spec.get('supportedVoices', []))
                context_text = f"{len(voices)} voices" if voices else "Multiple voices"
                item = QTableWidgetItem(context_text)
                item.setToolTip(f"Supported voices: {', '.join(voices[:5]) if voices else 'Various'}")
            elif model_type == 'embedding':
                dimensions = model_spec.get('dimensions', model_spec.get('embeddingDimensions', 'N/A'))
                item = QTableWidgetItem(f"Dim: {dimensions}")
                item.setToolTip(f"Embedding dimensions: {dimensions}")
            elif model_type == 'video':
                durations = constraints.get('durations', [])
                if durations:
                    item = QTableWidgetItem(", ".join(str(d) for d in durations))
                else:
                    item = QTableWidgetItem("Standard")
            else:
                item = QTableWidgetItem('—')
            return item, sort_key
        
        # Capability columns (text models only) - map to correct API field names
        if column_key in ("vision", "functions", "web_search", "reasoning", "logprobs"):
            is_text_model = model_type == 'text'
            if is_text_model:
                # Map column keys to actual API capability field names
                cap_key_map = {
                    'vision': 'supportsVision',
                    'functions': 'supportsFunctionCalling',
                    'web_search': 'supportsWebSearch',
                    'reasoning': 'supportsReasoning',
                    'logprobs': 'supportsLogProbs',
                }
                cap_key = cap_key_map.get(column_key, '')
                cap_enabled = capabilities.get(cap_key, False)
                value = "✓" if cap_enabled else "✗"
                item = QTableWidgetItem(value)
                if cap_enabled:
                    item.setBackground(QColor("#4CAF50"))
                    item.setForeground(QColor("#ffffff"))
                else:
                    item.setBackground(QColor("#ef5350"))
                    item.setForeground(QColor("#ffffff"))
            else:
                item = QTableWidgetItem("—")
                item.setForeground(QColor(self.theme.text_secondary))
            return item, 1.0 if (is_text_model and cap_enabled) else 0.0
        
        # Price columns
        if column_key == "input_price":
            if model_type == 'text':
                input_cost = pricing.get('input', {}).get('usd', 0) * 1000
                item = QTableWidgetItem(f"${input_cost:.3f}")
                item.setData(Qt.UserRole, input_cost)
                return item, input_cost
            elif model_type == 'tts':
                per_char = pricing.get('input', {}).get('usd', 0)
                item = QTableWidgetItem(f"${per_char:.2f}/1M")
                item.setToolTip(f"Cost per 1M characters: ${per_char:.2f}")
                item.setData(Qt.UserRole, per_char)
                return item, per_char
            elif model_type == 'embedding':
                input_cost = pricing.get('input', {}).get('usd', 0) * 1000
                item = QTableWidgetItem(f"${input_cost:.3f}")
                item.setData(Qt.UserRole, input_cost)
                return item, input_cost
            elif model_type in ('image', 'upscale', 'inpaint', 'video'):
                per_gen = pricing.get('generation', {}).get('usd', 0)
                if per_gen == 0:
                    per_gen = pricing.get('perImage', {}).get('usd', 0)
                if per_gen > 0:
                    suffix = "/img" if model_type in ('image', 'upscale', 'inpaint') else "/video"
                    item = QTableWidgetItem(f"${per_gen:.4f}{suffix}")
                    item.setToolTip(f"Cost per generation: ${per_gen:.4f}")
                else:
                    if model_type == 'video':
                        item = QTableWidgetItem("Variable")
                        item.setToolTip("Use Video Quote API")
                    else:
                        item = QTableWidgetItem("See pricing")
                        item.setToolTip("Check Venice pricing page")
                item.setData(Qt.UserRole, per_gen if per_gen > 0 else 999999)
                return item, per_gen if per_gen > 0 else 999999
            elif model_type == 'asr':
                per_min = pricing.get('input', {}).get('usd', 0)
                item = QTableWidgetItem(f"${per_min:.3f}/min")
                item.setData(Qt.UserRole, per_min)
                return item, per_min
        
        if column_key == "output_price":
            if model_type == 'text':
                output_cost = pricing.get('output', {}).get('usd', 0) * 1000
                item = QTableWidgetItem(f"${output_cost:.3f}")
                item.setData(Qt.UserRole, output_cost)
                return item, output_cost
            return QTableWidgetItem("—"), 0.0
        
        # Cache columns - prompt caching pricing
        if column_key in ("cache_input", "cache_write"):
            cache_key = "cache_input" if column_key == "cache_input" else "cache_write"
            cache_pricing = pricing.get(cache_key, {})
            if cache_pricing:
                cache_cost = cache_pricing.get('usd', 0) * 1000  # Convert to $/1K tokens
                item = QTableWidgetItem(f"${cache_cost:.3f}")
                item.setData(Qt.UserRole, cache_cost)
                return item, cache_cost
            return QTableWidgetItem("—"), 0.0
        
        # Privacy - this is a string field like "private" or "anonymized"
        if column_key == "privacy":
            privacy = model_spec.get('privacy', '')
            if privacy:
                item = QTableWidgetItem(privacy)
            return item, privacy if privacy else ""
        
        # Image/video specific columns
        if column_key == "resolutions":
            resolutions = constraints.get('resolutions', [])
            if resolutions:
                res_str = ", ".join(str(r) for r in resolutions[:5])
                if len(resolutions) > 5:
                    res_str += "..."
                item = QTableWidgetItem(res_str)
                sort_key = len(resolutions)  # Sort by number of resolutions
            else:
                item = QTableWidgetItem("Standard")
                sort_key = 0  # Sort "Standard" at the beginning
            return item, sort_key
        
        if column_key == "steps":
            steps = constraints.get('steps', {})
            max_steps = steps.get('max', steps.get('default', 'N/A'))
            item = QTableWidgetItem(str(max_steps))
            sort_key = max_steps if isinstance(max_steps, int) else 0
            return item, sort_key
        
        if column_key == "prompt_limit":
            limit = constraints.get('promptCharacterLimit', 'N/A')
            item = QTableWidgetItem(str(limit))
            sort_key = limit if isinstance(limit, int) else 0
            return item, sort_key
        
        if column_key == "generation_price":
            per_gen = pricing.get('generation', {}).get('usd', 0)
            res_pricing = pricing.get('resolutions', {})
            
            if per_gen > 0:
                item = QTableWidgetItem(f"${per_gen:.4f}/gen")
                item.setData(Qt.UserRole, per_gen)
            elif res_pricing:
                # Handle resolution-based pricing (e.g., nano-banana-pro)
                prices = []
                for res, price_info in res_pricing.items():
                    if isinstance(price_info, dict) and 'usd' in price_info:
                        prices.append(price_info['usd'])
                
                if prices:
                    min_price = min(prices)
                    max_price = max(prices)
                    if min_price == max_price:
                        item = QTableWidgetItem(f"${min_price:.2f}/gen")
                        item.setData(Qt.UserRole, min_price)
                    else:
                        item = QTableWidgetItem(f"${min_price:.2f}-${max_price:.2f}/gen")
                        item.setData(Qt.UserRole, min_price)
                    item.setToolTip(f"Resolution-based pricing: {', '.join(f'{res}: ${price_info.get('usd', 0):.2f}' for res, price_info in res_pricing.items() if isinstance(price_info, dict))}")
                else:
                    item = QTableWidgetItem("See pricing")
                    item.setToolTip("Check Venice pricing page")
            else:
                if model_type == 'video':
                    item = QTableWidgetItem("Variable")
                    item.setToolTip("Use Video Quote API")
                else:
                    item = QTableWidgetItem("See pricing")
                    item.setToolTip("Check Venice pricing page")
            return item, per_gen or (min(prices) if 'prices' in locals() and prices else 999999)
        
        # Video specific columns
        if column_key == "video_type":
            # Check constraints['model_type'] for "image-to-video" vs "text-to-video"
            video_model_type = constraints.get('model_type', '')
            if video_model_type == 'image-to-video':
                item = QTableWidgetItem("img→vid")
                sort_key = "image-to-video"
            elif video_model_type == 'text-to-video':
                item = QTableWidgetItem("text→vid")
                sort_key = "text-to-video"
            else:
                # Default based on model ID if not specified
                model_id = model.get('id', '').lower()
                if 'image' in model_id or 'img' in model_id or 'i2v' in model_id:
                    item = QTableWidgetItem("img→vid")
                    sort_key = "image-to-video"
                else:
                    item = QTableWidgetItem("text→vid")
                    sort_key = "text-to-video"
            return item, sort_key
        
        if column_key == "durations":
            durations = constraints.get('durations', [])
            if durations:
                # Durations may already include 's' suffix or just be numbers
                dur_strs = []
                for d in durations:
                    d_str = str(d)
                    if not d_str.endswith('s'):
                        d_str += 's'
                    dur_strs.append(d_str)
                item = QTableWidgetItem(", ".join(dur_strs))
                sort_key = len(durations)  # Sort by number of durations available
            else:
                item = QTableWidgetItem("Standard")
                sort_key = 0
            return item, sort_key
        
        if column_key == "audio":
            has_audio = constraints.get('audio', False)
            item = QTableWidgetItem("✓" if has_audio else "✗")
            return item, 1.0 if has_audio else 0.0
        
        if column_key == "audio_configurable":
            config = constraints.get('audio_configurable', False)
            item = QTableWidgetItem("✓" if config else "✗")
            return item, 1.0 if config else 0.0
        
        if column_key == "aspect_ratios":
            # Field is 'aspect_ratios' with underscore in API
            ratios = constraints.get('aspect_ratios', [])
            if ratios:
                item = QTableWidgetItem(", ".join(str(r) for r in ratios[:4]))
                if len(ratios) > 4:
                    item.setToolTip(", ".join(str(r) for r in ratios))
                sort_key = len(ratios)  # Sort by number of aspect ratios
            else:
                item = QTableWidgetItem("—")
                sort_key = 0
            return item, sort_key
        
        if column_key == "base_price":
            model_id = model.get('id')
            base_price = self.video_base_prices.get(model_id)
            if base_price:
                item = QTableWidgetItem(f"${base_price.base_usd:.3f}")
                item.setToolTip(f"Base price: {base_price.min_duration}s at {base_price.min_resolution}, no audio")
                item.setData(Qt.UserRole, base_price.base_usd)
                return item, base_price.base_usd
            else:
                item = QTableWidgetItem("—")
                item.setToolTip("Base price not available")
                return item, 0.0
        
        if column_key == "audio_price":
            # Check if model has audio capability
            has_audio = constraints.get('audio', False)
            if has_audio:
                item = QTableWidgetItem("Included")
                item.setToolTip("Audio included in generation price")
            else:
                item = QTableWidgetItem("—")
            return item, 0.0
        
        # Generic "price" column for DEFAULT view (all model types)
        if column_key == "price":
            if model_type == 'text':
                input_cost = pricing.get('input', {}).get('usd', 0) * 1000
                output_cost = pricing.get('output', {}).get('usd', 0) * 1000
                if input_cost > 0 or output_cost > 0:
                    item = QTableWidgetItem(f"${input_cost:.2f}/${output_cost:.2f}")
                    item.setToolTip(f"Input: ${input_cost:.3f}/1K, Output: ${output_cost:.3f}/1K")
                    return item, input_cost
            elif model_type in ('image', 'upscale', 'inpaint'):
                per_gen = pricing.get('generation', {}).get('usd', 0)
                if per_gen > 0:
                    item = QTableWidgetItem(f"${per_gen:.4f}/img")
                    return item, per_gen
            elif model_type == 'video':
                # Check if we have base price data for this video model
                model_id = model.get('id')
                base_price = self.video_base_prices.get(model_id)
                if base_price:
                    item = QTableWidgetItem(f"${base_price.base_usd:.3f}")
                    item.setToolTip(f"Base price: {base_price.min_duration}s at {base_price.min_resolution}, no audio (Use Video Quote API for custom pricing)")
                    item.setData(Qt.UserRole, base_price.base_usd)
                    return item, base_price.base_usd
                else:
                    item = QTableWidgetItem("See pricing")
                    item.setToolTip("Check Venice pricing page")
                    return item, 0.0
            elif model_type == 'tts':
                per_char = pricing.get('input', {}).get('usd', 0)
                if per_char > 0:
                    item = QTableWidgetItem(f"${per_char:.2f}/1M chars")
                    return item, per_char
            elif model_type == 'asr':
                per_min = pricing.get('input', {}).get('usd', 0)
                if per_min > 0:
                    item = QTableWidgetItem(f"${per_min:.3f}/min")
                    return item, per_min
            elif model_type == 'embedding':
                input_cost = pricing.get('input', {}).get('usd', 0) * 1000
                if input_cost > 0:
                    item = QTableWidgetItem(f"${input_cost:.3f}/1K")
                    return item, input_cost
            return QTableWidgetItem("—"), 0.0
        
        # Upscale specific
        if column_key == "upscale_factors":
            factors = list(pricing.get('upscale', {}).keys())
            if factors:
                item = QTableWidgetItem(", ".join(factors))
            else:
                item = QTableWidgetItem("2x, 4x")
            return item, 0.0
        
        if column_key == "upscale_price":
            prices = pricing.get('upscale', {})
            if prices:
                min_price = min(p.get('usd', 0) for p in prices.values())
                item = QTableWidgetItem(f"${min_price:.4f}")
                item.setData(Qt.UserRole, min_price)
            else:
                item = QTableWidgetItem("See pricing")
            return item, min_price if prices else 999999
        
        if column_key == "inpaint_price":
            inpaint_pricing = pricing.get('inpaint', {})
            if inpaint_pricing:
                price = inpaint_pricing.get('usd', 0)
                item = QTableWidgetItem(f"${price:.4f}")
                item.setData(Qt.UserRole, price)
            else:
                item = QTableWidgetItem("See pricing")
            return item, price if inpaint_pricing else 999999
        
        # TTS voices
        if column_key == "voices":
            voices = model_spec.get('voices', model_spec.get('supportedVoices', []))
            item = QTableWidgetItem(f"{len(voices)} voices" if voices else "Multiple")
            sort_key = len(voices) if voices else 0
            return item, sort_key
        
        # Embedding dimensions
        if column_key == "dimensions":
            dims = model_spec.get('dimensions', model_spec.get('embeddingDimensions', 'N/A'))
            item = QTableWidgetItem(str(dims))
            sort_key = dims if isinstance(dims, int) else 0
            return item, sort_key
        
        # Resolution pricing
        if column_key == "resolution_pricing":
            res_pricing = pricing.get('resolutions', {})
            has_res_pricing = bool(res_pricing and any(isinstance(price_info, dict) and 'usd' in price_info for price_info in res_pricing.values()))
            item = QTableWidgetItem("Yes" if has_res_pricing else "No")
            return item, 1.0 if has_res_pricing else 0.0
        
        return item, 0.0

    def populate_comparison_table(self):
        """Populate the comparison table with model data using dynamic columns."""
        if not self.models_data or 'data' not in self.models_data:
            return

        if not hasattr(self, 'column_manager'):
            return

        # Temporarily disable sorting to prevent data loss during population
        was_sorting_enabled = self.comparison_table.isSortingEnabled()
        self.comparison_table.setSortingEnabled(False)
        
        self.model.setRowCount(0)
        columns = self.column_manager.get_columns()
        
        for i, model in enumerate(self.models_data['data']):
            model_id = model.get('id', 'Unknown')
            model_spec = model.get('model_spec', {})
            model_type = model.get('type', 'unknown')
            capabilities = model_spec.get('capabilities', {})
            pricing = model_spec.get('pricing', {})
            constraints = model_spec.get('constraints', {})

            self.model.insertRow(i)

            for col_idx, col_def in enumerate(columns):
                result = self._get_cell_value(
                    col_def.key, model, model_spec, capabilities, pricing, constraints
                )
                if isinstance(result, tuple) and len(result) == 2:
                    item, sort_key = result
                else:
                    # Fallback if something went wrong
                    item = QTableWidgetItem("—")
                    sort_key = 0.0
                
                # Ensure item is a QTableWidgetItem
                if not hasattr(item, 'text'):
                    item = QTableWidgetItem(str(item))
                
                # Create QStandardItem with display text
                standard_item = QStandardItem(item.text())
                # Set tooltip if it was set on the QTableWidgetItem
                if hasattr(item, 'toolTip') and item.toolTip():
                    standard_item.setToolTip(item.toolTip())
                # Set colors for capability columns
                if col_def.key in ("vision", "functions", "web_search", "reasoning", "logprobs"):
                    if item.text() == "✓":
                        standard_item.setBackground(QColor("#4CAF50"))
                        standard_item.setForeground(QColor("#ffffff"))
                    elif item.text() == "✗":
                        standard_item.setBackground(QColor("#ef5350"))
                        standard_item.setForeground(QColor("#ffffff"))
                    elif item.text() == "—":
                        standard_item.setForeground(QColor(self.theme.text_secondary))
                # Set sort data based on the type of sort_key
                if isinstance(sort_key, (int, float)):
                    standard_item.setData(sort_key, Qt.UserRole)
                elif isinstance(sort_key, str):
                    standard_item.setData(sort_key, Qt.UserRole)
                # For other types, let it sort by display text
                self.model.setItem(i, col_idx, standard_item)

        # Resize columns to content
        for col_idx in range(len(columns) - 1):
            self.comparison_table.resizeColumnToContents(col_idx)
            
        # Re-enable sorting if it was enabled before
        self.comparison_table.setSortingEnabled(was_sorting_enabled)

    def setup_performance_table(self):
        """Setup performance metrics table"""
        headers = ["Model", "Avg Response Time", "Success Rate", "Requests", "Tokens Used"]

        self.performance_table.setColumnCount(len(headers))
        self.performance_table.setHorizontalHeaderLabels(headers)
        self.performance_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.performance_table.setStyleSheet(self.comparison_table.styleSheet())

        # Mock data - would be populated from analytics
        mock_data = [
            ["llama-3.3-70b", "2.4s", "98.5%", "1,250", "45,000"],
            ["llama-3.2-3b", "1.2s", "99.2%", "2,100", "32,000"],
            ["qwen-2.5-vl", "3.1s", "97.8%", "890", "68,000"],
        ]

        self.performance_table.setRowCount(len(mock_data))
        for i, row in enumerate(mock_data):
            for j, value in enumerate(row):
                item = QTableWidgetItem(value)
                if j == 1:  # Response time column
                    try:
                        time_val = float(value[:-1])  # Remove 's' and convert
                        if time_val > 2.5:
                            item.setBackground(QColor("#ef5350"))  # Vibrant red
                            item.setForeground(QColor("#ffffff"))
                        elif time_val < 1.5:
                            item.setBackground(QColor("#4CAF50"))  # Vibrant green
                            item.setForeground(QColor("#ffffff"))
                    except ValueError:
                        pass
                elif j == 2:  # Success rate column
                    try:
                        rate_val = float(value[:-1])  # Remove '%'
                        if rate_val < 98:
                            item.setBackground(QColor("#ef5350"))  # Vibrant red
                            item.setForeground(QColor("#ffffff"))
                        elif rate_val > 99:
                            item.setBackground(QColor("#4CAF50"))  # Vibrant green
                            item.setForeground(QColor("#ffffff"))
                    except ValueError:
                        pass
                self.performance_table.setItem(i, j, item)

    def _get_combobox_style(self):
        """Return modern combobox styling that matches the leaderboard"""
        return f"""
            QComboBox {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                border: 1px solid {self.theme.accent};
                border-radius: 4px;
                padding: 5px;
                min-width: 100px;
            }}
            QComboBox:hover {{
                border: 2px solid {self.theme.accent};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {self.theme.text};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                selection-background-color: {self.theme.accent};
                selection-color: {self.theme.text};
                border: 1px solid {self.theme.accent};
            }}
        """

    def apply_filters(self):
        """Apply current filters including search to both table and tree views"""
        model_type = self.type_filter.currentText().lower()
        
        # Update columns based on the selected model type
        if hasattr(self, 'column_manager'):
            self.column_manager.set_model_type(self.type_filter.currentText())
        
        # Get search text
        search_text = ""
        if hasattr(self, 'search_input'):
            search_text = self.search_input.text().lower().strip()

        # Collect capability requirements
        required_caps = []
        if self.vision_chk.isChecked():
            required_caps.append('supportsVision')
        if self.web_chk.isChecked():
            required_caps.append('supportsWebSearch')
        if self.function_chk.isChecked():
            required_caps.append('supportsFunctionCalling')
        if self.reasoning_chk.isChecked():
            required_caps.append('supportsReasoning')

        # Price filter
        max_price = 10000.0  # Default high value
        try:
            if self.price_filter.text():
                max_price = float(self.price_filter.text())
        except ValueError:
            max_price = 10000.0

        # Always filter from the original complete dataset, never from filtered data
        filtered_models = []
        if self.original_models_data and 'data' in self.original_models_data:
            for model in self.original_models_data['data']:
                model_id = model.get('id', '')
                model_spec = model.get('model_spec', {})
                capabilities = model_spec.get('capabilities', {})
                pricing = model_spec.get('pricing', {})
                traits = model_spec.get('traits', [])
                
                # Search filter - check model ID, traits, and capabilities
                if search_text:
                    search_match = False
                    if search_text in model_id.lower():
                        search_match = True
                    elif any(search_text in trait.lower() for trait in traits):
                        search_match = True
                    elif any(search_text in cap.lower().replace('supports', '') for cap, enabled in capabilities.items() if enabled):
                        search_match = True
                    
                    if not search_match:
                        continue
                
                # Check model type
                if model_type != "all" and model.get('type', '').lower() != model_type:
                    continue

                # Check capabilities
                caps_match = True
                for cap in required_caps:
                    if not capabilities.get(cap, False):
                        caps_match = False
                        break

                if not caps_match:
                    continue

                # Check price (only for text models with input pricing)
                input_cost = pricing.get('input', {}).get('usd', 0) * 1000
                if model.get('type') == 'text' and input_cost > max_price:
                    continue

                filtered_models.append(model)

        # Create a DISPLAY-only copy - NEVER modify the original data
        if self.original_models_data:
            self.models_data = self.original_models_data.copy()
            self.models_data['data'] = filtered_models
        else:
            self.models_data = {'data': filtered_models}

        # Update results count
        self._update_results_count(len(filtered_models))

        # Refresh the table view
        self.populate_comparison_table()

    def start_analytics_update(self):
        """Start periodic analytics updates"""
        # Clean up existing worker first
        if hasattr(self, 'analytics_worker') and self.analytics_worker is not None:
            if isValid(self.analytics_worker) and self.analytics_worker.isRunning():
                self.analytics_worker.quit()
                self.analytics_worker.wait(2000)
            self.analytics_worker = None
        
        self.analytics_worker = ModelAnalyticsWorker(parent=self)
        self.analytics_worker.analytics_ready.connect(self.update_analytics_display)
        self.analytics_worker.finished.connect(self._on_analytics_worker_finished)
        self.analytics_worker.start()
    
    def _on_analytics_worker_finished(self):
        """Handle analytics worker completion - clear reference before deleteLater"""
        worker = self.analytics_worker
        self.analytics_worker = None
        if worker and isValid(worker):
            worker.deleteLater()

    def update_analytics_display(self, analytics):
        """Update the analytics display with new data"""
        self.current_analytics = analytics

        # Update recommendations
        if 'recommendations' in analytics:
            rec_text = ""
            for rec in analytics['recommendations']:
                priority_icon = "🔴" if rec['priority'] == 'high' else "🟡"
                rec_text += f"{priority_icon} {rec['message']}\n"
            self.recommendations_text.setText(rec_text.strip())
        
        # Render the charts with the new data in separate tabs
        self.render_requests_chart(analytics)
        self.render_tokens_chart(analytics)
        self.render_cost_chart(analytics)

    def update_video_base_prices(self, base_prices: List[VideoBasePrice]):
        """Update video base prices and refresh table if needed"""
        self.video_base_prices = {price.model_id: price for price in base_prices}
        # Refresh the table to show updated prices
        if hasattr(self, 'comparison_table') and self.models_data:
            self.populate_comparison_table()

    def render_requests_chart(self, analytics):
        """Render the requests chart with logarithmic scale for outliers"""
        if 'model_usage' not in analytics:
            return
        
        usage_data = analytics['model_usage']
        
        # Clear previous chart
        self.requests_chart.fig.clear()
        
        # Create single subplot for requests
        ax = self.requests_chart.fig.add_subplot(111)
        
        # Get theme colors
        text_color = self.theme.text
        bg_color = self.theme.card_background
        self.theme.accent
        
        # Configure chart colors
        self.requests_chart.fig.patch.set_facecolor(bg_color)
        
        # Extract data and sort by values (descending)
        models = list(usage_data.keys())
        requests = [usage_data[m]['requests'] for m in models]
        
        # Sort by requests (descending) for better visualization
        sorted_indices = sorted(range(len(requests)), key=lambda i: requests[i], reverse=True)
        models = [models[i] for i in sorted_indices]
        requests = [requests[i] for i in sorted_indices]
        
        # Define vibrant color palette based on theme - use accent as primary
        primary_colors = self.theme.chart_colors
        bar_colors = [primary_colors[i % len(primary_colors)] for i in range(len(models))]
        
        # Shorten model names for display if they're too long
        short_models = []
        for model in models:
            if len(model) > 20:
                parts = model.split('-')
                if len(parts) > 2:
                    short_models.append(f"{parts[0]}-{parts[-1]}")
                else:
                    short_models.append(model[:17] + "...")
            else:
                short_models.append(model)
        
        # Check if we need logarithmic scale
        non_zero_requests = [r for r in requests if r > 0]
        use_log_scale = False
        if non_zero_requests and max(non_zero_requests) > 10 * min(non_zero_requests):
            use_log_scale = True
        
        # Plot requests with rounded bars effect
        bars = ax.bar(short_models, requests, color=bar_colors, width=0.7, edgecolor='none')
        ax.set_ylabel('Requests (log scale)' if use_log_scale else 'Requests',
                      color=text_color, fontsize=12, fontweight='bold')
        ax.set_title('Requests by Model',
                     color=text_color, fontsize=14, fontweight='bold', pad=20)
        
        if use_log_scale:
            ax.set_yscale('log')
            ax.grid(True, which='both', axis='y', linestyle='--', alpha=0.2, color=text_color)
        else:
            ax.grid(True, axis='y', linestyle='--', alpha=0.2, color=text_color)
        
        ax.tick_params(colors=text_color, labelsize=10)
        ax.set_facecolor(bg_color)
        ax.spines['bottom'].set_color(text_color)
        ax.spines['left'].set_color(text_color)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Rotate x-axis labels for better readability
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=9)
        
        # Add value labels on bars with smart positioning
        max(requests) if requests else 1
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                # Position label above bar, or inside if bar is tall enough
                label_y = height
                va = 'bottom'
                label_color = text_color
                
                ax.text(bar.get_x() + bar.get_width()/2., label_y,
                        f'{int(height):,}', 
                        ha='center', va=va, color=label_color, fontsize=9, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor=bg_color, 
                                edgecolor='none', alpha=0.7))
        
        # Adjust layout with proper spacing
        try:
            self.requests_chart.fig.tight_layout(pad=2.0)
        except:
            # If tight_layout fails, just draw without it
            pass
        self.requests_chart.draw()

    def render_tokens_chart(self, analytics):
        """Render the tokens chart with logarithmic scale for outliers"""
        if 'model_usage' not in analytics:
            return
        
        usage_data = analytics['model_usage']
        
        # Clear previous chart
        self.tokens_chart.fig.clear()
        
        # Create single subplot for tokens
        ax = self.tokens_chart.fig.add_subplot(111)
        
        # Get theme colors
        text_color = self.theme.text
        bg_color = self.theme.card_background
        self.theme.accent
        
        # Configure chart colors
        self.tokens_chart.fig.patch.set_facecolor(bg_color)
        
        # Extract data and sort by tokens (descending)
        models = list(usage_data.keys())
        tokens = [usage_data[m]['tokens'] for m in models]
        
        # Sort by tokens (descending) for better visualization
        sorted_indices = sorted(range(len(tokens)), key=lambda i: tokens[i], reverse=True)
        models = [models[i] for i in sorted_indices]
        tokens = [tokens[i] for i in sorted_indices]
        
        # Define vibrant color palette
        primary_colors = self.theme.chart_colors
        bar_colors = [primary_colors[i % len(primary_colors)] for i in range(len(models))]
        
        # Shorten model names for display if they're too long
        short_models = []
        for model in models:
            if len(model) > 20:
                parts = model.split('-')
                if len(parts) > 2:
                    short_models.append(f"{parts[0]}-{parts[-1]}")
                else:
                    short_models.append(model[:17] + "...")
            else:
                short_models.append(model)
        
        # Check if we need logarithmic scale
        non_zero_tokens = [t for t in tokens if t > 0]
        use_log_scale = False
        if non_zero_tokens and max(non_zero_tokens) > 10 * min(non_zero_tokens):
            use_log_scale = True
        
        # Plot tokens with rounded bars effect
        bars = ax.bar(short_models, tokens, color=bar_colors, width=0.7, edgecolor='none')
        ax.set_ylabel('Tokens (log scale)' if use_log_scale else 'Tokens',
                      color=text_color, fontsize=12, fontweight='bold')
        ax.set_title('Tokens by Model',
                     color=text_color, fontsize=14, fontweight='bold', pad=20)
        
        if use_log_scale:
            ax.set_yscale('log')
            ax.grid(True, which='both', axis='y', linestyle='--', alpha=0.2, color=text_color)
        else:
            ax.grid(True, axis='y', linestyle='--', alpha=0.2, color=text_color)
        
        ax.tick_params(colors=text_color, labelsize=10)
        ax.set_facecolor(bg_color)
        ax.spines['bottom'].set_color(text_color)
        ax.spines['left'].set_color(text_color)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Rotate x-axis labels for better readability
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=9)
        
        # Add value labels on bars - format large numbers nicely
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                # Format large numbers with K or M suffix
                if height >= 1000000:
                    label = f'{height/1000000:.1f}M'
                elif height >= 1000:
                    label = f'{height/1000:.0f}K'
                else:
                    label = f'{int(height)}'
                
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        label, 
                        ha='center', va='bottom', color=text_color, fontsize=9, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor=bg_color, 
                                edgecolor='none', alpha=0.7))
        
        # Adjust layout with proper spacing
        try:
            self.tokens_chart.fig.tight_layout(pad=2.0)
        except:
            # If tight_layout fails, just draw without it
            pass
        self.tokens_chart.draw()

    def render_cost_chart(self, analytics):
        """Render the cost breakdown pie chart with improved layout"""
        if 'cost_breakdown' not in analytics:
            return
        
        cost_data = analytics['cost_breakdown']
        
        # Clear previous chart
        self.cost_chart.fig.clear()
        
        # Create subplot for pie chart
        ax = self.cost_chart.fig.add_subplot(111)
        
        # Get theme colors
        text_color = self.theme.text
        bg_color = self.theme.card_background
        self.theme.accent
        
        # Configure chart colors
        self.cost_chart.fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
        
        # Extract data and sort by cost (descending)
        models = list(cost_data.keys())
        costs = list(cost_data.values())
        
        # Sort by cost descending
        sorted_indices = sorted(range(len(costs)), key=lambda i: costs[i], reverse=True)
        models = [models[i] for i in sorted_indices]
        costs = [costs[i] for i in sorted_indices]
        
        # Define vibrant color palette matching other charts
        colors_pie = self.theme.chart_colors + [
            '#E91E63',  # Additional pink for more slices
            '#795548',  # Additional brown for more slices
        ]
        
        # Filter to non-zero costs only
        non_zero_data = [(m, c) for m, c in zip(models, costs) if c > 0]
        if not non_zero_data:
            ax.text(0.5, 0.5, 'No cost data available', 
                   ha='center', va='center', color=text_color, fontsize=14,
                   transform=ax.transAxes)
            ax.set_title('💰 Cost Distribution', color=text_color, fontsize=14, fontweight='bold')
            self.cost_chart.draw()
            return
        
        models, costs = zip(*non_zero_data)
        models, costs = list(models), list(costs)
        total_cost = sum(costs)
        
        # Limit to top N models, group rest as "Other"
        MAX_SLICES = 10
        if len(models) > MAX_SLICES:
            top_models = models[:MAX_SLICES-1]
            top_costs = costs[:MAX_SLICES-1]
            other_cost = sum(costs[MAX_SLICES-1:])
            other_count = len(costs) - MAX_SLICES + 1
            top_models.append(f"Other ({other_count} models)")
            top_costs.append(other_cost)
            models, costs = top_models, top_costs
        
        # Shorten model names for legend - allow longer names for better readability
        short_models = []
        for model in models:
            if model.startswith("Other ("):
                short_models.append(model)
            elif len(model) > 35:
                parts = model.split('-')
                if len(parts) > 2:
                    short_models.append(f"{parts[0]}-{parts[1]}-...{parts[-1]}")
                else:
                    short_models.append(model[:32] + "...")
            else:
                short_models.append(model)
        
        # Assign colors
        filtered_colors = [colors_pie[i % len(colors_pie)] for i in range(len(costs))]
        
        # Create pie chart - no labels or autopct on chart, use legend only
        explode = [0.02 if i == 0 else 0 for i in range(len(costs))]
        
        wedges, _ = ax.pie(
            costs, 
            labels=None,
            autopct=None,  # No text on slices - cleaner look
            startangle=90,
            colors=filtered_colors,
            explode=explode,
            wedgeprops=dict(edgecolor=bg_color, linewidth=2, width=0.65),  # Donut style
        )
        
        # Add total cost in center of donut
        ax.text(0, 0, f'Total\n${total_cost:.2f}', 
               ha='center', va='center', fontsize=12, fontweight='bold', color=text_color)
        
        # Add title
        ax.set_title('Cost Distribution by Model',
                    color=text_color, fontsize=13, fontweight='bold', pad=10)
        
        # Build legend labels with cost and percentage
        legend_labels = []
        for short, cost in zip(short_models, costs):
            pct = (cost / total_cost) * 100
            legend_labels.append(f'{short}: ${cost:.4f} ({pct:.0f}%)')
        
        # Legend to the right of chart instead of below
        legend = ax.legend(wedges, legend_labels, 
                          loc='center left', 
                          bbox_to_anchor=(1.0, 0.5),
                          fontsize=9, 
                          frameon=True, 
                          facecolor=bg_color, 
                          edgecolor=text_color,
                          labelcolor=text_color)
        legend.get_frame().set_alpha(0.9)
        
        # Equal aspect ratio ensures that pie is drawn as a circle
        ax.axis('equal')
        
        # Adjust layout - give room for legend on right (smaller chart, more legend space)
        self.cost_chart.fig.subplots_adjust(right=0.45, left=0.05, top=0.9, bottom=0.1)
        
        # Refresh the canvas
        self.cost_chart.draw()

    def refresh_data(self):
        """Refresh all data and analytics"""
        if hasattr(self, 'analytics_worker') and self.analytics_worker is not None:
            if isValid(self.analytics_worker) and self.analytics_worker.isRunning():
                return  # Already updating
            # Clean up old worker
            self.analytics_worker = None

        self.refresh_btn.setText("🔄 Refreshing...")
        self.refresh_btn.setEnabled(False)

        self.analytics_worker = ModelAnalyticsWorker(parent=self)
        self.analytics_worker.analytics_ready.connect(self.on_refresh_complete)
        self.analytics_worker.finished.connect(self._on_analytics_worker_finished)
        self.analytics_worker.start()

    def connect_from_compare_tab(self):
        """Handle connect button click from the Compare & Analyze tab"""
        # Update button state
        self.connect_btn.setText("🔗 Connecting...")
        self.connect_btn.setEnabled(False)

        # Emit signal to main app to trigger connection
        self.signals.connect_requested.emit()

        # Reset button state after a short delay (will be updated when connection completes)
        QTimer.singleShot(2000, lambda: self.connect_btn.setText("🔗 Connect") or self.connect_btn.setEnabled(True))

    def on_refresh_complete(self, analytics):
        """Handle refresh completion"""
        self.update_analytics_display(analytics)
        self.refresh_btn.setText("🔄 Refresh")
        self.refresh_btn.setEnabled(True)

        # Also refresh model data if needed
        # This would typically fetch new model data from the API
    
    def update_theme(self, new_theme):
        """Update widget theme and redraw all components.
        
        Args:
            new_theme: New Theme object
        """
        self.theme = new_theme
        
        # Update all styled components
        self._apply_theme_to_widgets()
        
        # Redraw charts with new theme colors
        if self.current_analytics:
            self.render_requests_chart(self.current_analytics)
            self.render_tokens_chart(self.current_analytics)
            self.render_cost_chart(self.current_analytics)
    
    def _apply_theme_to_widgets(self):
        """Apply theme to all widgets in the comparison view."""
        # Update all components with theme-dependent styling
        
        # Update buttons
        if hasattr(self, 'connect_btn'):
            self.connect_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme.card_background};
                    color: {self.theme.text};
                    border: 1px solid {self.theme.accent};
                    border-radius: 4px;
                    padding: 6px 12px;
                }}
                QPushButton:hover {{
                    background-color: {self.theme.accent};
                }}
            """)
        
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme.card_background};
                    color: {self.theme.text};
                    border: 1px solid {self.theme.accent};
                    border-radius: 4px;
                    padding: 6px 12px;
                }}
                QPushButton:hover {{
                    background-color: {self.theme.accent};
                }}
            """)
        
        # Update tab widget
        if hasattr(self, 'tab_widget'):
            self.tab_widget.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: 1px solid {self.theme.border};
                    background-color: {self.theme.card_background};
                }}
                QTabBar::tab {{
                    background-color: {self.theme.button_background};
                    color: {self.theme.text};
                    padding: 8px 16px;
                    border: 1px solid {self.theme.border};
                }}
                QTabBar::tab:selected {{
                    background-color: {self.theme.accent};
                    color: {self.theme.text};
                }}
            """)
        
        # Update chart backgrounds
        if hasattr(self, 'requests_chart'):
            self.requests_chart.setStyleSheet(f"background-color: {self.theme.card_background};")
        if hasattr(self, 'tokens_chart'):
            self.tokens_chart.setStyleSheet(f"background-color: {self.theme.card_background};")
        if hasattr(self, 'cost_chart'):
            self.cost_chart.setStyleSheet(f"background-color: {self.theme.card_background};")
        
        # Update chart tabs widget
        if hasattr(self, 'chart_tabs'):
            self.chart_tabs.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: 1px solid {self.theme.accent};
                    background-color: {self.theme.background};
                }}
                QTabBar::tab {{
                    background-color: {self.theme.card_background};
                    color: {self.theme.text};
                    padding: 10px 20px;
                    margin-right: 2px;
                    border-radius: 4px 4px 0 0;
                    font-size: 13px;
                }}
                QTabBar::tab:selected {{
                    background-color: {self.theme.accent};
                    color: {self.theme.text};
                    font-weight: bold;
                }}
            """)
        
        # Update comparison table
        if hasattr(self, 'comparison_table'):
            self.comparison_table.setStyleSheet(f"""
                QTableWidget {{
                    background-color: {self.theme.background};
                    alternate-background-color: {self.theme.card_background};
                    color: {self.theme.text};
                    gridline-color: {self.theme.border};
                    border: 1px solid {self.theme.border};
                }}
                QTableWidget::item {{
                    color: {self.theme.text};
                    padding: 5px;
                }}
                QTableWidget::item:selected {{
                    background-color: {self.theme.accent};
                    color: {self.theme.text};
                }}
                QHeaderView::section {{
                    background-color: {self.theme.card_background};
                    color: {self.theme.text};
                    padding: 5px;
                    border: 1px solid {self.theme.border};
                    font-weight: bold;
                }}
            """)
        
        # Update search input
        if hasattr(self, 'search_input'):
            self.search_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {self.theme.input_background};
                    color: {self.theme.text};
                    border: 1px solid {self.theme.border};
                    border-radius: 4px;
                    padding: 6px;
                }}
                QLineEdit:focus {{
                    border: 2px solid {self.theme.accent};
                }}
            """)
        
        # Update comboboxes
        if hasattr(self, 'type_filter'):
            self.type_filter.setStyleSheet(self._get_combobox_style())
        
        # Update recommendation text
        if hasattr(self, 'recommendations_text'):
            self.recommendations_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {self.theme.card_background};
                    color: {self.theme.text};
                    border: 1px solid {self.theme.border};
                    border-radius: 4px;
                    padding: 10px;
                }}
            """)
        
        # Update Smart Recommendations QGroupBox
        for groupbox in self.findChildren(QGroupBox):
            if groupbox.title() == "Smart Recommendations":
                groupbox.setStyleSheet(f"""
                    QGroupBox {{
                        font-weight: bold;
                        border: 1px solid {self.theme.accent};
                        border-radius: 4px;
                        margin-top: 10px;
                        padding: 10px;
                        background-color: {self.theme.card_background};
                        color: {self.theme.text};
                    }}
                    QGroupBox::title {{
                        subcontrol-origin: margin;
                        left: 10px;
                        padding: 0 5px 0 5px;
                        color: {self.theme.accent};
                    }}
                """)
            elif "Search & Filter Models" in groupbox.title():
                groupbox.setStyleSheet(f"""
                    QGroupBox {{
                        font-weight: bold;
                        border: 1px solid {self.theme.accent};
                        border-radius: 4px;
                        margin-top: 10px;
                        padding: 10px;
                        background-color: {self.theme.card_background};
                        color: {self.theme.text};
                    }}
                    QGroupBox::title {{
                        subcontrol-origin: margin;
                        left: 10px;
                        padding: 0 5px 0 5px;
                        color: {self.theme.accent};
                    }}
                """)
        
        # Update Browse Models filter controls
        if hasattr(self, 'vision_chk'):
            for chk in [self.vision_chk, self.web_chk, self.function_chk, self.reasoning_chk]:
                chk.setStyleSheet(f"color: {self.theme.text}; margin-right: 10px;")
        
        # Update filter labels
        for label in self.findChildren(QLabel):
            # Skip labels that have specific styling (like results count)
            label.styleSheet()
            if "Type:" in label.text() or "Capabilities:" in label.text() or "Max Input" in label.text():
                label.setStyleSheet(f"color: {self.theme.text};")
            elif "models" in label.text() and hasattr(self, 'results_count_label') and label == self.results_count_label:
                label.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 12px;")
        
        # Update price filter input
        if hasattr(self, 'price_filter'):
            self.price_filter.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {self.theme.input_background};
                    color: {self.theme.text};
                    border: 1px solid {self.theme.accent};
                    border-radius: 4px;
                    padding: 4px;
                }}
            """)
