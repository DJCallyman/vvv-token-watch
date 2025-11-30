"""
Cost Optimization Widget for displaying model cost analysis and recommendations.

This widget shows users how to optimize their DIEM/USD spending by identifying
opportunities to switch to more cost-effective models.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
                              QProgressBar, QFrame, QTabWidget, QComboBox, QSpinBox,
                              QSizePolicy, QScrollArea)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QColor, QBrush
from shiboken6 import isValid
from typing import List, Dict, Optional
import logging

from src.analytics.cost_optimizer import (CostOptimizer, CostOptimizationReport,
                                          ModelUsageStats, CostSavingsRecommendation)
from src.config.theme import Theme
from src.utils.utils import format_currency


logger = logging.getLogger(__name__)


class CostOptimizerWorker(QThread):
    """Worker thread for analyzing cost optimization"""
    analysis_complete = Signal(object)  # CostOptimizationReport
    error_occurred = Signal(str)
    
    def __init__(self, billing_data: List[Dict], api_keys_data: List[Dict] = None, analysis_days: int = 7, parent=None):
        super().__init__(parent)  # Important: parent prevents premature garbage collection
        self.billing_data = billing_data
        self.api_keys_data = api_keys_data or []
        self.analysis_days = analysis_days
        # Note: finished signal connections are set up by the caller (update_analysis)
    
    def run(self):
        """Run cost analysis in background thread"""
        try:
            optimizer = CostOptimizer()
            
            # Set API key usage data if available
            if self.api_keys_data:
                optimizer.set_api_key_usage(self.api_keys_data)
            
            optimizer.analyze_billing_data(self.billing_data)
            report = optimizer.generate_report(self.analysis_days)
            self.analysis_complete.emit(report)
        except Exception as e:
            # Don't use logger in worker thread - emit signal for main thread to log
            self.error_occurred.emit(f"Cost analysis failed: {e}")


class CostOptimizationWidget(QWidget):
    """
    Widget for displaying cost optimization analysis and recommendations.
    
    Shows:
    - Current spending breakdown by model
    - Cost-saving recommendations
    - Model comparison calculator
    - Potential monthly savings
    """
    
    refresh_requested = Signal()
    
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.current_report: Optional[CostOptimizationReport] = None
        self.worker: Optional[CostOptimizerWorker] = None
        
        self.init_ui()
    
    def _cleanup_worker(self):
        """Safely stop and clean up any running worker."""
        if self.worker is not None:
            # Check if C++ object is still valid before accessing it
            if not isValid(self.worker):
                self.worker = None
                return
            
            # Disconnect signals first to prevent callbacks during cleanup
            try:
                self.worker.analysis_complete.disconnect()
                self.worker.error_occurred.disconnect()
                self.worker.finished.disconnect()
            except (RuntimeError, TypeError):
                pass  # Signals may already be disconnected
            
            if self.worker.isRunning():
                self.worker.quit()
                # Wait with a longer timeout - don't terminate, let it finish
                if not self.worker.wait(5000):
                    # Only terminate as last resort
                    self.worker.terminate()
                    self.worker.wait(1000)
            
            self.worker = None
    
    def _on_worker_finished(self):
        """Called when worker finishes - clear reference before deleteLater runs."""
        self.worker = None
    
    def closeEvent(self, event):
        """Clean up worker when widget is closed."""
        self._cleanup_worker()
        super().closeEvent(event)
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Tab widget for different views
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(self._get_tab_style())
        
        # Tab 1: Model Breakdown
        self.breakdown_tab = self._create_breakdown_tab()
        self.tabs.addTab(self.breakdown_tab, "📊 Spending Breakdown")
        
        # Tab 2: Recommendations
        self.recommendations_tab = self._create_recommendations_tab()
        self.tabs.addTab(self.recommendations_tab, "💡 Recommendations")
        
        # Tab 3: Model Comparison Calculator
        self.calculator_tab = self._create_calculator_tab()
        self.tabs.addTab(self.calculator_tab, "🔢 Cost Calculator")
        
        layout.addWidget(self.tabs)
        
        self.setLayout(layout)
    
    def _create_header(self) -> QWidget:
        """Create header with title and controls"""
        header_widget = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("💰 Cost Optimization Advisor")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet(f"color: {self.theme.text};")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Analysis")
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        refresh_btn.setStyleSheet(self._get_button_style())
        header_layout.addWidget(refresh_btn)
        
        header_widget.setLayout(header_layout)
        return header_widget
    
    def _create_breakdown_tab(self) -> QWidget:
        """Create model spending breakdown tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Summary stats
        summary_group = QGroupBox("📈 Spending Summary")
        summary_group.setStyleSheet(self._get_groupbox_style())
        summary_layout = QHBoxLayout()
        
        self.total_diem_label = QLabel("Total DIEM: --")
        self.total_usd_label = QLabel("Total USD: --")
        self.period_label = QLabel("Period: --")
        
        for label in [self.total_diem_label, self.total_usd_label, self.period_label]:
            label.setFont(QFont("Arial", 11))
            label.setStyleSheet(f"color: {self.theme.text}; padding: 5px;")
            summary_layout.addWidget(label)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # Model breakdown table
        breakdown_group = QGroupBox("📊 Spending by Model")
        breakdown_group.setStyleSheet(self._get_groupbox_style())
        breakdown_layout = QVBoxLayout()
        
        self.breakdown_table = QTableWidget()
        self.breakdown_table.setColumnCount(5)
        self.breakdown_table.setHorizontalHeaderLabels([
            "Model", "Requests", "Avg Tokens", "Total Cost", "% of Total"
        ])
        self.breakdown_table.horizontalHeader().setStretchLastSection(True)
        self.breakdown_table.setStyleSheet(self._get_table_style())
        self.breakdown_table.setAlternatingRowColors(True)
        
        breakdown_layout.addWidget(self.breakdown_table)
        breakdown_group.setLayout(breakdown_layout)
        layout.addWidget(breakdown_group)
        
        widget.setLayout(layout)
        return widget
    
    def _create_recommendations_tab(self) -> QWidget:
        """Create recommendations tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Savings summary
        savings_group = QGroupBox("💰 Potential Savings")
        savings_group.setStyleSheet(self._get_groupbox_style())
        savings_layout = QVBoxLayout()
        
        self.monthly_savings_label = QLabel("Potential Monthly Savings: --")
        self.monthly_savings_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.monthly_savings_label.setStyleSheet(f"color: {self.theme.accent}; padding: 10px;")
        savings_layout.addWidget(self.monthly_savings_label)
        
        savings_group.setLayout(savings_layout)
        layout.addWidget(savings_group)
        
        # Recommendations table
        rec_group = QGroupBox("💡 Optimization Recommendations")
        rec_group.setStyleSheet(self._get_groupbox_style())
        rec_layout = QVBoxLayout()
        
        self.recommendations_table = QTableWidget()
        self.recommendations_table.setColumnCount(7)
        self.recommendations_table.setHorizontalHeaderLabels([
            "Current Model", "Recommended Model", "API Keys Using", "Requests", "Savings", "Confidence", "Reason"
        ])
        self.recommendations_table.horizontalHeader().setStretchLastSection(True)
        self.recommendations_table.setStyleSheet(self._get_table_style())
        self.recommendations_table.setAlternatingRowColors(True)
        
        rec_layout.addWidget(self.recommendations_table)
        rec_group.setLayout(rec_layout)
        layout.addWidget(rec_group)
        
        widget.setLayout(layout)
        return widget
    
    def _create_calculator_tab(self) -> QWidget:
        """Create model comparison calculator tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Calculator group
        calc_group = QGroupBox("🔢 Cost Comparison Calculator")
        calc_group.setStyleSheet(self._get_groupbox_style())
        calc_layout = QVBoxLayout()
        
        # Input controls
        inputs_layout = QHBoxLayout()
        
        # Model 1 selector
        model1_label = QLabel("Model 1:")
        model1_label.setStyleSheet(f"color: {self.theme.text};")
        self.model1_combo = QComboBox()
        self.model1_combo.setStyleSheet(self._get_combo_style())
        inputs_layout.addWidget(model1_label)
        inputs_layout.addWidget(self.model1_combo)
        
        # Model 2 selector
        model2_label = QLabel("Model 2:")
        model2_label.setStyleSheet(f"color: {self.theme.text};")
        self.model2_combo = QComboBox()
        self.model2_combo.setStyleSheet(self._get_combo_style())
        inputs_layout.addWidget(model2_label)
        inputs_layout.addWidget(self.model2_combo)
        
        calc_layout.addLayout(inputs_layout)
        
        # Token inputs
        tokens_layout = QHBoxLayout()
        
        prompt_label = QLabel("Avg Prompt Tokens:")
        prompt_label.setStyleSheet(f"color: {self.theme.text};")
        self.prompt_tokens_spin = QSpinBox()
        self.prompt_tokens_spin.setRange(1, 100000)
        self.prompt_tokens_spin.setValue(500)
        self.prompt_tokens_spin.setStyleSheet(self._get_spin_style())
        
        completion_label = QLabel("Avg Completion Tokens:")
        completion_label.setStyleSheet(f"color: {self.theme.text};")
        self.completion_tokens_spin = QSpinBox()
        self.completion_tokens_spin.setRange(1, 100000)
        self.completion_tokens_spin.setValue(500)
        self.completion_tokens_spin.setStyleSheet(self._get_spin_style())
        
        tokens_layout.addWidget(prompt_label)
        tokens_layout.addWidget(self.prompt_tokens_spin)
        tokens_layout.addWidget(completion_label)
        tokens_layout.addWidget(self.completion_tokens_spin)
        
        calc_layout.addLayout(tokens_layout)
        
        # Calculate button
        calc_btn = QPushButton("Calculate Cost Difference")
        calc_btn.clicked.connect(self._calculate_comparison)
        calc_btn.setStyleSheet(self._get_button_style())
        calc_layout.addWidget(calc_btn)
        
        # Results label
        self.calc_results_label = QLabel("Enter models and click Calculate")
        self.calc_results_label.setWordWrap(True)
        self.calc_results_label.setStyleSheet(f"color: {self.theme.text}; padding: 15px; background-color: {self.theme.card_background}; border-radius: 5px;")
        calc_layout.addWidget(self.calc_results_label)
        
        calc_group.setLayout(calc_layout)
        layout.addWidget(calc_group)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def update_analysis(self, billing_data: List[Dict], api_keys_data: List[Dict] = None, analysis_days: int = 7):
        """
        Update the cost optimization analysis.
        
        Args:
            billing_data: List of billing entries from /billing/usage API
            api_keys_data: List of API key data from /api_keys endpoint (optional)
            analysis_days: Number of days analyzed
        """
        # Stop and clean up any existing worker before creating a new one
        self._cleanup_worker()
        
        # Run analysis in background thread - pass self as parent to prevent GC
        self.worker = CostOptimizerWorker(billing_data, api_keys_data, analysis_days, parent=self)
        self.worker.analysis_complete.connect(self._handle_analysis_complete)
        self.worker.error_occurred.connect(self._handle_analysis_error)
        # Clear reference before deleteLater runs to avoid accessing deleted C++ object
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()
    
    def _handle_analysis_complete(self, report: CostOptimizationReport):
        """Handle completed cost analysis"""
        self.current_report = report
        self._update_breakdown_tab(report)
        self._update_recommendations_tab(report)
        self._populate_model_combos()
    
    def _handle_analysis_error(self, error_msg: str):
        """Handle analysis error"""
        logger.error(f"Cost analysis error: {error_msg}")
        # Update UI to show error state
        self.monthly_savings_label.setText(f"Analysis Error: {error_msg}")
    
    def _update_breakdown_tab(self, report: CostOptimizationReport):
        """Update the breakdown tab with report data"""
        # Update summary
        self.total_diem_label.setText(f"Total DIEM: {format_currency(report.total_cost_diem, 'DIEM')}")
        self.total_usd_label.setText(f"Total USD: {format_currency(report.total_cost_usd, 'USD')}")
        self.period_label.setText(f"Period: Last {report.analysis_period_days} days")
        
        # Update table
        self.breakdown_table.setRowCount(len(report.model_breakdown))
        
        for row, stats in enumerate(report.model_breakdown):
            # Model name
            self.breakdown_table.setItem(row, 0, QTableWidgetItem(stats.display_name))
            
            # Request count
            self.breakdown_table.setItem(row, 1, QTableWidgetItem(str(stats.request_count)))
            
            # Avg tokens
            self.breakdown_table.setItem(row, 2, QTableWidgetItem(f"{stats.avg_tokens_per_request:.0f}"))
            
            # Total cost
            total_cost = stats.total_cost_diem + stats.total_cost_usd
            cost_text = f"{format_currency(total_cost, 'DIEM')}"
            self.breakdown_table.setItem(row, 3, QTableWidgetItem(cost_text))
            
            # Percentage
            pct_item = QTableWidgetItem(f"{stats.percentage_of_total:.1f}%")
            self.breakdown_table.setItem(row, 4, pct_item)
            
            # Color code by percentage
            if stats.percentage_of_total > 30:
                color = QColor(self.theme.error if hasattr(self.theme, 'error') else "#ff6b6b")
            elif stats.percentage_of_total > 15:
                color = QColor(self.theme.warning if hasattr(self.theme, 'warning') else "#ffa500")
            else:
                color = QColor(self.theme.success if hasattr(self.theme, 'success') else "#51cf66")
            
            pct_item.setBackground(QBrush(color))
        
        self.breakdown_table.resizeColumnsToContents()
    
    def _update_recommendations_tab(self, report: CostOptimizationReport):
        """Update the recommendations tab with report data"""
        # Update savings summary
        self.monthly_savings_label.setText(
            f"Potential Monthly Savings: {format_currency(report.potential_monthly_savings, 'DIEM')}"
        )
        
        # Update table
        self.recommendations_table.setRowCount(len(report.recommendations))
        
        for row, rec in enumerate(report.recommendations):
            # Current model
            self.recommendations_table.setItem(row, 0, QTableWidgetItem(rec.current_model_name))
            
            # Recommended model
            rec_item = QTableWidgetItem(rec.recommended_model_name)
            rec_item.setFont(QFont("Arial", 10, QFont.Bold))
            self.recommendations_table.setItem(row, 1, rec_item)
            
            # API Keys Using
            if rec.api_keys_using and len(rec.api_keys_using) > 0:
                # Ensure it's a list
                if isinstance(rec.api_keys_using, str):
                    logger.error(f"BUG - api_keys_using is a string: {rec.api_keys_using!r}")
                    api_keys_text = rec.api_keys_using
                else:
                    # Join with newlines for better readability if multiple keys
                    if len(rec.api_keys_using) > 2:
                        api_keys_text = "\n".join(rec.api_keys_using)
                    else:
                        api_keys_text = ", ".join(rec.api_keys_using)
            else:
                api_keys_text = "Unknown\n(No API key data)"
            
            api_keys_item = QTableWidgetItem(api_keys_text)
            api_keys_item.setFont(QFont("Arial", 9))
            
            # Color code by confidence level
            if api_keys_text.startswith("Confirmed:"):
                api_keys_item.setForeground(QBrush(QColor("#51cf66")))  # Green - confirmed
            elif api_keys_text.startswith("Likely:"):
                api_keys_item.setForeground(QBrush(QColor(self.theme.accent)))  # Accent - likely
            else:
                api_keys_item.setForeground(QBrush(QColor("#ffa500")))  # Orange - possibly/unknown
            
            self.recommendations_table.setItem(row, 2, api_keys_item)
            
            # Request count
            self.recommendations_table.setItem(row, 3, QTableWidgetItem(str(rec.usage_count)))
            
            # Savings
            savings_text = f"{format_currency(rec.savings_amount, 'DIEM')} ({rec.savings_percent:.1f}%)"
            savings_item = QTableWidgetItem(savings_text)
            savings_item.setForeground(QBrush(QColor(self.theme.accent)))
            self.recommendations_table.setItem(row, 4, savings_item)
            
            # Confidence
            confidence_item = QTableWidgetItem(rec.confidence.upper())
            if rec.confidence == "high":
                confidence_item.setForeground(QBrush(QColor("#51cf66")))
            elif rec.confidence == "medium":
                confidence_item.setForeground(QBrush(QColor("#ffa500")))
            else:
                confidence_item.setForeground(QBrush(QColor("#ff6b6b")))
            self.recommendations_table.setItem(row, 5, confidence_item)
            
            # Reason
            self.recommendations_table.setItem(row, 6, QTableWidgetItem(rec.reason))
        
        self.recommendations_table.resizeColumnsToContents()
        
        # Ensure API Keys column is wide enough
        self.recommendations_table.setColumnWidth(2, max(180, self.recommendations_table.columnWidth(2)))
    
    def _populate_model_combos(self):
        """Populate model combo boxes in calculator"""
        from src.data.model_pricing import ModelPricingDatabase
        
        # Include beta models since they're commonly used
        chat_models = ModelPricingDatabase.get_chat_models(include_beta=True)
        
        self.model1_combo.clear()
        self.model2_combo.clear()
        
        # Sort by display name for easier selection
        sorted_models = sorted(chat_models.items(), key=lambda x: x[1].display_name)
        
        for model_id, pricing in sorted_models:
            beta_marker = " (β)" if pricing.is_beta else ""
            display_text = f"{pricing.display_name}{beta_marker} (${pricing.input_price:.2f}/${pricing.output_price:.2f})"
            self.model1_combo.addItem(display_text, model_id)
            self.model2_combo.addItem(display_text, model_id)
        
        # Set defaults
        if self.model1_combo.count() > 0:
            self.model1_combo.setCurrentIndex(0)
        if self.model2_combo.count() > 1:
            self.model2_combo.setCurrentIndex(1)
    
    def _calculate_comparison(self):
        """Calculate and display model cost comparison"""
        from src.analytics.cost_optimizer import CostOptimizer
        
        model1_id = self.model1_combo.currentData()
        model2_id = self.model2_combo.currentData()
        prompt_tokens = self.prompt_tokens_spin.value()
        completion_tokens = self.completion_tokens_spin.value()
        
        if not model1_id or not model2_id:
            self.calc_results_label.setText("Please select both models")
            return
        
        optimizer = CostOptimizer()
        comparison = optimizer.get_model_comparison(
            model1_id, model2_id, prompt_tokens, completion_tokens
        )
        
        if not comparison:
            self.calc_results_label.setText("Unable to compare selected models")
            return
        
        # Format results
        model1 = comparison['model1']
        model2 = comparison['model2']
        comp = comparison['comparison']
        
        results_text = f"""
<b>{model1['name']}</b>: ${model1['cost']:.6f} per request<br>
<b>{model2['name']}</b>: ${model2['cost']:.6f} per request<br>
<br>
<b style="color: {self.theme.accent};">Cheaper Option:</b> {comparison['comparison']['cheaper_model']}<br>
<b>Cost Difference:</b> ${comp['savings_usd']:.6f} per request ({comp['savings_percent']:.1f}%)<br>
<b>Annual Savings (1K req/day):</b> ${comp['cost_per_1k_requests_diff'] * 365:.2f}
        """
        
        self.calc_results_label.setText(results_text)
    
    def _get_tab_style(self) -> str:
        """Get tab widget stylesheet"""
        return f"""
            QTabWidget::pane {{
                border: 1px solid {self.theme.border};
                background-color: {self.theme.background};
            }}
            QTabBar::tab {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid {self.theme.border};
                border-bottom: none;
            }}
            QTabBar::tab:selected {{
                background-color: {self.theme.accent};
                color: {self.theme.text};
            }}
        """
    
    def _get_groupbox_style(self) -> str:
        """Get group box stylesheet"""
        return f"""
            QGroupBox {{
                font-weight: bold;
                color: {self.theme.text};
                border: 2px solid {self.theme.border};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }}
        """
    
    def _get_table_style(self) -> str:
        """Get table stylesheet"""
        return f"""
            QTableWidget {{
                background-color: {self.theme.background};
                color: {self.theme.text};
                gridline-color: {self.theme.border};
                border: 1px solid {self.theme.border};
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
            QHeaderView::section {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                padding: 5px;
                border: 1px solid {self.theme.border};
                font-weight: bold;
            }}
        """
    
    def _get_button_style(self) -> str:
        """Get button stylesheet"""
        return f"""
            QPushButton {{
                background-color: {self.theme.accent};
                color: {self.theme.text};
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent};
                opacity: 0.8;
            }}
        """
    
    def _get_combo_style(self) -> str:
        """Get combobox stylesheet"""
        return f"""
            QComboBox {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                border: 1px solid {self.theme.border};
                padding: 5px;
                border-radius: 3px;
            }}
        """
    
    def _get_spin_style(self) -> str:
        """Get spinbox stylesheet"""
        return f"""
            QSpinBox {{
                background-color: {self.theme.card_background};
                color: {self.theme.text};
                border: 1px solid {self.theme.border};
                padding: 5px;
                border-radius: 3px;
            }}
        """
