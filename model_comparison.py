"""
Model Comparison and Analytics Widget for Venice AI Model Viewer
Provides comprehensive comparison tools, usage analytics, and enhanced discovery features.
"""

import sys
from typing import List, Dict, Any, Optional
import json
from datetime import datetime, timedelta
import math

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QCheckBox, QGroupBox, QScrollArea,
    QFrame, QSplitter, QTextEdit, QLineEdit,
    QSizePolicy, QHeaderView, QProgressBar,
    QTabWidget, QTreeWidget, QTreeWidgetItem
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QThread
from PySide6.QtGui import QFont, QColor, QBrush, QIcon

# Matplotlib imports for chart rendering
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# HTTP requests for API calls
import requests
from datetime import timezone

from .config import Config
from .theme import Theme
from .usage_tracker import UsageWorker, APIKeyUsage


class ChartCanvas(FigureCanvas):
    """Custom matplotlib canvas for embedding charts in Qt"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Set transparent background
        self.fig.patch.set_alpha(0.0)
        
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

    def __init__(self, admin_key: str = None):
        super().__init__()
        self.admin_key = admin_key or Config.VENICE_ADMIN_KEY
        self.base_url = "https://api.venice.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.admin_key}",
            "Content-Type": "application/json"
        }

    def run(self):
        """Fetch and process analytics data from Venice API"""
        try:
            # Try to fetch real data from billing/usage endpoint
            usage_data = self._fetch_billing_usage(days=7)
            analytics = self._process_usage_data(usage_data)
            print(f"DEBUG: Successfully fetched real analytics data for {len(analytics.get('model_usage', {}))} models")
            
        except Exception as e:
            print(f"WARNING: Failed to fetch real analytics data: {e}")
            print("DEBUG: Falling back to mock data")
            # Fallback to mock data if API call fails
            analytics = self._get_mock_analytics()
        
        self.analytics_ready.emit(analytics)

    def _fetch_billing_usage(self, days: int = 7) -> List[Dict[str, Any]]:
        """Fetch real billing usage data from Venice API"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Format dates as ISO 8601 strings without microseconds (API expects this format)
        start_date_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_date_str = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        params = {
            'startDate': start_date_str,
            'endDate': end_date_str,
            'limit': 500,  # Get up to 500 recent entries
            'sortOrder': 'desc'
        }
        
        url = f"{self.base_url}/billing/usage"
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        return data.get('data', [])

    def _process_usage_data(self, usage_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process raw billing usage data into analytics format"""
        model_usage = {}
        cost_breakdown = {}
        performance_data = {}
        request_tracker = {}  # Track unique requests per model
        
        print(f"DEBUG: Processing {len(usage_entries)} usage entries")
        
        for entry in usage_entries:
            sku = entry.get('sku', 'unknown')
            amount = entry.get('amount', 0)
            currency = entry.get('currency', 'USD')
            inference = entry.get('inferenceDetails') or {}  # Handle None values
            
            print(f"DEBUG: Processing entry - SKU: {sku}, Amount: {amount}, Inference: {type(inference)}")
            
            # Use absolute value (negative amounts represent actual usage costs)
            abs_amount = abs(amount)
            
            # Skip zero amounts
            if abs_amount == 0:
                continue
            
            # Clean up model name (remove suffixes like '-llm-input-mtoken', '-llm-output-mtoken')
            model_name = sku.split('-llm-')[0] if '-llm-' in sku else sku
            model_name = model_name.replace('-mtoken', '').replace('-input', '').replace('-output', '')
            
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
                print(f"DEBUG: Found request {request_id} for model {model_name}")
            elif not request_id:
                # Only print debug for missing request IDs, not for duplicates
                if 'requestId' not in str(inference):
                    print(f"DEBUG: No requestId field in inference: {inference}")
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
            print("DEBUG: No valid usage data found, using mock data")
            return self._get_mock_analytics()
        
        print(f"DEBUG: Processed analytics for {len(model_usage)} models: {list(model_usage.keys())}")
        
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

        # Comparison Matrix Tab
        self.init_comparison_tab()

        # Analytics Dashboard Tab
        self.init_analytics_tab()

        # Discovery Tools Tab
        self.init_discovery_tab()

        layout.addWidget(self.tab_widget)

    def init_comparison_tab(self):
        """Initialize the model comparison matrix with usability focus"""
        comparison_tab = QWidget()
        layout = QVBoxLayout(comparison_tab)

        # Filtering controls
        filters_group = QGroupBox("Quick Filters")
        filters_group.setStyleSheet(f"""
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
        filters_layout = QHBoxLayout(filters_group)

        # Model type filter
        type_layout = QVBoxLayout()
        type_label = QLabel("Type:")
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All", "text", "image", "tts", "embedding", "upscale", "inpaint"])
        self.type_filter.currentTextChanged.connect(self.apply_filters)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_filter)
        filters_layout.addLayout(type_layout)

        # Capability filters
        capabilities_layout = QVBoxLayout()
        capabilities_layout.addWidget(QLabel("Capabilities:"))

        self.vision_chk = QCheckBox("Vision")
        self.web_chk = QCheckBox("Web Search")
        self.function_chk = QCheckBox("Functions")
        self.reasoning_chk = QCheckBox("Reasoning")

        for chk in [self.vision_chk, self.web_chk, self.function_chk, self.reasoning_chk]:
            chk.stateChanged.connect(self.apply_filters)
            chk.setStyleSheet(f"color: {self.theme.text};")
            capabilities_layout.addWidget(chk)

        filters_layout.addLayout(capabilities_layout)

        # Price range filter
        price_layout = QVBoxLayout()
        price_layout.addWidget(QLabel("Max Input $/1K:"))
        self.price_filter = QLineEdit("10000")
        self.price_filter.textChanged.connect(self.apply_filters)
        self.price_filter.setMaximumWidth(80)
        price_layout.addWidget(self.price_filter)
        filters_layout.addLayout(price_layout)

        filters_layout.addStretch()
        layout.addWidget(filters_group)

        # Comparison table
        self.comparison_table = QTableWidget()
        self.setup_comparison_table()
        layout.addWidget(self.comparison_table)

        self.tab_widget.addTab(comparison_tab, "🔍 Compare")

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
        self.recommendations_text.setMaximumHeight(180)
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

    def init_discovery_tab(self):
        """Initialize the discovery tools"""
        discovery_tab = QWidget()
        layout = QVBoxLayout(discovery_tab)

        # Search and filtering
        search_group = QGroupBox("Advanced Search")
        search_layout = QHBoxLayout(search_group)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search models by name, trait, or capability...")
        self.search_input.textChanged.connect(self.search_models)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.theme.input_background};
                color: {self.theme.text};
                border: 1px solid {self.theme.accent};
                border-radius: 4px;
                padding: 6px;
                font-size: 14px;
            }}
        """)
        search_layout.addWidget(self.search_input)

        search_layout.addStretch()
        layout.addWidget(search_group)

        # Results with enhanced display
        results_group = QGroupBox("Model Discovery Results")
        results_layout = QVBoxLayout(results_group)

        # Results list with rich display
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["Model", "Type", "Key Features", "Pricing"])
        self.setup_results_tree()
        results_layout.addWidget(self.results_tree)

        layout.addWidget(results_group)
        self.tab_widget.addTab(discovery_tab, "🎯 Discover")

    def setup_comparison_table(self):
        """Setup the comparative table with proper styling"""
        headers = ["Model", "Type", "Context", "Vision", "Functions", "Web Search", "Input $/1K", "Output $/1K", "Rating"]

        self.comparison_table.setColumnCount(len(headers))
        self.comparison_table.setHorizontalHeaderLabels(headers)

        # Set column properties
        self.comparison_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.comparison_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                border: 1px solid {self.theme.accent};
                border-radius: 4px;
                gridline-color: {self.theme.accent};
            }}
            QHeaderView::section {{
                background-color: {self.theme.background};
                color: {self.theme.text};
                padding: 8px;
                border: 1px solid {self.theme.accent};
                font-weight: bold;
            }}
        """)

        # Populate with model data
        self.populate_comparison_table()

    def populate_comparison_table(self):
        """Populate the comparison table with model data"""
        if not self.models_data or 'data' not in self.models_data:
            return

        self.comparison_table.setRowCount(0)

        for i, model in enumerate(self.models_data['data']):
            model_id = model.get('id', 'Unknown')
            model_spec = model.get('model_spec', {})
            model_type = model.get('type', 'unknown')
            capabilities = model_spec.get('capabilities', {})
            pricing = model_spec.get('pricing', {})

            self.comparison_table.insertRow(i)

            # Model name
            model_item = QTableWidgetItem(model_id)
            model_item.setToolTip(f"Model: {model_id}")
            self.comparison_table.setItem(i, 0, model_item)

            # Type
            type_item = QTableWidgetItem(model_type)
            self.comparison_table.setItem(i, 1, type_item)

            # Context tokens
            context = model_spec.get('availableContextTokens', 'N/A')
            context_item = QTableWidgetItem(str(context) if context else 'N/A')
            self.comparison_table.setItem(i, 2, context_item)

            # Capabilities with icons
            vision = "✓" if capabilities.get('supportsVision') else "✗"
            vision_item = QTableWidgetItem(vision)
            vision_item.setBackground(QColor("#e8f5e8") if capabilities.get('supportsVision') else QColor("#fce8e6"))
            self.comparison_table.setItem(i, 3, vision_item)

            functions = "✓" if capabilities.get('supportsFunctionCalling') else "✗"
            functions_item = QTableWidgetItem(functions)
            functions_item.setBackground(QColor("#e8f5e8") if capabilities.get('supportsFunctionCalling') else QColor("#fce8e6"))
            self.comparison_table.setItem(i, 4, functions_item)

            web_search = "✓" if capabilities.get('supportsWebSearch') else "✗"
            web_search_item = QTableWidgetItem(web_search)
            web_search_item.setBackground(QColor("#e8f5e8") if capabilities.get('supportsWebSearch') else QColor("#fce8e6"))
            self.comparison_table.setItem(i, 5, web_search_item)

            # Pricing
            input_cost = pricing.get('input', {}).get('usd', 0) * 1000
            output_cost = pricing.get('output', {}).get('usd', 0) * 1000

            input_item = QTableWidgetItem(f"${input_cost:.3f}")
            input_item.setData(Qt.DisplayRole, input_cost)  # For sorting
            self.comparison_table.setItem(i, 6, input_item)

            output_item = QTableWidgetItem(f"${output_cost:.3f}")
            output_item.setData(Qt.DisplayRole, output_cost)  # For sorting
            self.comparison_table.setItem(i, 7, output_item)

            # Placeholder rating (would come from usage data)
            rating_item = QTableWidgetItem("★★★★☆")  # Mock rating
            self.comparison_table.setItem(i, 8, rating_item)

        self.comparison_table.resizeColumnsToContents()

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
                            item.setBackground(QColor("#fce8e6"))
                        elif time_val < 1.5:
                            item.setBackground(QColor("#e8f5e8"))
                    except ValueError:
                        pass
                elif j == 2:  # Success rate column
                    try:
                        rate_val = float(value[:-1])  # Remove '%'
                        if rate_val < 98:
                            item.setBackground(QColor("#fce8e6"))
                        elif rate_val > 99:
                            item.setBackground(QColor("#e8f5e8"))
                    except ValueError:
                        pass
                self.performance_table.setItem(i, j, item)

    def setup_results_tree(self):
        """Setup the discovery results tree with rich display"""
        self.results_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                border: 1px solid {self.theme.accent};
                border-radius: 4px;
            }}
            QHeaderView::section {{
                background-color: {self.theme.background};
                color: {self.theme.text};
                padding: 8px;
                border: 1px solid {self.theme.accent};
                font-weight: bold;
            }}
        """)

        self.results_tree.setColumnWidth(0, 200)
        self.results_tree.setColumnWidth(1, 100)
        self.results_tree.setColumnWidth(2, 300)
        self.results_tree.setColumnWidth(3, 150)

        self.populate_discovery_results()

    def populate_discovery_results(self):
        """Populate discovery results based on search and filters"""
        self.results_tree.clear()

        if not self.models_data or 'data' not in self.models_data:
            return

        # Add root categories
        text_category = QTreeWidgetItem(["Text Models", "", "", ""])
        image_category = QTreeWidgetItem(["Image Models", "", "", ""])
        tts_category = QTreeWidgetItem(["TTS Models", "", "", ""])
        embedding_category = QTreeWidgetItem(["Embedding Models", "", "", ""])

        for model in self.models_data['data']:
            model_item = self.create_model_tree_item(model)
            model_type = model.get('type', 'unknown')

            if model_type == 'text':
                text_category.addChild(model_item)
            elif model_type == 'image':
                image_category.addChild(model_item)
            elif model_type == 'tts':
                tts_category.addChild(model_item)
            elif model_type == 'embedding':
                embedding_category.addChild(model_item)

        # Add categories that have children
        if text_category.childCount() > 0:
            self.results_tree.addTopLevelItem(text_category)
            text_category.setExpanded(True)
        if image_category.childCount() > 0:
            self.results_tree.addTopLevelItem(image_category)
            image_category.setExpanded(False)
        if tts_category.childCount() > 0:
            self.results_tree.addTopLevelItem(tts_category)
            tts_category.setExpanded(False)
        if embedding_category.childCount() > 0:
            self.results_tree.addTopLevelItem(embedding_category)
            embedding_category.setExpanded(False)

    def create_model_tree_item(self, model):
        """Create rich tree item for model display"""
        model_id = model.get('id', 'Unknown')
        model_type = model.get('type', 'unknown')
        model_spec = model.get('model_spec', {})
        capabilities = model_spec.get('capabilities', {})
        pricing = model_spec.get('pricing', {})

        # Build features string
        features = []
        if capabilities.get('supportsVision'):
            features.append("🎨 Vision")
        if capabilities.get('supportsFunctionCalling'):
            features.append("🔧 Functions")
        if capabilities.get('supportsWebSearch'):
            features.append("🌐 Web")
        if capabilities.get('supportsReasoning'):
            features.append("🧠 Reasoning")
        if model_spec.get('traits'):
            features.extend([f"🏷️ {trait}" for trait in model_spec['traits'][:2]])  # Show first 2 traits

        features_str = ", ".join(features) if features else "—"

        # Build pricing string
        pricing_str = "—"
        if model_type == 'text' and 'input' in pricing:
            input_cost = pricing['input'].get('usd', 0) * 1000
            output_cost = pricing.get('output', {}).get('usd', 0) * 1000
            pricing_str = f"Input: ${input_cost:.3f}/1K\nOutput: ${output_cost:.3f}/1K"

        item = QTreeWidgetItem([model_id, model_type.capitalize(), features_str, pricing_str])
        item.setToolTip(1, model_id)  # Show full model ID on hover

        return item

    def apply_filters(self):
        """Apply current filters to the comparison table"""
        model_type = self.type_filter.currentText().lower()

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
                # Check model type
                if model_type != "all" and model.get('type', '').lower() != model_type:
                    continue

                model_spec = model.get('model_spec', {})
                capabilities = model_spec.get('capabilities', {})
                pricing = model_spec.get('pricing', {})

                # Check capabilities
                caps_match = True
                for cap in required_caps:
                    if not capabilities.get(cap, False):
                        caps_match = False
                        break

                if not caps_match:
                    continue

                # Check price
                input_cost = pricing.get('input', {}).get('usd', 0) * 1000
                if input_cost > max_price:
                    continue

                filtered_models.append(model)

        # Create a DISPLAY-only copy - NEVER modify the original data
        if self.original_models_data:
            self.models_data = self.original_models_data.copy()
            self.models_data['data'] = filtered_models
        else:
            self.models_data = {'data': filtered_models}

        # Refresh the display with filtered results
        self.populate_comparison_table()
        self.populate_discovery_results()

    def search_models(self, query):
        """Search models by name, trait, or capability"""
        if not query:
            self.populate_discovery_results()
            return

        query_lower = query.lower()
        self.results_tree.clear()

        if not self.models_data or 'data' not in self.models_data:
            return

        found_models = []
        for model in self.models_data['data']:
            model_id = model.get('id', '').lower()
            model_spec = model.get('model_spec', {})
            capabilities = model_spec.get('capabilities', {})
            traits = model_spec.get('traits', [])

            # Search in model ID
            if query_lower in model_id:
                found_models.append(model)
                continue

            # Search in traits
            if any(query_lower in trait.lower() for trait in traits):
                found_models.append(model)
                continue

            # Search in capabilities
            cap_matches = []
            for cap_name, cap_enabled in capabilities.items():
                if cap_enabled and query_lower in cap_name.lower().replace('supports', ''):
                    cap_matches.append(cap_name)

            if cap_matches:
                found_models.append(model)

        # Display results safely
        for model in found_models:
            item = self.create_model_tree_item(model)
            self.results_tree.addTopLevelItem(item)

        # If no matches found, show empty results
        if not found_models:
            empty_item = QTreeWidgetItem(["No models found", "", "", ""])
            self.results_tree.addTopLevelItem(empty_item)

    def start_analytics_update(self):
        """Start periodic analytics updates"""
        self.analytics_worker = ModelAnalyticsWorker()
        self.analytics_worker.analytics_ready.connect(self.update_analytics_display)
        self.analytics_worker.start()

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

    def render_requests_chart(self, analytics):
        """Render the requests chart with logarithmic scale for outliers"""
        if 'model_usage' not in analytics:
            return
        
        usage_data = analytics['model_usage']
        
        # Clear previous chart
        self.requests_chart.fig.clear()
        
        # Create single subplot for requests
        ax = self.requests_chart.fig.add_subplot(111)
        
        # Get theme colors - determine if we're in dark mode
        is_dark = self.theme.background == "#1e1e1e"
        text_color = '#ffffff' if is_dark else '#000000'
        bg_color = self.theme.card_background
        
        # Configure chart colors
        self.requests_chart.fig.patch.set_facecolor(bg_color)
        
        # Extract data and sort by values (descending)
        models = list(usage_data.keys())
        requests = [usage_data[m]['requests'] for m in models]
        
        # Sort by requests (descending) for better visualization
        sorted_indices = sorted(range(len(requests)), key=lambda i: requests[i], reverse=True)
        models = [models[i] for i in sorted_indices]
        requests = [requests[i] for i in sorted_indices]
        
        # Define color palette - use gradient for sorted data
        colors = ['#4CAF50', '#66BB6A', '#81C784', '#A5D6A7', '#C8E6C9', '#E8F5E9']
        bar_colors = [colors[i % len(colors)] for i in range(len(models))]
        
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
        
        # Plot requests
        bars = ax.bar(short_models, requests, color=bar_colors, width=0.6)
        ax.set_ylabel('Requests (log scale)' if use_log_scale else 'Requests', 
                      color=text_color, fontsize=11)
        ax.set_title('Requests by Model (Sorted by Volume)', 
                     color=text_color, fontsize=13, fontweight='bold', pad=15)
        
        if use_log_scale:
            ax.set_yscale('log')
            ax.grid(True, which='both', axis='y', linestyle='--', alpha=0.3, color=text_color)
        
        ax.tick_params(colors=text_color, labelsize=10)
        ax.set_facecolor(bg_color)
        ax.spines['bottom'].set_color(text_color)
        ax.spines['left'].set_color(text_color)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Rotate x-axis labels for better readability
        ax.tick_params(axis='x', rotation=45, labelsize=9)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height):,}', 
                        ha='center', va='bottom', color=text_color, fontsize=9,
                        bbox=dict(boxstyle='round,pad=0.3', facecolor=bg_color, 
                                edgecolor='none', alpha=0.8))
        
        # Adjust layout
        self.requests_chart.fig.subplots_adjust(left=0.08, right=0.98, top=0.93, bottom=0.15)
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
        
        
        # Get theme colors - determine if we're in dark mode
        is_dark = self.theme.background == "#1e1e1e"
        text_color = '#ffffff' if is_dark else '#000000'
        bg_color = self.theme.card_background
        
        # Configure chart colors
        self.tokens_chart.fig.patch.set_facecolor(bg_color)
        
        # Extract data and sort by tokens (descending)
        models = list(usage_data.keys())
        tokens = [usage_data[m]['tokens'] for m in models]
        
        # Sort by tokens (descending) for better visualization
        sorted_indices = sorted(range(len(tokens)), key=lambda i: tokens[i], reverse=True)
        models = [models[i] for i in sorted_indices]
        tokens = [tokens[i] for i in sorted_indices]
        
        # Define color palette - use gradient for sorted data
        colors = ['#4CAF50', '#66BB6A', '#81C784', '#A5D6A7', '#C8E6C9', '#E8F5E9']
        bar_colors = [colors[i % len(colors)] for i in range(len(models))]
        
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
        
        # Plot tokens
        bars = ax.bar(short_models, tokens, color=bar_colors, width=0.6)
        ax.set_ylabel('Tokens (log scale)' if use_log_scale else 'Tokens', 
                      color=text_color, fontsize=11)
        ax.set_title('Tokens by Model (Sorted by Volume)', 
                     color=text_color, fontsize=13, fontweight='bold', pad=15)
        
        if use_log_scale:
            ax.set_yscale('log')
            ax.grid(True, which='both', axis='y', linestyle='--', alpha=0.3, color=text_color)
        
        ax.tick_params(colors=text_color, labelsize=10)
        ax.set_facecolor(bg_color)
        ax.spines['bottom'].set_color(text_color)
        ax.spines['left'].set_color(text_color)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Rotate x-axis labels for better readability
        ax.tick_params(axis='x', rotation=45, labelsize=9)
        
        # Add value labels on bars - format large numbers nicely
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                # Format large numbers with K or M suffix
                if height >= 1000000:
                    label = f'{height/1000000:.2f}M'
                elif height >= 1000:
                    label = f'{height/1000:.1f}K'
                else:
                    label = f'{int(height)}'
                
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        label, 
                        ha='center', va='bottom', color=text_color, fontsize=9,
                        bbox=dict(boxstyle='round,pad=0.3', facecolor=bg_color, 
                                edgecolor='none', alpha=0.8))
        
        # Adjust layout
        self.tokens_chart.fig.subplots_adjust(left=0.08, right=0.98, top=0.93, bottom=0.15)
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
        is_dark = self.theme.background == "#1e1e1e"
        text_color = '#ffffff' if is_dark else '#000000'
        bg_color = self.theme.card_background
        
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
        
        # Define color palette with gradient
        colors_pie = ['#4CAF50', '#66BB6A', '#81C784', '#A5D6A7', '#C8E6C9', '#E8F5E9']
        
        # Shorten model names for display if they're too long
        short_models = []
        for model in models:
            if len(model) > 15:
                # Keep first part and last part, truncate middle
                parts = model.split('-')
                if len(parts) > 2:
                    short_models.append(f"{parts[0]}-{parts[-1]}")
                else:
                    short_models.append(model[:12] + "...")
            else:
                short_models.append(model)
        
        # Only show models with non-zero costs
        filtered_models = []
        filtered_costs = []
        filtered_colors = []
        filtered_short_models = []
        
        for i, (model, cost, short_model) in enumerate(zip(models, costs, short_models)):
            if cost > 0:
                filtered_models.append(model)
                filtered_costs.append(cost)
                filtered_colors.append(colors_pie[i % len(colors_pie)])
                filtered_short_models.append(short_model)
        
        if not filtered_costs:
            # No costs to display
            ax.text(0.5, 0.5, 'No cost data available', 
                   ha='center', va='center', color=text_color, fontsize=12,
                   transform=ax.transAxes)
            ax.set_title('Cost Distribution by Model', color=text_color, fontsize=12, fontweight='bold')
            self.cost_chart.draw()
            return
        
        # Calculate total cost for percentage display
        total_cost = sum(filtered_costs)
        
        # Custom autopct function to show both percentage and amount
        def make_autopct(values):
            def my_autopct(pct):
                total = sum(values)
                val = pct * total / 100.0
                # Only show percentage if > 5%, otherwise it's too small to read
                if pct > 5:
                    return f'{pct:.1f}%\n${val:.4f}'
                elif pct > 1:
                    return f'{pct:.1f}%'
                else:
                    return ''
            return my_autopct
        
        # Create pie chart with better spacing
        wedges, texts, autotexts = ax.pie(
            filtered_costs, 
            labels=None,  # Remove labels from pie slices
            autopct=make_autopct(filtered_costs),
            startangle=90,
            colors=filtered_colors,
            textprops={'color': 'white', 'fontsize': 10, 'fontweight': 'bold'},
            wedgeprops=dict(edgecolor=bg_color, linewidth=2),
            pctdistance=0.7
        )
        
        # Add title with total cost - shorter to fit better
        ax.set_title(f'Cost by Model (${total_cost:.2f} total)', 
                    color=text_color, fontsize=13, fontweight='bold', pad=15)
        
        # Add legend BELOW the chart for better space utilization
        legend_labels = []
        for short, cost in zip(filtered_short_models, filtered_costs):
            pct = (cost / total_cost) * 100
            legend_labels.append(f'{short}: ${cost:.4f} ({pct:.1f}%)')
        
        ax.legend(legend_labels, loc='lower center', bbox_to_anchor=(0.5, -0.25), 
                 fontsize=9, frameon=True, facecolor=bg_color, edgecolor=text_color,
                 labelcolor=text_color, ncol=2, title="Models (Sorted by Cost)", title_fontsize=10)
        
        # Equal aspect ratio ensures that pie is drawn as a circle
        ax.axis('equal')
        
        # Adjust layout with space at bottom for legend
        self.cost_chart.fig.subplots_adjust(left=0.05, right=0.95, top=0.90, bottom=0.30)
        
        # Refresh the canvas
        self.cost_chart.draw()

    def refresh_data(self):
        """Refresh all data and analytics"""
        if self.analytics_worker and self.analytics_worker.isRunning():
            return  # Already updating

        self.refresh_btn.setText("🔄 Refreshing...")
        self.refresh_btn.setEnabled(False)

        self.analytics_worker = ModelAnalyticsWorker()
        self.analytics_worker.analytics_ready.connect(self.on_refresh_complete)
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
