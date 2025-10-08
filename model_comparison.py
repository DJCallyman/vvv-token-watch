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

from .config import Config
from .theme import Theme
from .usage_tracker import UsageWorker, APIKeyUsage


class ComparisonSignals(QObject):
    """Signals for ModelComparisonWidget to communicate with main app"""
    connect_requested = Signal()


class ModelAnalyticsWorker(QThread):
    """Worker thread for fetching and processing model analytics data"""
    analytics_ready = Signal(dict)

    def __init__(self, admin_key: str = None):
        super().__init__()
        self.admin_key = admin_key or Config.VENICE_ADMIN_KEY

    def run(self):
        """Fetch and process analytics data"""
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

        self.analytics_ready.emit(analytics)

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
        performance = analytics['performance_metrics']
        for model, metrics in performance.items():
            if metrics['success_rate'] < 98:
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
        self.type_filter.addItems(["All", "text", "image", "tts", "embedding", "upscale"])
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
        self.price_filter = QLineEdit("10.0")
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
        """Initialize the analytics dashboard"""
        analytics_tab = QWidget()
        layout = QHBoxLayout(analytics_tab)

        # Left side - Charts
        charts_panel = QWidget()
        charts_layout = QVBoxLayout(charts_panel)

        # Usage chart placeholder
        usage_group = QGroupBox("Usage by Model")
        usage_layout = QVBoxLayout(usage_group)
        self.usage_chart_label = QLabel("Chart will be rendered here")
        self.usage_chart_label.setAlignment(Qt.AlignCenter)
        self.usage_chart_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme.text};
                background-color: {self.theme.card_background};
                border: 1px dashed {self.theme.accent};
                padding: 40px;
                border-radius: 4px;
            }}
        """)
        usage_layout.addWidget(self.usage_chart_label)
        charts_layout.addWidget(usage_group)

        # Cost breakdown
        cost_group = QGroupBox("Cost Breakdown")
        cost_layout = QVBoxLayout(cost_group)
        self.cost_chart_label = QLabel("Cost visualization coming soon")
        self.cost_chart_label.setAlignment(Qt.AlignCenter)
        self.cost_chart_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme.text};
                background-color: {self.theme.card_background};
                border: 1px dashed {self.theme.accent};
                padding: 30px;
                border-radius: 4px;
            }}
        """)
        cost_layout.addWidget(self.cost_chart_label)
        charts_layout.addWidget(cost_group)

        layout.addWidget(charts_panel, 2)

        # Right side - Details and recommendations
        details_panel = QWidget()
        details_layout = QVBoxLayout(details_panel)

        # Performance metrics table
        perf_group = QGroupBox("Performance Metrics")
        perf_layout = QVBoxLayout(perf_group)
        self.performance_table = QTableWidget()
        self.setup_performance_table()
        perf_layout.addWidget(self.performance_table)
        details_layout.addWidget(perf_group)

        # Recommendations panel
        rec_group = QGroupBox("Smart Recommendations")
        rec_layout = QVBoxLayout(rec_group)
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setReadOnly(True)
        self.recommendations_text.setMaximumHeight(150)
        self.recommendations_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                border: 1px solid {self.theme.accent};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        rec_layout.addWidget(self.recommendations_text)
        details_layout.addWidget(rec_group)

        layout.addWidget(details_panel, 1)

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
        max_price = 100.0  # Default high value
        try:
            if self.price_filter.text():
                max_price = float(self.price_filter.text())
        except ValueError:
            max_price = 100.0

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

        # Update performance table with real data
        if 'model_usage' in analytics:
            perf_data = analytics['performance_metrics']
            self.performance_table.setRowCount(len(perf_data))

            for i, (model, metrics) in enumerate(perf_data.items()):
                usage_data = analytics.get('model_usage', {}).get(model, {})

                row_data = [
                    model,
                    f"{metrics['avg_response_time']:.1f}s",
                    f"{metrics['success_rate']:.1f}%",
                    f"{usage_data.get('requests', 0):,}",
                    f"{usage_data.get('tokens', 0):,}"
                ]

                for j, value in enumerate(row_data):
                    item = QTableWidgetItem(str(value))
                    # Color coding for performance
                    if j == 1:  # Response time
                        time_val = float(value[:-1])
                        if time_val > 3:
                            item.setBackground(QColor("#fce8e6"))
                        elif time_val < 1.5:
                            item.setBackground(QColor("#e8f5e8"))
                    elif j == 2:  # Success rate
                        rate_val = float(value[:-1])
                        if rate_val < 98:
                            item.setBackground(QColor("#fce8e6"))
                        elif rate_val > 99:
                            item.setBackground(QColor("#e8f5e8"))

                    self.performance_table.setItem(i, j, item)

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
