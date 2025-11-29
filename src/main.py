import sys
import json
import threading
import traceback
import time
import queue
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
import requests
import warnings
import urllib3

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                 QLabel, QPushButton, QComboBox, QFrame, QScrollArea,
                                 QScrollBar, QGridLayout, QSpacerItem, QSizePolicy,
                                 QErrorMessage, QMessageBox, QStatusBar, QTabWidget,
                                 QGroupBox, QTextEdit, QLineEdit, QSplitter)
from PySide6.QtCore import Qt, Signal, QObject, QThread, QTimer, QSize
from PySide6.QtGui import QFont, QPalette, QColor, QCloseEvent, QDoubleValidator

# Add the project directory to Python path (make it dynamic)
import os
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import local modules using relative imports (now a standalone repo)
from src.utils.utils import format_currency, validate_holding_amount, ValidationState
from src.utils.error_handler import ErrorHandler
from src.utils.model_utils import ModelNameParser
from src.config.config import Config
from src.config.theme import Theme
from src.config.features import FeatureFlags
from src.widgets.price_display import PriceDisplayWidget
from src.cli.model_viewer import ModelViewerWidget
from src.analytics.model_comparison import ModelComparisonWidget
from src.core.usage_tracker import UsageWorker, BalanceInfo, APIKeyUsage
from src.core.worker_factory import APIWorkerFactory, WorkerPool
from src.widgets.vvv_display import BalanceDisplayWidget, APIKeyUsageWidget
from src.widgets.enhanced_balance_widget import HeroBalanceWidget
from src.widgets.action_buttons import ActionButtonWidget
from src.utils.date_utils import DateFormatter
from src.widgets.usage_leaderboard import UsageLeaderboardWidget
from src.core.web_usage import WebUsageWorker, WebUsageMetrics
from src.core.unified_usage import UnifiedUsageEntry, UnifiedUsageIntegrator
from src.widgets.cost_optimization_widget import CostOptimizationWidget

# --- Suppress Warnings (Use with caution) ---
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)


# --- Logging Configuration ---
def setup_logging():
    """
    Configure application-wide logging with proper levels and handlers.
    Replaces scattered print() statements with proper logging.
    """
    # Determine log level from config
    log_level = logging.DEBUG if getattr(Config, 'DEBUG_MODE', False) else logging.INFO
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter(
        '[%(levelname)s] %(message)s'
    )
    
    # File handler for all logs
    file_handler = logging.FileHandler('app.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # File handler for errors only
    error_handler = logging.FileHandler('error_log.txt', encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    
    # Console handler for INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    
    # Quiet down noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    return root_logger


# Initialize logging
logger = setup_logging()
logger.info("=" * 60)
logger.info("Venice Token Watch Application Starting")
logger.info("=" * 60)

# Check feature availability
PHASE2_AVAILABLE = FeatureFlags.is_phase2_available()
PHASE3_AVAILABLE = FeatureFlags.is_phase3_available()
FeatureFlags.log_feature_status()


class CombinedViewerApp(QMainWindow):
    """
    Main application window combining Venice AI model viewing and CoinGecko price tracking.

    This application provides a comprehensive interface for:
    - Viewing and filtering Venice AI models by type (text, image, TTS)
    - Real-time cryptocurrency price tracking with CoinGecko API
    - API usage monitoring and balance tracking
    - Dark/light theme support

    Features:
    - Multi-threaded API calls to prevent UI blocking
    - Automatic price updates with configurable intervals
    - Model filtering and detailed specification display
    - Usage tracking with visual indicators
    - Theme switching with persistent styling
    - Comprehensive error handling and logging

    Attributes:
        theme (Theme): Current theme configuration
        models_data (dict): Cached Venice AI models data
        price_data (dict): Current price information for all currencies
        holding_amount (float): User-configured token holding amount
        validation_state (ValidationState): Current input validation state
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        logger.debug("Initializing CombinedViewerApp...")
        
        # Initialize theme system
        self.theme = Theme()
        
        # Validate configuration before starting
        is_valid, error_msg = Config.validate()
        if not is_valid:
            QMessageBox.critical(self, "Configuration Error", error_msg)
            sys.exit(1)
            
        self.setWindowTitle("Venice AI Models & CoinGecko Price Viewer")
        self.setMinimumSize(1200, 850)  # Increased minimum size for better chart display
        
        # Set a good default size for 1470x956 display
        self.resize(1280, 920)
        
        self.models_data = None
        self.model_types = ["all"]
        self.price_data = {
            'usd': {'price': None, 'total': None},
            'aud': {'price': None, 'total': None}
        }
        self.holding_amount = Config.COINGECKO_HOLDING_AMOUNT
        self.validation_state = ValidationState.VALID
        
        # Initialize API usage tracking components
        self.usage_worker = None
        self.web_usage_worker = None
        self.web_usage_metrics = None
        self.balance_display = None
        self.api_key_widgets = []
        self.current_usage_data = []
        self.current_balance_data = None
        self.current_daily_usage = {}  # Store daily usage totals
        
        # Phase 2: Initialize analytics and services
        if PHASE2_AVAILABLE:
            try:
                UsageAnalytics = FeatureFlags.get_feature_module('UsageAnalytics')
                ExchangeRateService = FeatureFlags.get_feature_module('ExchangeRateService')
                
                self.usage_analytics = UsageAnalytics()
                self.exchange_rate_service = ExchangeRateService(cache_ttl_minutes=5)
                logger.info("Phase 2 components initialized successfully")
            except Exception as e:
                ErrorHandler.log_warning(f"Phase 2 initialization failed: {e}")
                self.usage_analytics = None
                self.exchange_rate_service = None
        else:
            logger.debug("Phase 2 components not available, skipping initialization")
            self.usage_analytics = None
            self.exchange_rate_service = None
        
        # Phase 3: Initialize key management and security monitoring
        if PHASE3_AVAILABLE:
            try:
                usage_report_generator = FeatureFlags.get_feature_module('UsageReportGenerator')
                self.usage_report_generator = usage_report_generator
                self.key_management_enabled = True
                logger.info("Phase 3 components initialized successfully")
            except Exception as e:
                ErrorHandler.log_warning(f"Phase 3 initialization failed: {e}")
                self.usage_report_generator = None
                self.key_management_enabled = False
        else:
            logger.debug("Phase 3 components not available, skipping initialization")
            self.usage_report_generator = None
            self.key_management_enabled = False
        
        # Initialize UI
        self.init_ui()
    
    def get_combobox_style(self):
        """Get the modern combobox stylesheet"""
        bg_color = self.theme.background
        text_color = self.theme.text
        accent_color = self.theme.accent
        card_bg = self.theme.card_background
        
        return f"""
            QComboBox {{
                background-color: {card_bg};
                color: {text_color};
                border: 1px solid {accent_color};
                border-radius: 4px;
                padding: 5px;
                min-width: 100px;
            }}
            QComboBox:hover {{
                border: 2px solid {accent_color};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {text_color};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {card_bg};
                color: {text_color};
                selection-background-color: {accent_color};
                selection-color: {text_color};
                border: 1px solid {accent_color};
            }}
        """
    
    def get_button_style(self):
        """Get the modern button stylesheet"""
        bg_color = self.theme.background
        text_color = self.theme.text
        accent_color = self.theme.accent
        card_bg = self.theme.card_background
        border_color = self.theme.border
        
        return f"""
            QPushButton {{
                background-color: {card_bg};
                color: {text_color};
                border: 1px solid {accent_color};
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {accent_color};
                color: {text_color};
            }}
            QPushButton:pressed {{
                background-color: {accent_color};
                border: 2px solid {accent_color};
            }}
            QPushButton:disabled {{
                background-color: {border_color};
                color: {self.theme.text_secondary};
                border: 1px solid {border_color};
            }}
        """
    
    def get_radiobutton_style(self):
        """Get the modern radio button stylesheet"""
        text_color = self.theme.text
        accent_color = self.theme.accent
        
        return f"""
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
    
    def init_ui(self):
        """Initialize the main UI after helper methods are defined"""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Click 'Connect' for models. Price updates automatically.")
        
        # Create tab widget for different sections
        self.main_tabs = QTabWidget()
        main_layout.addWidget(self.main_tabs)
        
        # Create usage tracking container  
        self.usage_container = QWidget()
        self.usage_container.setStyleSheet(f"background-color: {self.theme.background};")
        usage_layout = QVBoxLayout(self.usage_container)
        usage_layout.setSpacing(10)
        usage_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create overall balance display (Hero Card)
        try:
            self.hero_balance_display = HeroBalanceWidget(self.theme.theme_colors)
            # Connect Phase 2 signals
            self.hero_balance_display.refresh_requested.connect(self.refresh_balance_action)
            usage_layout.addWidget(self.hero_balance_display)
            
            # Force text styling after widget is added to main app (to override any parent styling)
            QTimer.singleShot(100, self.hero_balance_display.force_text_styling)
            
        except Exception as e:
            logger.error(f"Failed to create hero balance widget: {e}")
            # Fallback to original balance display
            self.balance_display = BalanceDisplayWidget(self.theme.theme_colors)
            usage_layout.addWidget(self.balance_display)
        
        # Keep the old balance display for backward compatibility during transition
        if not hasattr(self, 'balance_display'):
            self.balance_display = BalanceDisplayWidget(self.theme.theme_colors)
        # Don't add it to layout - we'll phase it out
        
        # Create scroll area for API key usage
        self.usage_scroll_area = QScrollArea()
        self.usage_scroll_area.setWidgetResizable(True)
        self.usage_scroll_area.setStyleSheet(f"background-color: {self.theme.background};")
        
        self.usage_frame = QFrame()
        self.usage_frame.setStyleSheet(f"background-color: {self.theme.background};")
        self.usage_frame_layout = QVBoxLayout(self.usage_frame)
        self.usage_frame_layout.setSpacing(8)
        self.usage_frame_layout.setContentsMargins(8, 8, 8, 8)
        
        self.usage_scroll_area.setWidget(self.usage_frame)
        usage_layout.addWidget(self.usage_scroll_area)
        
        # Create first tab: API Balance & Tokens
        self.balance_tab = QWidget()
        balance_tab_layout = QVBoxLayout(self.balance_tab)
        balance_tab_layout.setContentsMargins(5, 5, 5, 5)
        balance_tab_layout.setSpacing(10)

        # Add usage tracking to balance tab
        balance_tab_layout.addWidget(self.usage_container)
        
        # Create enhanced action buttons for global data refresh
        try:
            self.action_buttons = ActionButtonWidget(self.theme.theme_colors)
            
            # Connect action button signals
            self.action_buttons.connect_models_requested.connect(self.connect_thread)
            self.action_buttons.refresh_balance_requested.connect(self.refresh_balance_action)
            self.action_buttons.load_usage_requested.connect(self.load_usage_action)
            self.action_buttons.refresh_all_requested.connect(self.refresh_all_action)
            
            balance_tab_layout.addWidget(self.action_buttons)
            
        except Exception as e:
            logger.error(f"Failed to create action buttons: {e}")
        
        # Create price display components
        self.price_display_usd = PriceDisplayWidget(self.theme)
        self.price_display_aud = PriceDisplayWidget(self.theme)

        # Create price container
        self.price_container = QWidget()
        self.price_container.setStyleSheet(f"background-color: {self.theme.background};")
        price_layout = QVBoxLayout(self.price_container)
        price_layout.setSpacing(10)
        price_layout.setContentsMargins(10, 10, 10, 10)

        # Token name
        token_name_text = Config.COINGECKO_TOKEN_ID.replace('-', ' ').capitalize()
        self.token_name_label = QLabel(token_name_text)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.token_name_label.setFont(font)
        self.token_name_label.setStyleSheet(f"color: {self.theme.text};")
        self.token_name_label.setAlignment(Qt.AlignCenter)
        price_layout.addWidget(self.token_name_label)

        # Holding amount
        self.holding_frame = QFrame()
        self.holding_frame.setStyleSheet(f"background-color: {self.theme.background};")
        holding_layout = QHBoxLayout(self.holding_frame)
        holding_layout.setContentsMargins(0, 0, 0, 0)

        holding_label = QLabel("Holding Amount:")
        holding_label.setStyleSheet(f"color: {self.theme.text};")
        holding_layout.addWidget(holding_label)

        self.holding_entry = QLineEdit(str(Config.COINGECKO_HOLDING_AMOUNT))
        self.holding_entry.setFixedWidth(80)
        self.holding_entry.textChanged.connect(self._on_holding_text_changed)
        self.holding_entry.editingFinished.connect(self.update_holding_amount)
        self.holding_entry.setValidator(QDoubleValidator(0.0, 1000000.0, 2))
        holding_layout.addWidget(self.holding_entry)

        token_label = QLabel("tokens")
        token_label.setStyleSheet(f"color: {self.theme.text};")
        holding_layout.addWidget(token_label)

        price_layout.addWidget(self.holding_frame, alignment=Qt.AlignCenter)

        # Price displays
        self.prices_frame = QFrame()
        self.prices_frame.setStyleSheet(f"background-color: {self.theme.background};")
        prices_layout = QHBoxLayout(self.prices_frame)
        prices_layout.setSpacing(10)

        # USD Display
        self.usd_group = QGroupBox(" USD ")
        self.usd_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {self.theme.background};
                border: 1px solid {self.theme.accent};
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
                color: {self.theme.text};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                background-color: {self.theme.background};
            }}
        """)
        usd_layout = QVBoxLayout(self.usd_group)
        usd_layout.addWidget(self.price_display_usd)
        prices_layout.addWidget(self.usd_group)

        # AUD Display
        self.aud_group = QGroupBox(" AUD ")
        self.aud_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {self.theme.background};
                border: 1px solid {self.theme.accent};
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
                color: {self.theme.text};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                background-color: {self.theme.background};
            }}
        """)
        aud_layout = QVBoxLayout(self.aud_group)
        aud_layout.addWidget(self.price_display_aud)
        prices_layout.addWidget(self.aud_group)

        price_layout.addWidget(self.prices_frame)

        # Price status
        self.price_status_label = QLabel("Initializing...")
        self.price_status_label.setStyleSheet(f"color: {self.theme.text};")
        self.price_status_label.setAlignment(Qt.AlignCenter)
        price_layout.addWidget(self.price_status_label)

        # Theme toggle
        self.theme_frame = QFrame()
        self.theme_frame.setStyleSheet(f"background-color: {self.theme.background};")
        theme_layout = QHBoxLayout(self.theme_frame)
        theme_layout.setContentsMargins(0, 0, 0, 0)

        theme_label = QLabel("Theme:")
        theme_label.setStyleSheet(f"color: {self.theme.text};")
        theme_layout.addWidget(theme_label)

        self.theme_toggle = QComboBox()
        self.theme_toggle.addItems(["Dark", "Light"])
        self.theme_toggle.setCurrentText("Dark" if self.theme.mode == 'dark' else "Light")
        self.theme_toggle.currentTextChanged.connect(self.toggle_theme)
        self.theme_toggle.setStyleSheet(self.get_combobox_style())
        theme_layout.addWidget(self.theme_toggle)

        price_layout.addWidget(self.theme_frame, alignment=Qt.AlignRight)

        # Add price container to balance tab
        balance_tab_layout.addWidget(self.price_container)

        # Add balance tab to main tabs
        self.main_tabs.addTab(self.balance_tab, "API Balance & Tokens")
        
        # Create second tab: Models
        self.models_tab = QWidget()
        models_tab_layout = QVBoxLayout(self.models_tab)
        models_tab_layout.setContentsMargins(5, 5, 5, 5)
        models_tab_layout.setSpacing(10)

        # Create control buttons
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)

        # Keep original connect button for fallback during transition
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_thread)
        self.connect_button.setStyleSheet(self.get_button_style())
        controls_layout.addWidget(self.connect_button)

        self.display_button = QPushButton("Display Models")
        self.display_button.clicked.connect(self.display_selected_models_action)
        self.display_button.setEnabled(False)
        self.display_button.setStyleSheet(self.get_button_style())
        controls_layout.addWidget(self.display_button)

        self.view_styles_button = QPushButton("View Style Presets")
        self.view_styles_button.clicked.connect(self.view_style_presets_action)
        self.view_styles_button.setEnabled(False)
        self.view_styles_button.setStyleSheet(self.get_button_style())
        controls_layout.addWidget(self.view_styles_button)

        # Create model type selector
        self.type_combobox = QComboBox()
        self.type_combobox.addItems(self.model_types)
        self.type_combobox.setEnabled(False)
        # Block signals during initial setup to prevent unwanted filter calls
        self.type_combobox.blockSignals(True)
        self.type_combobox.setCurrentText("all")
        self.type_combobox.blockSignals(False)
        self.type_combobox.currentTextChanged.connect(self.display_selected_models_action)
        self.type_combobox.setStyleSheet(self.get_combobox_style())
        controls_layout.addWidget(self.type_combobox)

        self.traits_combobox = QComboBox()
        self.traits_combobox.addItems(["all"])
        self.traits_combobox.setEnabled(False)
        # Block signals during initial setup to prevent unwanted filter calls
        self.traits_combobox.blockSignals(True)
        self.traits_combobox.setCurrentText("all")
        self.traits_combobox.blockSignals(False)
        self.traits_combobox.currentTextChanged.connect(self.display_selected_models_action)
        self.traits_combobox.setStyleSheet(self.get_combobox_style())

        # Add debugging to verify combobox signals are connected
        logger.debug("Setting up combobox signal connections...")
        logger.debug(f"Type combobox has {self.type_combobox.count()} items")
        logger.debug(f"Traits combobox has {self.traits_combobox.count()} items")
        controls_layout.addWidget(self.traits_combobox)

        models_tab_layout.addLayout(controls_layout)

        # Create scroll area for model display
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"background-color: {self.theme.background};")

        self.display_frame = QFrame()
        self.display_frame.setStyleSheet(f"background-color: {self.theme.background};")
        self.display_layout = QVBoxLayout(self.display_frame)
        self.display_layout.setSpacing(10)
        self.display_layout.setContentsMargins(10, 10, 10, 10)

        self.scroll_area.setWidget(self.display_frame)
        models_tab_layout.addWidget(self.scroll_area)

        # Add models tab to main tabs
        self.main_tabs.addTab(self.models_tab, "Models")

        # Create third tab: Cost Optimization & Analytics
        self._create_cost_optimization_tab()
        
        # Create fourth tab: Compare & Analyze (Phase 2)
        if PHASE2_AVAILABLE:
            self.create_comparison_tab()
        
        # Create fifth tab: Usage Leaderboard (Phase 2)
        if PHASE2_AVAILABLE:
            self.create_leaderboard_tab()

        # Initialize holding entry with proper value format
        self.holding_entry.setText(str(int(Config.COINGECKO_HOLDING_AMOUNT)) if Config.COINGECKO_HOLDING_AMOUNT.is_integer() else f"{Config.COINGECKO_HOLDING_AMOUNT:.2f}")
        
        # Initialize usage tracking
        self._init_usage_tracking()
        
        # Phase 2: Initialize analytics and exchange rate services
        self._init_phase2_services()
        
        # Start periodic updates
        QTimer.singleShot(Config.COINGECKO_INITIAL_DELAY_MS, self.update_price_label)
        QTimer.singleShot(1000, self._start_usage_updates)  # Start usage updates after a short delay
        
        # Initial actions
        QTimer.singleShot(Config.COINGECKO_INITIAL_DELAY_MS, self.update_price_label)
        
        logger.debug("CombinedViewerApp initialization complete.")
    
    def _on_holding_text_changed(self, text: str) -> None:
        """
        Handle text changes in the holding amount entry field.

        Updates the validation state and visual indicators based on the current input.
        This provides real-time feedback to the user about input validity.

        Args:
            text: The current text in the holding amount input field
        """
        try:
            state = validate_holding_amount(text)
            self.validation_state = state

            # Update validation state for both displays
            self.price_display_usd.set_validation_state(state.value)
            self.price_display_aud.set_validation_state(state.value)
        except Exception as e:
            logging.error(f"Error validating holding amount input: {e}")
            # Set to invalid state on error
            self.validation_state = ValidationState.INVALID
            self.price_display_usd.set_validation_state(ValidationState.INVALID.value)
            self.price_display_aud.set_validation_state(ValidationState.INVALID.value)
    
    def update_holding_amount(self):
        """Validates and processes user input for holding amount."""
        try:
            new_amount = float(self.holding_entry.text())
            if new_amount <= 0:
                raise ValueError("Amount must be positive")
            self.holding_amount = new_amount
            for currency in Config.COINGECKO_CURRENCIES:
                if self.price_data[currency]['price'] is not None:
                    self.price_data[currency]['total'] = self.price_data[currency]['price'] * self.holding_amount
            
            # Update price displays
            self._update_price_display()
            
            # Update status
            self.price_status_label.setText(f"Holding amount updated to {new_amount:.2f}. Price updates automatically.")
            self.price_status_label.setStyleSheet(f"color: {self.theme.text};")
            
            # Update theme for all components
            self._apply_theme()
        
        except ValueError:
            self.holding_entry.setText(str(int(self.holding_amount)) if self.holding_amount.is_integer() else f"{self.holding_amount:.2f}")
            self.price_status_label.setText("Invalid holding amount. Must be a positive number.")
            self.price_status_label.setStyleSheet(f"color: {self.theme.error};")
            # Ensure price display is updated with current valid holding amount
            self._update_price_display()
    
    def _update_price_display(self):
        """Update price display based on current price_data and holding_amount"""
        # Update USD display
        if self.price_data['usd']['price'] is not None:
            self.price_display_usd.set_price(self.price_data['usd']['price'])
            self.price_display_usd.set_holding_value(self.price_data['usd']['total'])
        else:
            self.price_display_usd.set_price(0)
            self.price_display_usd.set_holding_value(0)
        
        # Update AUD display
        if self.price_data['aud']['price'] is not None:
            self.price_display_aud.set_price(self.price_data['aud']['price'])
            self.price_display_aud.set_holding_value(self.price_data['aud']['total'])
        else:
            self.price_display_aud.set_price(0)
            self.price_display_aud.set_holding_value(0)
    
    def _apply_theme(self):
        """Apply current theme to all UI elements"""
        # Get theme colors
        bg_color = self.theme.background
        text_color = self.theme.text
        accent_color = self.theme.accent
        card_bg = self.theme.card_background
        border_color = self.theme.border
        
        # Update price container
        self.price_container.setStyleSheet(f"background-color: {bg_color};")
        
        # Update usage container
        if hasattr(self, 'usage_container'):
            self.usage_container.setStyleSheet(f"background-color: {bg_color};")
        
        # Update token name label
        self.token_name_label.setStyleSheet(f"color: {text_color};")
        
        # Update holding frame
        self.holding_frame.setStyleSheet(f"background-color: {bg_color};")
        for child in self.holding_frame.findChildren(QLabel):
            child.setStyleSheet(f"color: {text_color};")
        
        # Update price frames
        self.prices_frame.setStyleSheet(f"background-color: {bg_color};")
        for group in [self.usd_group, self.aud_group]:
            group.setStyleSheet(f"""
                QGroupBox {{
                    background-color: {bg_color};
                    border: 1px solid {accent_color};
                    border-radius: 5px;
                    margin-top: 10px;
                    padding: 10px;
                    color: {text_color};
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    padding: 0 5px;
                    background-color: {bg_color};
                }}
            """)
        
        # Update status label
        self.price_status_label.setStyleSheet(f"color: {text_color};")
        
        # Update theme toggle
        self.theme_frame.setStyleSheet(f"background-color: {bg_color};")
        for child in self.theme_frame.findChildren(QLabel):
            child.setStyleSheet(f"color: {text_color};")
        
        # Apply modern styling to comboboxes
        combobox_style = f"""
            QComboBox {{
                background-color: {card_bg};
                color: {text_color};
                border: 1px solid {accent_color};
                border-radius: 4px;
                padding: 5px;
                min-width: 100px;
            }}
            QComboBox:hover {{
                border: 2px solid {accent_color};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {text_color};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {card_bg};
                color: {text_color};
                selection-background-color: {accent_color};
                selection-color: {text_color};
                border: 1px solid {accent_color};
            }}
        """
        
        if hasattr(self, 'theme_toggle'):
            self.theme_toggle.setStyleSheet(combobox_style)
        if hasattr(self, 'type_combobox'):
            self.type_combobox.setStyleSheet(combobox_style)
        if hasattr(self, 'traits_combobox'):
            self.traits_combobox.setStyleSheet(combobox_style)
        
        # Apply modern styling to buttons
        button_style = f"""
            QPushButton {{
                background-color: {card_bg};
                color: {text_color};
                border: 1px solid {accent_color};
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {accent_color};
                color: {text_color};
            }}
            QPushButton:pressed {{
                background-color: {accent_color};
                border: 2px solid {accent_color};
            }}
            QPushButton:disabled {{
                background-color: {border_color};
                color: {self.theme.text_secondary};
                border: 1px solid {border_color};
            }}
        """
        
        if hasattr(self, 'connect_button'):
            self.connect_button.setStyleSheet(button_style)
        if hasattr(self, 'display_button'):
            self.display_button.setStyleSheet(button_style)
        if hasattr(self, 'view_styles_button'):
            self.view_styles_button.setStyleSheet(button_style)
        
        # Apply styling to scroll areas
        scroll_style = f"""
            QScrollArea {{
                background-color: {bg_color};
                border: none;
            }}
            QScrollBar:vertical {{
                background: {card_bg};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {accent_color};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {accent_color};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: {card_bg};
                height: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal {{
                background: {accent_color};
                border-radius: 6px;
                min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {accent_color};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """
        
        if hasattr(self, 'scroll_area'):
            self.scroll_area.setStyleSheet(scroll_style)
        if hasattr(self, 'usage_scroll_area'):
            self.usage_scroll_area.setStyleSheet(scroll_style)
    
    def toggle_theme(self, theme_name):
        """Toggle between dark and light themes"""
        self.theme = Theme('dark' if theme_name == "Dark" else 'light')
        self._apply_theme()
        self.price_display_usd.theme = self.theme
        self.price_display_aud.theme = self.theme
        
        # Update model comparison widget theme if it exists
        if hasattr(self, 'model_comparison_widget') and self.model_comparison_widget:
            self.model_comparison_widget.theme = self.theme
        
        # Update enhanced components theme
        if hasattr(self, 'hero_balance_display') and self.hero_balance_display:
            self.hero_balance_display.set_theme_colors(self.theme.theme_colors)
        
        if hasattr(self, 'action_buttons') and self.action_buttons:
            self.action_buttons.set_theme_colors(self.theme.theme_colors)
        
        # Phase 3: Update key management widget themes
        if PHASE3_AVAILABLE and hasattr(self, 'api_key_widgets'):
            for widget in self.api_key_widgets:
                if hasattr(widget, 'set_theme_colors'):
                    widget.set_theme_colors(self.theme.theme_colors)
        
        # Update leaderboard theme
        if hasattr(self, 'leaderboard_widget') and self.leaderboard_widget:
            self.leaderboard_widget.theme_colors = self.theme.theme_colors
            self.leaderboard_widget.apply_theme()

        # Update validation state display
        self.price_display_usd.set_validation_state(self.validation_state.value)
        self.price_display_aud.set_validation_state(self.validation_state.value)
    
    def _create_cost_optimization_tab(self):
        """Create the Cost Optimization & Analytics tab"""
        self.cost_optimization_tab = QWidget()
        cost_tab_layout = QVBoxLayout(self.cost_optimization_tab)
        cost_tab_layout.setContentsMargins(5, 5, 5, 5)
        cost_tab_layout.setSpacing(10)
        
        # Create cost optimization widget
        self.cost_optimizer_widget = CostOptimizationWidget(self.theme, self)
        self.cost_optimizer_widget.refresh_requested.connect(self._refresh_cost_analysis)
        cost_tab_layout.addWidget(self.cost_optimizer_widget)
        
        # Add tab to main tabs
        self.main_tabs.addTab(self.cost_optimization_tab, "💰 Cost Optimization")
        
        logger.debug("Cost optimization tab created successfully")
    
    def _refresh_cost_analysis(self):
        """Refresh cost optimization analysis with latest billing data"""
        try:
            # Fetch billing data (last 7 days with intelligent caching)
            from src.core.venice_api_client import VeniceAPIClient
            from datetime import datetime, timedelta, timezone
            import requests
            import json
            from pathlib import Path
            
            client = VeniceAPIClient(Config.VENICE_ADMIN_KEY)
            
            # Calculate date range (last 7 complete days)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=7)
            
            # Setup cache file
            cache_file = Path("data/billing_cache.json")
            cache_file.parent.mkdir(exist_ok=True)
            
            # Load cached data if exists
            cached_data = []
            last_fetch_time = None
            
            if cache_file.exists():
                try:
                    with open(cache_file, 'r') as f:
                        cache = json.load(f)
                        cached_data = cache.get('records', [])
                        last_fetch_str = cache.get('last_fetch')
                        if last_fetch_str:
                            last_fetch_time = datetime.fromisoformat(last_fetch_str.replace('Z', '+00:00'))
                    logger.debug(f"Loaded {len(cached_data)} cached billing records")
                except Exception as e:
                    logger.warning(f"Failed to load billing cache: {e}")
            
            # Determine fetch strategy
            if last_fetch_time and (end_date - last_fetch_time).total_seconds() < 300:
                # Last fetch was less than 5 minutes ago - skip refresh
                logger.info(f"Using cached billing data ({len(cached_data)} records, last fetched {int((end_date - last_fetch_time).total_seconds())}s ago)")
                if cached_data:
                    # Still need to fetch API key usage data
                    try:
                        api_keys_response = client.get("/api_keys")
                        api_keys_data = api_keys_response.json().get('data', [])
                        logger.debug(f"Fetched usage data for {len(api_keys_data)} API keys (with cached billing data)")
                    except Exception as e:
                        logger.warning(f"Failed to fetch API key data: {e}")
                        api_keys_data = []
                    
                    self.cost_optimizer_widget.update_analysis(cached_data, api_keys_data, analysis_days=7)
                return
            
            # Determine if we need full refresh or incremental update
            if last_fetch_time and (end_date - last_fetch_time).total_seconds() < 3600:
                # Last fetch was less than 1 hour ago - fetch only new records
                fetch_start = last_fetch_time - timedelta(minutes=5)  # Small overlap to avoid gaps
                logger.info(f"Incremental fetch: Getting records since {fetch_start.strftime('%Y-%m-%d %H:%M')}")
            else:
                # Full refresh needed
                fetch_start = start_date
                cached_data = []  # Clear cache for full refresh
                logger.info(f"Full refresh: Getting all records from last 7 days")
            
            # Fetch new/updated billing data
            new_records = []
            page = 1
            max_pages = 20
            
            while page <= max_pages:
                params = {
                    'startDate': fetch_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    'endDate': end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    'limit': 500,
                    'page': page,
                    'sortOrder': 'desc'
                }
                
                response = client.get("/billing/usage", params=params, timeout=60)
                data = response.json()
                
                billing_data = data.get('data', [])
                pagination = data.get('pagination', {})
                
                new_records.extend(billing_data)
                
                total_pages = pagination.get('totalPages', 1)
                logger.debug(f"Fetched page {page}/{total_pages}: {len(billing_data)} records")
                
                if page >= total_pages:
                    break
                    
                page += 1
            
            # Merge new records with cached data (remove duplicates by timestamp)
            if cached_data and new_records:
                # Create a set of existing record IDs (using timestamp as key)
                existing_ids = {r.get('timestamp', '') for r in cached_data}
                # Add only truly new records
                unique_new = [r for r in new_records if r.get('timestamp', '') not in existing_ids]
                all_records = cached_data + unique_new
                logger.info(f"✓ Merged data: {len(cached_data)} cached + {len(unique_new)} new = {len(all_records)} total records")
            else:
                all_records = new_records or cached_data
                logger.info(f"✓ Fetched {len(all_records)} total billing entries")
            
            # Filter to only last 7 days
            cutoff_time = start_date.isoformat()
            all_records = [r for r in all_records if r.get('timestamp', '') >= cutoff_time]
            
            # Save to cache
            try:
                cache = {
                    'last_fetch': end_date.isoformat(),
                    'records': all_records
                }
                with open(cache_file, 'w') as f:
                    json.dump(cache, f)
                logger.debug(f"Cached {len(all_records)} records to {cache_file}")
            except Exception as e:
                logger.warning(f"Failed to save billing cache: {e}")
            
            # Update the cost optimizer widget
            if all_records:
                # Also fetch API key usage data
                try:
                    api_keys_response = client.get("/api_keys")
                    api_keys_data = api_keys_response.json().get('data', [])
                    logger.debug(f"Fetched usage data for {len(api_keys_data)} API keys")
                except Exception as e:
                    logger.warning(f"Failed to fetch API key data: {e}")
                    api_keys_data = []
                
                # Pass both billing and API key data to the optimizer
                self.cost_optimizer_widget.update_analysis(all_records, api_keys_data, analysis_days=7)
            else:
                logger.warning("No billing data available for cost analysis")
                
        except requests.exceptions.HTTPError as e:
            # Detailed logging for HTTP errors
            if e.response is not None:
                logger.error(f"Failed to refresh cost analysis: HTTP {e.response.status_code}")
                logger.error(f"Request URL: {e.response.url}")
                if e.response.status_code == 400:
                    try:
                        error_body = e.response.json()
                        logger.error(f"API Error Details: {error_body}")
                    except:
                        logger.error(f"API Error Body: {e.response.text[:500]}")
            else:
                logger.error(f"Failed to refresh cost analysis: {e}")
        except Exception as e:
            logger.error(f"Failed to refresh cost analysis: {type(e).__name__}: {e}")
    
    def get_coingecko_price(self):
        """Fetch prices for all configured currencies from CoinGecko API."""
        url = f"https://api.coingecko.com/api/v3/simple/price"
        vs_currencies_str = ','.join(Config.COINGECKO_CURRENCIES)
        params = {
            'ids': Config.COINGECKO_TOKEN_ID,
            'vs_currencies': vs_currencies_str
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if Config.COINGECKO_TOKEN_ID in data:
                    price_data = {}
                    for currency in Config.COINGECKO_CURRENCIES:
                        if currency in data[Config.COINGECKO_TOKEN_ID]:
                            price_data[currency] = data[Config.COINGECKO_TOKEN_ID][currency]
                    return price_data
                return None
            except requests.exceptions.RequestException as e:
                error_msg = f"Error fetching data from CoinGecko API (attempt {attempt + 1}/{max_retries}): {e}"
                logger.error(error_msg)
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return None
    
    def update_price_label(self):
        """Updates price display for all configured currencies."""
        price_data = self.get_coingecko_price()
        
        if price_data:
            status_messages = []
            failed_currencies = []
            
            for currency in Config.COINGECKO_CURRENCIES:
                if currency in price_data:
                    self.price_data[currency]['price'] = price_data[currency]
                    self.price_data[currency]['total'] = price_data[currency] * self.holding_amount
                    
                    price_str = format_currency(price_data[currency], currency)
                    status_messages.append(f"{currency.upper()}: {price_str}")
                else:
                    failed_currencies.append(currency)
                    status_messages.append(f"{currency.upper()}: Error")
            
            if failed_currencies:
                if len(failed_currencies) == len(Config.COINGECKO_CURRENCIES):
                    status_str = "Price Update Error. Retrying..."
                    status_color = self.theme.error
                    QMessageBox.warning(self, "Price Update Failed", "Failed to retrieve price data from CoinGecko API. Retrying...")
                else:
                    failed_str = ", ".join([c.upper() for c in failed_currencies])
                    status_str = f"Partial update: {failed_str} failed | {', '.join(status_messages)} | Last updated: {time.strftime('%H:%M:%S')}"
                    status_color = self.theme.error
                    QMessageBox.warning(self, "Partial Price Update", f"Failed to retrieve {failed_str} prices. Other prices updated successfully.")
            else:
                status_str = f"Prices updated: {', '.join(status_messages)} | Last updated: {time.strftime('%H:%M:%S')}"
                status_color = self.theme.text
            
            self.price_status_label.setText(status_str)
            self.price_status_label.setStyleSheet(f"color: {status_color};")
        else:
            status_str = "Price Update Error. Retrying..."
            status_color = self.theme.error
            self.price_status_label.setText(status_str)
            self.price_status_label.setStyleSheet(f"color: {status_color};")
            QMessageBox.warning(self, "Price Update Failed", "Failed to connect to CoinGecko API. Retrying...")
        
        # Update price displays
        self._update_price_display()
        
        QTimer.singleShot(Config.COINGECKO_REFRESH_INTERVAL_MS, self.update_price_label)
    
    def connect_thread(self):
        """Starts the API connection in a separate thread."""
        # Disable legacy buttons
        self.connect_button.setEnabled(False)
        self.display_button.setEnabled(False)
        self.view_styles_button.setEnabled(False)
        self.type_combobox.setEnabled(False)
        
        # Set loading state for action buttons
        if hasattr(self, 'action_buttons'):
            self.action_buttons.set_button_loading('connect', True, "Connecting...")
        
        self.clear_display_frame()
        self.status_bar.showMessage("Connecting to Venice API...")
        
        # Ensure scroll area is reset
        self.scroll_area.verticalScrollBar().setValue(0)
        
        # Clear layout
        for i in reversed(range(self.display_layout.count())):
            self.display_layout.takeAt(i).widget().deleteLater()
        
        # Add connecting label
        connecting_label = QLabel("Connecting to Venice API...")
        connecting_label.setStyleSheet(f"color: {self.theme.text};")
        self.display_layout.addWidget(connecting_label, alignment=Qt.AlignCenter)
        
        # Create and start worker thread using factory
        self.api_worker = APIWorkerFactory.create_models_worker(model_type='all', parent=self)
        self.api_worker.result.connect(self._update_gui_after_connect)
        self.api_worker.start()
    
    def refresh_balance_action(self):
        """Handle refresh balance button action."""
        if hasattr(self, 'action_buttons'):
            self.action_buttons.set_button_loading('refresh_balance', True, "Refreshing...")
        
        try:
            # Trigger balance refresh by restarting the usage worker
            if hasattr(self, 'usage_worker') and self.usage_worker:
                # If worker is already running, let it finish first
                if not self.usage_worker.isRunning():
                    self.usage_worker.start()
                else:
                    logger.info("Usage worker already running, refresh will happen automatically")
                
            # Show success after a short delay
            QTimer.singleShot(2000, lambda: [
                self.action_buttons.set_button_loading('refresh_balance', False) if hasattr(self, 'action_buttons') else None,
                self.action_buttons.set_button_success('refresh_balance', "Balance Updated") if hasattr(self, 'action_buttons') else None
            ])
            
        except Exception as e:
            if hasattr(self, 'action_buttons'):
                self.action_buttons.set_button_loading('refresh_balance', False)
                self.action_buttons.set_button_error('refresh_balance', "Refresh Failed")
            logger.error(f"Error refreshing balance: {e}")
    
    def load_usage_action(self):
        """Handle load usage button action."""
        if hasattr(self, 'action_buttons'):
            self.action_buttons.set_button_loading('load_usage', True, "Loading...")
        
        try:
            # Trigger usage data refresh by restarting the usage worker
            if hasattr(self, 'usage_worker') and self.usage_worker:
                # If worker is already running, let it finish first
                if not self.usage_worker.isRunning():
                    self.usage_worker.start()
                else:
                    logger.info("Usage worker already running, refresh will happen automatically")
                
            # Show success after a short delay
            QTimer.singleShot(2500, lambda: [
                self.action_buttons.set_button_loading('load_usage', False) if hasattr(self, 'action_buttons') else None,
                self.action_buttons.set_button_success('load_usage', "Usage Loaded") if hasattr(self, 'action_buttons') else None
            ])
            
        except Exception as e:
            if hasattr(self, 'action_buttons'):
                self.action_buttons.set_button_loading('load_usage', False)
                self.action_buttons.set_button_error('load_usage', "Load Failed")
            logger.error(f"Error loading usage: {e}")
    
    def refresh_all_action(self):
        """Handle refresh all data button action."""
        if hasattr(self, 'action_buttons'):
            self.action_buttons.set_button_loading('refresh_all', True, "Refreshing all...")
        
        try:
            # Trigger multiple refreshes
            self.refresh_balance_action()
            self.load_usage_action()
            self.update_price_label()  # Refresh prices
            
            # Show success after all operations complete
            QTimer.singleShot(3000, lambda: [
                self.action_buttons.set_button_loading('refresh_all', False) if hasattr(self, 'action_buttons') else None,
                self.action_buttons.set_button_success('refresh_all', "All Data Updated") if hasattr(self, 'action_buttons') else None
            ])
            
        except Exception as e:
            if hasattr(self, 'action_buttons'):
                self.action_buttons.set_button_loading('refresh_all', False)
                self.action_buttons.set_button_error('refresh_all', "Refresh Failed")
            logger.error(f"Error refreshing all data: {e}")
    
    def view_style_presets_action(self):
        """Starts fetching style presets in a separate thread."""
        if self.models_data is None:
            QMessageBox.warning(self, "No Model Data", "Please connect to the Model API first.")
            return
            
        self.status_bar.showMessage("Fetching Style Presets...")
        self.clear_display_frame()
        
        # Ensure scroll area is reset
        self.scroll_area.verticalScrollBar().setValue(0)
        
        # Clear layout
        for i in reversed(range(self.display_layout.count())):
            self.display_layout.takeAt(i).widget().deleteLater()
        
        # Add fetching label
        fetching_label = QLabel("Fetching Style Presets...")
        fetching_label.setStyleSheet(f"color: {self.theme.text};")
        self.display_layout.addWidget(fetching_label, alignment=Qt.AlignCenter)
        
        # Create and start worker thread using factory
        self.style_worker = APIWorkerFactory.create_style_presets_worker(parent=self)
        self.style_worker.result.connect(self._update_gui_after_fetch_style_presets)
        self.style_worker.start()
    
    def _update_gui_after_connect(self, result):
        """Updates GUI elements after the model connection attempt."""
        self.connect_button.setEnabled(True)
        self.clear_display_frame()
        
        # Ensure scroll area is reset
        self.scroll_area.verticalScrollBar().setValue(0)
        
        # Clear layout
        for i in reversed(range(self.display_layout.count())):
            self.display_layout.takeAt(i).widget().deleteLater()
        
        if result['success']:
            self.models_data = result['data']
            types = set(model.get('type', 'Unknown') for model in self.models_data['data'])
            types = {str(t) if t is not None else 'Unknown' for t in types}
            self.model_types = ["all"] + sorted(list(types))

            self.type_combobox.clear()
            self.type_combobox.addItems(self.model_types)
            # Block signals to prevent unwanted filter triggers during setup
            self.type_combobox.blockSignals(True)
            self.type_combobox.setCurrentText("all")
            self.type_combobox.blockSignals(False)
            self.type_combobox.setEnabled(True)
            self.display_button.setEnabled(True)
            self.view_styles_button.setEnabled(True)

            # Update action buttons to success state
            if hasattr(self, 'action_buttons'):
                self.action_buttons.set_button_loading('connect', False)
                self.action_buttons.set_button_success('connect', "Connected")

            # Update the comparison widget with new model data
            self.update_model_comparison_data()

            self.status_bar.showMessage("Model API Connected. Select type and 'Display Models'.")

            # Start fetching traits
            self.fetch_traits()

            # Add instruction label
            instruction_label = QLabel("Select model type and click 'Display Models'.")
            instruction_label.setStyleSheet(f"color: {self.theme.text};")
            self.display_layout.addWidget(instruction_label, alignment=Qt.AlignCenter)
        else:
            self.models_data = None
            self.type_combobox.clear()
            self.type_combobox.addItem("all")
            self.type_combobox.setCurrentText("all")
            self.type_combobox.setEnabled(False)
            self.display_button.setEnabled(False)
            self.view_styles_button.setEnabled(False)
            self.status_bar.showMessage("Model connection failed. Check logs or API key.")
            
            # Update action buttons to error state
            if hasattr(self, 'action_buttons'):
                self.action_buttons.set_button_loading('connect', False)
                self.action_buttons.set_button_error('connect', "Connection Failed")
            
            # Add error label
            error_label = QLabel("Model Connection failed.")
            error_label.setStyleSheet(f"color: {self.theme.error};")
            self.display_layout.addWidget(error_label, alignment=Qt.AlignCenter)
            
            if result['error']:
                self._show_api_error("Venice API Connection Error", result['error'])
    
    def _update_gui_after_fetch_style_presets(self, result):
        """Updates the model display frame with style presets."""
        self.clear_display_frame()
        
        # Ensure scroll area is reset
        self.scroll_area.verticalScrollBar().setValue(0)
        
        if result['success']:
            style_presets = result['data']
            section_label = QLabel("Available Style Presets:")
            font = QFont()
            font.setItalic(True)
            font.setPointSize(10)
            section_label.setFont(font)
            section_label.setStyleSheet(f"color: {self.theme.text}; padding: 10px 0px 1px 0px;")
            self.display_layout.addWidget(section_label)
            
            text_widget = QTextEdit()
            text_widget.setReadOnly(True)
            text_widget.setStyleSheet(f"""
                background-color: {self.theme.background};
                color: {self.theme.text};
                border: none;
                padding: 5px;
            """)
            for preset in style_presets:
                text_widget.append(preset)
            self.display_layout.addWidget(text_widget, 1)
            
            self.status_bar.showMessage("Displayed available style presets.")
        else:
            error_label = QLabel("No style presets available or error occurred.")
            error_label.setStyleSheet(f"color: orange;")
            self.display_layout.addWidget(error_label, alignment=Qt.AlignCenter)
            if result['error']:
                self._show_api_error("Style Preset API Error", result['error'])
        
        # Ensure scroll area updates
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(0))
    
    def _show_api_error(self, title, error_message):
        QMessageBox.critical(self, title, error_message)
    
    def display_selected_models_action(self):
        if self.models_data is None:
            QMessageBox.warning(self, "No Model Data", "Please connect to the Model API first.")
            return

        logger.debug(f"Original models count before filtering: {len(self.models_data['data'])}")
        logger.debug(f"Selected type: {self.type_combobox.currentText()}")
        logger.debug(f"Selected trait: {self.traits_combobox.currentText()}")

        # Debug: Show model types present
        model_types_set = set()
        for model in self.models_data['data']:
            if isinstance(model, dict):
                model_type = model.get('type')
                if model_type:
                    model_types_set.add(str(model_type))

        logger.debug(f"Available model types in data: {sorted(list(model_types_set))}")

        self.display_filtered_models()
    
    def clear_display_frame(self):
        """Clear all widgets from the display frame."""
        for i in reversed(range(self.display_layout.count())):
            self.display_layout.takeAt(i).widget().deleteLater()
        self.scroll_area.verticalScrollBar().setValue(0)
    
    def _add_separator(self, layout):
        """Add a horizontal separator to the layout."""
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet(f"color: #555555;")
        layout.addWidget(separator)
    
    def _add_section_heading(self, layout, text, row=None):
        """Add a section heading to the layout."""
        heading = QLabel(text)
        font = QFont()
        font.setItalic(True)
        font.setPointSize(10)
        heading.setFont(font)
        heading.setStyleSheet(f"color: {self.theme.text}; padding: 5px 0px 1px 0px;")
        layout.addWidget(heading)
        return 0
    
    def _add_detail(self, layout, key, value, row=None):
        """Add a key-value detail to the layout."""
        row_layout = QHBoxLayout()
        row_layout.setSpacing(5)
        
        key_label = QLabel(f"{key}:")
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        key_label.setFont(font)
        key_label.setStyleSheet(f"color: {self.theme.text};")
        key_label.setAlignment(Qt.AlignRight)
        key_label.setFixedWidth(120)
        row_layout.addWidget(key_label)
        
        value_text = str(value) if value is not None else "N/A"
        value_color = self.theme.text
        if isinstance(value, bool):
            value_text = "Yes" if value else "No"
            value_color = "#00FF00" if value else "#FF0000"
        
        value_label = QLabel(value_text)
        value_label.setStyleSheet(f"color: {value_color};")
        value_label.setWordWrap(True)
        row_layout.addWidget(value_label)
        
        layout.addLayout(row_layout)
        return 0
    
    def _init_usage_tracking(self):
        """Initialize the usage tracking system."""
        # Create and connect the usage worker
        self.usage_worker = UsageWorker(Config.VENICE_ADMIN_KEY)
        self.usage_worker.usage_data_updated.connect(self._update_usage_display)
        self.usage_worker.balance_data_updated.connect(self._update_balance_display)
        self.usage_worker.daily_usage_updated.connect(self._update_daily_usage_display)
        self.usage_worker.error_occurred.connect(self._handle_usage_error)
        
        # Initialize web usage worker for unified leaderboard
        self.web_usage_worker = WebUsageWorker(Config.VENICE_ADMIN_KEY)
        self.web_usage_worker.progress_updated.connect(self._on_web_usage_progress)
        self.web_usage_worker.web_usage_updated.connect(self._on_web_usage_finished)
        self.web_usage_worker.error_occurred.connect(self._on_web_usage_error)
    
    def _start_usage_updates(self):
        """Start periodic usage data updates."""
        if self.usage_worker:
            # Start initial update
            self.usage_worker.start()
            
            # Set up periodic updates (5 minutes for API keys)
            QTimer.singleShot(Config.USAGE_REFRESH_INTERVAL_MS, self._update_usage_data)
        
        # Start web usage updates (15 minutes interval)
        if self.web_usage_worker:
            # Start initial web usage fetch
            self._refresh_web_usage()
            
            # Set up periodic updates (15 minutes = 900,000 ms)
            QTimer.singleShot(900000, self._update_web_usage_data)
    
    def _update_usage_data(self):
        """Trigger a usage data update and schedule the next one."""
        if self.usage_worker and not self.usage_worker.isRunning():
            self.usage_worker.start()
        
        # Schedule next update
        QTimer.singleShot(Config.USAGE_REFRESH_INTERVAL_MS, self._update_usage_data)
    
    def _update_web_usage_data(self):
        """Trigger a web usage data update and schedule the next one."""
        self._refresh_web_usage()
        
        # Schedule next update (15 minutes)
        QTimer.singleShot(900000, self._update_web_usage_data)
    
    def _refresh_web_usage(self):
        """Refresh web app usage data."""
        if self.web_usage_worker and not self.web_usage_worker.isRunning():
            # Show loading indicator before starting fetch
            if hasattr(self, 'leaderboard_widget'):
                self.leaderboard_widget.show_loading("⏳ Loading web app usage data...")
            self.web_usage_worker.days = 7  # 7-day window to match API keys
            self.web_usage_worker.start()
    
    def _update_daily_usage_display(self, daily_usage: Dict[str, float]):
        """Handle daily usage totals from the Venice billing API."""
        self.current_daily_usage = daily_usage
        logger.debug(f"Daily usage updated - DIEM: {daily_usage.get('diem', 0):.4f}, USD: ${daily_usage.get('usd', 0):.2f}")
        
        # Update any widgets that need to display total daily usage
        # This can be extended in the future for dashboard summaries
    
    def _on_web_usage_progress(self, message: str):
        """Handle web usage fetch progress."""
        logger.debug(f"Web usage progress: {message}")
        # Update loading indicator in leaderboard
        if hasattr(self, 'leaderboard_widget'):
            self.leaderboard_widget.show_loading(f"⏳ {message}")
    
    def _on_web_usage_finished(self, web_metrics: WebUsageMetrics):
        """Handle web usage data received."""
        logger.debug(f"Web usage finished - {web_metrics.diem:.4f} DIEM (${web_metrics.usd:.2f} USD)")
        self.web_usage_metrics = web_metrics
        # Hide loading indicator
        if hasattr(self, 'leaderboard_widget'):
            self.leaderboard_widget.hide_loading()
        self._update_unified_leaderboard()
    
    def _on_web_usage_error(self, error_message: str):
        """Handle web usage fetch error."""
        logger.warning(f"Web usage error: {error_message}")
        # Hide loading indicator on error
        if hasattr(self, 'leaderboard_widget'):
            self.leaderboard_widget.hide_loading()
        # Fall back to API keys only
        self._update_unified_leaderboard()
    
    def _refresh_data(self):
        """
        Refresh all data immediately (for use after key management operations).
        This triggers an immediate data update without waiting for the timer.
        """
        try:
            logger.debug("Refreshing data after key management operation")
            
            if self.usage_worker and not self.usage_worker.isRunning():
                self.usage_worker.start()
            
            # Also update other data if workers exist
            if hasattr(self, 'price_worker') and self.price_worker and not self.price_worker.isRunning():
                self.price_worker.start()
                
        except Exception as e:
            logger.error(f"Failed to refresh data: {e}")
    
    def _update_unified_leaderboard(self):
        """Update leaderboard with combined API key and web usage data."""
        # Get API keys (from existing worker)
        api_keys = self.current_usage_data if self.current_usage_data else []
        
        # Get web usage (default to empty if not yet loaded)
        if hasattr(self, 'web_usage_metrics') and self.web_usage_metrics:
            web_metrics = self.web_usage_metrics
        else:
            # Create empty metrics
            web_metrics = WebUsageMetrics(
                diem=0.0, usd=0.0, vcu=0.0,
                total_requests=0, items=[], by_sku={}
            )
        
        # Create unified entries
        entries, api_diem, api_usd, web_diem, web_usd = \
            UnifiedUsageIntegrator.create_unified_entries(
                api_keys=api_keys,
                web_usage=web_metrics,
                days=7
            )
        
        logger.debug(f"Unified entries created - {len(entries)} total "
              f"(API: {api_diem:.4f} DIEM, Web: {web_diem:.4f} DIEM)")
        
        # Update leaderboard (now accepts UnifiedUsageEntry)
        if hasattr(self, 'leaderboard_widget') and self.leaderboard_widget:
            self.leaderboard_widget.set_data(entries)
        
        # Update balance widget with breakdown
        if hasattr(self, 'hero_balance') and self.hero_balance:
            # Get exchange rate
            if hasattr(self, 'exchange_rate_service') and self.exchange_rate_service:
                try:
                    rate_data = self.exchange_rate_service.get_rate()
                    exchange_rate = rate_data.rate if rate_data else 0.72
                except Exception as e:
                    logger.warning(f"Failed to get exchange rate: {e}")
                    exchange_rate = 0.72
            else:
                exchange_rate = 0.72
            
            self.hero_balance.update_usage_breakdown(
                api_keys_diem=api_diem,
                api_keys_usd=api_usd,
                web_usage_diem=web_diem,
                web_usage_usd=web_usd,
                exchange_rate=exchange_rate
            )
    
    
    def _update_usage_display(self, usage_data: List[APIKeyUsage]):
        """Update the UI with new API key usage data."""
        self.current_usage_data = usage_data
        
        # Clear existing widgets
        for widget in self.api_key_widgets:
            widget.deleteLater()
        self.api_key_widgets.clear()
        
        # Clear layout
        while self.usage_frame_layout.count():
            item = self.usage_frame_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Create new widgets for each API key
        for key_usage in usage_data:
            # Phase 3: Use enhanced management widget if available
            if PHASE3_AVAILABLE and self.key_management_enabled:
                APIKeyManagementWidget = FeatureFlags.get_feature_module('APIKeyManagementWidget')
                if APIKeyManagementWidget:
                    widget = APIKeyManagementWidget(key_usage, self.theme.theme_colors, self.current_balance_data)
                    # Connect management signals
                    widget.key_revoked.connect(self._handle_key_revoke)
                    
                    # Update last used timestamp from security monitoring
                    if hasattr(key_usage, 'last_used_at') and key_usage.last_used_at:
                        widget.update_last_used(key_usage.last_used_at)
                else:
                    widget = APIKeyUsageWidget(key_usage, self.theme.theme_colors)
            else:
                # Fallback to original widget
                widget = APIKeyUsageWidget(key_usage, self.theme.theme_colors)
            
            self.api_key_widgets.append(widget)
            self.usage_frame_layout.addWidget(widget)
        
        # Add stretch to push widgets to the top
        self.usage_frame_layout.addStretch()
        
        # Update the unified leaderboard with API keys and web usage
        self._update_unified_leaderboard()
    
    def _update_balance_display(self, balance_info: BalanceInfo):
        """Update the UI with new balance information using Phase 2 analytics."""
        self.current_balance_data = balance_info
        
        # Update existing API key widgets with new balance info
        for widget in self.api_key_widgets:
            if hasattr(widget, 'update_balance_info'):
                widget.update_balance_info(balance_info)
        
        # Phase 2: Use analytics integration
        try:
            self._update_balance_with_analytics(balance_info, self.current_usage_data)
        except Exception as e:
            logger.error(f"Analytics update failed, falling back to basic update: {e}")
            # Fallback to original update method
            self._update_balance_display_fallback(balance_info)
        
        # Trigger cost analysis refresh when balance data updates
        if hasattr(self, 'cost_optimizer_widget'):
            QTimer.singleShot(1000, self._refresh_cost_analysis)  # Delay to avoid blocking UI
    
    def _update_balance_display_fallback(self, balance_info: BalanceInfo):
        """Fallback balance update method (original implementation)."""
        # Update original balance display
        if self.balance_display:
            self.balance_display.update_balance(balance_info)
        
        # Update hero balance widget
        if hasattr(self, 'hero_balance_display') and self.hero_balance_display:
            try:
                # Extract balance values from BalanceInfo
                diem_balance = balance_info.diem if hasattr(balance_info, 'diem') else 0.0
                usd_balance = balance_info.usd if hasattr(balance_info, 'usd') else 0.0
                
                # Calculate exchange rate if both values are available
                exchange_rate = None
                if diem_balance > 0 and usd_balance > 0:
                    exchange_rate = usd_balance / diem_balance
                
                # Update hero balance widget
                self.hero_balance_display.update_balance(
                    diem_balance=diem_balance,
                    usd_balance=usd_balance,
                    exchange_rate=exchange_rate,
                    animate=True
                )
                
                # Update usage info if we have usage data
                if hasattr(self, 'current_usage_data') and self.current_usage_data:
                    # Calculate simple usage metrics
                    daily_average = self._calculate_daily_average()
                    trend = self._calculate_usage_trend()
                    days_remaining = self._estimate_days_remaining(diem_balance, daily_average)
                    
                    self.hero_balance_display.update_usage_info(
                        daily_average=daily_average,
                        trend=trend,
                        days_remaining=days_remaining
                    )
                
            except Exception as e:
                logger.info(f"Error updating hero balance display: {e}")
                # Set error state if update fails
                self.hero_balance_display.set_error_state("Failed to update balance")
    
    def _calculate_daily_average(self) -> float:
        """Calculate average daily spending from current usage data."""
        try:
            if not hasattr(self, 'current_usage_data') or not self.current_usage_data:
                return 0.0
            
            # Simple calculation - sum all usage and estimate daily average
            total_usage = 0.0
            for usage in self.current_usage_data:
                if hasattr(usage, 'usage') and hasattr(usage.usage, 'usd'):
                    total_usage += usage.usage.usd
            
            # Estimate over last 30 days (rough approximation)
            daily_average = total_usage / 30.0 if total_usage > 0 else 0.0
            return daily_average
            
        except Exception as e:
            logger.info(f"Error calculating daily average: {e}")
            return 0.0
    
    def _calculate_usage_trend(self) -> str:
        """Calculate usage trend from recent data."""
        try:
            # For now, return stable - in the future this could analyze historical data
            # to determine if usage is increasing, decreasing, or stable
            daily_avg = self._calculate_daily_average()
            
            if daily_avg > 5.0:  # High usage
                return "increasing"
            elif daily_avg < 1.0:  # Low usage
                return "decreasing"
            else:
                return "stable"
                
        except Exception as e:
            logger.info(f"Error calculating usage trend: {e}")
            return "stable"
    
    def _estimate_days_remaining(self, current_balance: float, daily_average: float) -> Optional[int]:
        """Estimate days remaining based on current balance and usage."""
        try:
            if daily_average <= 0 or current_balance <= 0:
                return None
            
            days_remaining = int(current_balance / daily_average)
            return max(0, days_remaining)  # Don't return negative days
            
        except Exception as e:
            logger.info(f"Error estimating days remaining: {e}")
            return None
    
    def _handle_usage_error(self, error_msg: str):
        """Handle errors from the usage worker."""
        logger.info(f"Usage tracking error: {error_msg}")
        self.status_bar.showMessage(f"Usage tracking error: {error_msg}")
        
        # Show error message if this is the first error or if it's different from the last one
        if not hasattr(self, '_last_usage_error') or self._last_usage_error != error_msg:
            QMessageBox.critical(self, "Usage Tracking Error", error_msg)
            self._last_usage_error = error_msg
    
    def display_filtered_models(self):
        """Display models filtered by selected type."""
        selected_type = self.type_combobox.currentText()
        selected_trait = self.traits_combobox.currentText()
        self.clear_display_frame()

        # Ensure scroll area is reset
        self.scroll_area.verticalScrollBar().setValue(0)

        if not self.models_data or 'data' not in self.models_data:
            error_label = QLabel("No model data available.")
            error_label.setStyleSheet(f"color: orange;")
            self.display_layout.addWidget(error_label, alignment=Qt.AlignCenter)
            return

        # Store original data and filter from it - NEVER modify the original!
        # Create a deep copy to prevent ANY potential reference issues
        import copy
        original_models = copy.deepcopy(self.models_data['data'])
        filtered_models = []

        # Apply current filter to create display list
        for model in original_models:
            # Defensive programming: ensure model is a dictionary
            if not isinstance(model, dict):
                logger.debug(f"Skipping invalid model data: {model}")
                continue

            model_id = model.get('id', 'N/A')

            # Defensive check: ensure model_id exists and is not None
            if not model_id or model_id == 'N/A':
                logger.debug("Skipping model with invalid ID")
                continue

            model_type = model.get('type')
            model_spec = model.get('model_spec', {})

            # Defensive check: ensure model_type is a string
            if not isinstance(model_type, str) or model_type == 'Unknown':
                logger.debug(f"Skipping model '{model_id}' with invalid type: {model_type}")
                continue

            traits = model_spec.get('traits', []) if isinstance(model_spec, dict) else []

            # Case-insensitive trait matching - ensure traits is a list
            if not isinstance(traits, list):
                traits = []
                logger.debug(f"Warning - model '{model_id}' has invalid traits format: {traits}")

            trait_match = selected_trait == "all" or selected_trait in traits
            type_match = selected_type == "all" or model_type == selected_type

            logger.debug(f"Model '{model_id}' - Type: {model_type}, Traits: {traits}, Type match: {type_match}, Trait match: {trait_match}")

            if type_match and trait_match:
                filtered_models.append(model)

        logger.debug(f"Filtered {len(filtered_models)} models out of {len(original_models)} total models")

        found_models = False
        models_container = QWidget()
        container_layout = QVBoxLayout(models_container)
        container_layout.setSpacing(10)
        container_layout.setContentsMargins(5, 5, 5, 5)

        # Display only the filtered models
        for model in filtered_models:
            found_models = True

            model_id = model.get('id', 'N/A')
            model_type = model.get('type', 'Unknown')
            model_spec = model.get('model_spec', {})

            # Create model frame
            model_frame = QGroupBox(f" {model_id} ")
            model_frame.setStyleSheet(f"""
                QGroupBox {{
                    background-color: {self.theme.background};
                    border: 1px solid #555555;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding: 10px;
                    color: {self.theme.text};
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    padding: 0 5px;
                    background-color: {self.theme.background};
                }}
            """)
            model_layout = QVBoxLayout(model_frame)
            model_layout.setSpacing(5)
            model_layout.setContentsMargins(5, 5, 5, 5)

            current_row = 0
            current_row = self._add_detail(model_layout, "Type", model_type, current_row)

            if model_type == "text":
                current_row = self._add_detail(model_layout, "Context Tokens", model_spec.get('availableContextTokens'), current_row)

            current_row = self._add_separator(model_layout)

            if model_type == "text":
                caps = model_spec.get('capabilities')
                if caps:
                    current_row = self._add_section_heading(model_layout, "Capabilities", current_row)
                    for key, value in caps.items():
                        current_row = self._add_detail(model_layout, key, value, current_row)
                    current_row = self._add_separator(model_layout)

                const = model_spec.get('constraints')
                if const:
                    current_row = self._add_section_heading(model_layout, "Constraints", current_row)
                    for key, value in const.items():
                        if isinstance(value, dict):
                            for sub_key, sub_value in value.items():
                                current_row = self._add_detail(model_layout, f"{key} ({sub_key})", sub_value, current_row)
                        else:
                            current_row = self._add_detail(model_layout, key, value, current_row)
                    current_row = self._add_separator(model_layout)

            elif model_type == "image":
                const = model_spec.get('constraints')
                if const:
                    current_row = self._add_section_heading(model_layout, "Constraints", current_row)
                    for key, value in const.items():
                        if isinstance(value, dict):
                            for sub_key, sub_value in value.items():
                                current_row = self._add_detail(model_layout, f"{key} ({sub_key})", sub_value, current_row)
                        else:
                            current_row = self._add_detail(model_layout, key, value, current_row)
                    current_row = self._add_separator(model_layout)

            elif model_type == "tts":
                voices = model_spec.get('voices', [])
                if voices:
                    current_row = self._add_section_heading(model_layout, "Voices", current_row)
                    current_row = self._add_detail(model_layout, "Available", ", ".join(voices), current_row)
                    current_row = self._add_separator(model_layout)

            traits = model_spec.get('traits', [])
            if traits:
                current_row = self._add_section_heading(model_layout, "Traits", current_row)
                current_row = self._add_detail(model_layout, "Assigned", ", ".join(traits), current_row)
                current_row = self._add_separator(model_layout)

            other_info_exists = any(k in model_spec for k in ['modelSource', 'beta', 'offline'])
            if other_info_exists:
                current_row = self._add_section_heading(model_layout, "Other Info", current_row)
                current_row = self._add_detail(model_layout, "Source", model_spec.get('modelSource'), current_row)
                current_row = self._add_detail(model_layout, "Beta", model_spec.get('beta'), current_row)
                current_row = self._add_detail(model_layout, "Offline", model_spec.get('offline'), current_row)

            container_layout.addWidget(model_frame)

        if found_models:
            self.display_layout.addWidget(models_container)
        else:
            not_found_label = QLabel(f"No models found for type: '{selected_type}'")
            not_found_label.setStyleSheet(f"color: orange;")
            self.display_layout.addWidget(not_found_label, alignment=Qt.AlignCenter)

        # Ensure scroll area updates
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(0))

    def create_comparison_tab(self):
        """Create the model comparison and analytics tab"""
        self.comparison_tab = QWidget()
        self.comparison_tab.setStyleSheet(f"background-color: {self.theme.background};")

        # Create the model comparison widget
        self.model_comparison_widget = ModelComparisonWidget(self.theme, self.models_data)
        tab_layout = QVBoxLayout(self.comparison_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(self.model_comparison_widget)

        # Connect the connect signal from the comparison widget to the main app's connect method
        self.model_comparison_widget.signals.connect_requested.connect(self.connect_thread)

        # Add tab to main tabs
        self.main_tabs.addTab(self.comparison_tab, "📊 Compare & Analyze")

    def create_leaderboard_tab(self):
        """Create the usage leaderboard tab"""
        self.leaderboard_tab = QWidget()
        tab_layout = QVBoxLayout(self.leaderboard_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the leaderboard widget
        self.leaderboard_widget = UsageLeaderboardWidget(self.theme.theme_colors)
        tab_layout.addWidget(self.leaderboard_widget)
        
        # Add tab to main tabs
        self.main_tabs.addTab(self.leaderboard_tab, "📊 Usage Leaderboard")

    def update_model_comparison_data(self):
        """Update the comparison widget with new model data"""
        if hasattr(self, 'model_comparison_widget') and self.model_comparison_widget:
            # Always use the full original data for the widget
            self.model_comparison_widget.original_models_data = self.models_data.copy() if self.models_data else {}
            self.model_comparison_widget.models_data = self.models_data.copy() if self.models_data else {}
            # Refresh the displays
            self.model_comparison_widget.populate_comparison_table()
            self.model_comparison_widget.populate_discovery_results()

    def _copy_models_data(self):
        """Create a deep copy of models data to prevent filtering from modifying the original data"""
        import copy
        return copy.deepcopy(self.models_data) if self.models_data else None

    def __del__(self):
        """Destructor to clean up resources"""
        try:
            self._cleanup_threads()
        except Exception as e:
            logger.debug(f"Error in destructor: {e}")

    def closeEvent(self, event):
        """Override close event to properly clean up resources"""
        logger.debug("Close event triggered, cleaning up...")

        try:
            # Phase 2: Stop exchange rate service
            if hasattr(self, 'exchange_rate_service') and self.exchange_rate_service:
                logger.debug("Stopping exchange rate service...")
                self.exchange_rate_service.stop_automatic_updates()
            
            # Stop all timers
            for timer in self.findChildren(QTimer):
                if timer.isActive():
                    timer.stop()

            # Clean up threads
            self._cleanup_threads()

            # Clean up model comparison widget if it exists
            if hasattr(self, 'model_comparison_widget') and self.model_comparison_widget:
                if hasattr(self.model_comparison_widget, 'analytics_worker'):
                    if self.model_comparison_widget.analytics_worker and self.model_comparison_widget.analytics_worker.isRunning():
                        self.model_comparison_widget.analytics_worker.wait()

            logger.debug("Cleanup completed successfully")

        except Exception as e:
            logger.debug(f"Error during cleanup: {e}")

        event.accept()

    def _cleanup_threads(self):
        """Clean up all active threads to prevent crashes"""
        logger.debug("Cleaning up threads...")

        # Clean up API worker
        if hasattr(self, 'api_worker') and self.api_worker and self.api_worker.isRunning():
            logger.debug("Waiting for API worker to finish...")
            self.api_worker.wait()

        # Clean up style worker
        if hasattr(self, 'style_worker') and self.style_worker and self.style_worker.isRunning():
            logger.debug("Waiting for style worker to finish...")
            self.style_worker.wait()

        # Clean up traits worker
        if hasattr(self, 'traits_worker') and self.traits_worker and self.traits_worker.isRunning():
            logger.debug("Waiting for traits worker to finish...")
            self.traits_worker.wait()

        # Clean up usage worker
        if self.usage_worker and self.usage_worker.isRunning():
            logger.debug("Waiting for usage worker to finish...")
            self.usage_worker.wait()

        logger.debug("Thread cleanup complete")

    def fetch_traits(self):
        """Starts fetching model traits in a separate thread."""
        self.traits_worker = APIWorkerFactory.create_traits_worker(parent=self)
        self.traits_worker.result.connect(self._update_gui_after_fetch_traits)
        self.traits_worker.start()

    def _update_gui_after_fetch_traits(self, result):
        """Updates GUI with model traits data."""
        if result['success']:
            traits_data = result['data']
            logger.debug(f"Raw Traits API response: {traits_data}")

            # Handle different possible response structures
            trait_names = []

            # First check if we have a standard API response with 'data' field
            if isinstance(traits_data, dict) and 'data' in traits_data:
                logger.debug("Found 'data' field in response")
                data = traits_data['data']

                # Check if data is a list of trait objects
                if isinstance(data, list):
                    logger.debug(f"Data is a list with {len(data)} items")
                    # Try to extract trait names from list items
                    for item in data:
                        if isinstance(item, dict) and 'name' in item:
                            trait_names.append(item['name'])
                        elif isinstance(item, str):
                            trait_names.append(item)

                # Check if data is a dictionary of traits
                elif isinstance(data, dict):
                    logger.debug(f"Data is a dictionary with {len(data)} keys")
                    # If data has a 'traits' field, use that
                    if 'traits' in data:
                        traits = data['traits']
                        if isinstance(traits, list):
                            trait_names = traits
                        elif isinstance(traits, dict):
                            trait_names = list(traits.keys())
                    else:
                        # Otherwise assume the top-level keys are the trait names
                        trait_names = list(data.keys())

            # If no 'data' field, try to extract directly
            else:
                logger.debug("No 'data' field found in response")
                if isinstance(traits_data, list):
                    # Assume list contains trait names
                    trait_names = [str(item) for item in traits_data if isinstance(item, (str, int))]
                elif isinstance(traits_data, dict):
                    # Try to find trait names in common fields
                    if 'traits' in traits_data:
                        traits = traits_data['traits']
                        if isinstance(traits, list):
                            trait_names = traits
                        elif isinstance(traits, dict):
                            trait_names = list(traits.keys())
                    else:
                        # Fallback: use top-level keys as trait names
                        trait_names = list(traits_data.keys())

            # Filter out non-trait keys that might be in the response
            valid_trait_names = []
            for name in trait_names:
                # Skip common API structural keys
                if name.lower() not in ['data', 'object', 'type', 'id', 'meta', 'links']:
                    valid_trait_names.append(name)

            logger.debug(f"Extracted {len(valid_trait_names)} valid traits: {valid_trait_names}")

            self.traits_combobox.clear()
            self.traits_combobox.addItems(["all"] + valid_trait_names)
            self.traits_combobox.setCurrentText("all")
            self.traits_combobox.setEnabled(True)
        else:
            logger.debug(f"Traits API error: {result.get('error', 'Unknown error')}")
            self.traits_combobox.clear()
            self.traits_combobox.addItems(["all"])
            self.traits_combobox.setEnabled(False)
            if result['error']:
                self._show_api_error("Traits API Error", result['error'])
    
    # Phase 2 Enhancement Methods
    
    def _init_phase2_services(self):
        """Initialize Phase 2 analytics and exchange rate services."""
        try:
            # Only initialize if components are available
            if not self.exchange_rate_service:
                logger.debug("Exchange rate service not available, skipping initialization")
                return
                
            # Connect exchange rate service signals
            self.exchange_rate_service.rate_updated.connect(self._handle_rate_update)
            self.exchange_rate_service.rate_error.connect(self._handle_rate_error)
            
            # DON'T start automatic rate updates yet - this might be causing the thread issue
            # self.exchange_rate_service.start_automatic_updates(interval_minutes=5)
            
            logger.debug("Phase 2 services initialized successfully (without auto-updates)")
            
        except Exception as e:
            logger.error(f"Failed to initialize Phase 2 services: {e}")
            # Don't let this break the app - just continue without Phase 2 features
    
    def _handle_rate_update(self, rate_data):
        """
        Handle exchange rate updates.
        
        Args:
            rate_data: ExchangeRateData object
        """
        try:
            # Update hero balance widget with new rate
            if hasattr(self, 'hero_balance_display'):
                self.hero_balance_display.update_exchange_rate_display(rate_data)
            
            # Update status bar
            self.status_bar.showMessage(f"Exchange rate updated: {rate_data.rate:.4f}", 2000)
            
        except Exception as e:
            logger.error(f"Failed to handle rate update: {e}")
    
    def _handle_rate_error(self, error_msg: str):
        """
        Handle exchange rate fetch errors.
        
        Args:
            error_msg: Error message
        """
        logger.warning(f"Exchange rate error: {error_msg}")
        self.status_bar.showMessage(f"Rate update failed: {error_msg}", 5000)
    
    def _update_balance_with_analytics(self, balance_info, usage_data):
        """
        Update balance display with analytics integration.
        
        Args:
            balance_info: BalanceInfo object
            usage_data: List of APIKeyUsage objects
        """
        try:
            # Record usage snapshot for analytics
            self.usage_analytics.record_usage_snapshot(usage_data, balance_info)
            
            # Get usage trend analysis
            trend = self.usage_analytics.get_usage_trend(days=7)
            
            # Calculate days remaining estimate
            current_rate = getattr(self.exchange_rate_service.current_rate, 'rate', 0.72) if self.exchange_rate_service.current_rate else 0.72
            days_remaining = self.usage_analytics.estimate_days_remaining(balance_info.usd)
            trend.days_remaining_estimate = days_remaining
            
            # Update hero widget with analytics
            if hasattr(self, 'hero_balance_display'):
                self.hero_balance_display.update_with_analytics(
                    balance_info, 
                    trend, 
                    self.exchange_rate_service.current_rate
                )
            
            # Update original widget for backward compatibility
            if hasattr(self, 'balance_display') and self.balance_display:
                self.balance_display.update_balance_info(balance_info)
                
        except Exception as e:
            logger.error(f"Failed to update balance with analytics: {e}")
            # Fallback to basic update
            if hasattr(self, 'hero_balance_display'):
                self.hero_balance_display.update_balance(
                    balance_info.diem, 
                    balance_info.usd, 
                    0.72  # Fallback rate
                )
    
    def get_usage_analytics_summary(self) -> Dict[str, any]:
        """
        Get comprehensive usage analytics summary.
        
        Returns:
            Dictionary with analytics data
        """
        try:
            summary = self.usage_analytics.get_usage_summary(days=7)
            
            # Add current balance data
            if hasattr(self, 'hero_balance_display'):
                balance_summary = self.hero_balance_display.get_analytics_summary()
                summary.update(balance_summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get analytics summary: {e}")
            return {"error": str(e)}
    
    # Phase 3: Key Management Signal Handlers
    
    def _handle_key_rename(self, key_id: str, new_name: str):
        """
        Handle API key rename request with real Venice API integration.
        
        Args:
            key_id: ID of the key to rename
            new_name: New name for the key
        """
        try:
            logger.debug(f"Renaming key {key_id} to '{new_name}'")
            
            # Get Venice key management service
            get_key_management_service = FeatureFlags.get_feature_module('get_key_management_service')
            key_service = get_key_management_service() if get_key_management_service else None
            
            if key_service:
                # Make actual API call to Venice
                success = key_service.rename_api_key(key_id, new_name)
                
                if success:
                    # Update local data only after successful API call
                    for key_usage in self.current_usage_data:
                        if key_usage.id == key_id:
                            key_usage.name = new_name
                            break
                    
                    self.status_bar.showMessage(f"Key successfully renamed to '{new_name}'", 3000)
                    
                    # Generate usage report with new name
                    if self.usage_report_generator:
                        for key_usage in self.current_usage_data:
                            if key_usage.id == key_id:
                                self.usage_report_generator.record_usage_snapshot(key_usage)
                                break
                    
                    # Refresh data to show the change
                    self._refresh_data()
                else:
                    self.status_bar.showMessage(f"Rename not supported by Venice API", 5000)
                    QMessageBox.information(self, "Operation Not Supported", 
                                      f"Venice API does not support renaming existing API keys.\n\n"
                                      f"Available operations:\n"
                                      f"• Create new keys (with custom descriptions)\n"
                                      f"• Delete/revoke existing keys\n"
                                      f"• View key details and usage\n\n"
                                      f"To 'rename' a key, you would need to:\n"
                                      f"1. Create a new key with the desired name\n"
                                      f"2. Update your applications to use the new key\n"
                                      f"3. Delete the old key\n\n"
                                      f"This ensures your key security is maintained.")
            else:
                # Fallback to local update only
                logger.warning("Venice key management service not available, updating locally only")
                for key_usage in self.current_usage_data:
                    if key_usage.id == key_id:
                        key_usage.name = new_name
                        break
                self.status_bar.showMessage(f"Key renamed locally to '{new_name}' (API unavailable)", 3000)
                        
        except Exception as e:
            logger.error(f"Failed to rename key: {e}")
            self.status_bar.showMessage(f"Failed to rename key: {e}", 5000)
    def _handle_key_revoke(self, key_id: str):
        """
        Handle API key revocation request with real Venice API integration.
        
        Args:
            key_id: ID of the key to revoke
        """
        try:
            logger.debug(f"Revoking key {key_id}")
            
            # Get Venice key management service
            get_key_management_service = FeatureFlags.get_feature_module('get_key_management_service')
            key_service = get_key_management_service() if get_key_management_service else None
            
            if key_service:
                # Make actual API call to Venice
                success = key_service.revoke_api_key(key_id)
                
                if success:
                    # Update local data only after successful API call
                    for key_usage in self.current_usage_data:
                        if key_usage.id == key_id:
                            key_usage.is_active = False
                            break
                    
                    self.status_bar.showMessage("Key successfully revoked", 3000)
                    
                    # Refresh data to show the change
                    self._refresh_data()
                else:
                    self.status_bar.showMessage("Failed to revoke key - Venice API error", 5000)
                    QMessageBox.warning(self, "Revocation Failed", 
                                      f"Could not revoke the API key. This may be because:\n"
                                      f"• The key doesn't exist\n"
                                      f"• Network connectivity issues\n"
                                      f"• Insufficient permissions\n\n"
                                      f"Check the console for detailed error information.")
            else:
                # Fallback to local update only
                logger.warning("Venice key management service not available, updating locally only")
                for key_usage in self.current_usage_data:
                    if key_usage.id == key_id:
                        key_usage.is_active = False
                        break
                self.status_bar.showMessage("Key revoked locally (API unavailable)", 3000)
            
        except Exception as e:
            logger.error(f"Failed to revoke key: {e}")
            self.status_bar.showMessage(f"Failed to revoke key: {e}", 5000)
            QMessageBox.critical(self, "Error", f"An error occurred while revoking the key:\n{e}")


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    window = CombinedViewerApp()
    window.show()
    sys.exit(app.exec())


# Main application
if __name__ == "__main__":
    main()
