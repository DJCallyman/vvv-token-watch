import sys
import time
from typing import Dict, Optional, List
import logging
import warnings
import urllib3

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                 QLabel, QPushButton, QComboBox, QFrame, QScrollArea,
                                 QMessageBox, QStatusBar, QTabWidget, QGroupBox,
                                 QTextEdit, QLineEdit)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QDoubleValidator

# Add the project directory to Python path (make it dynamic)
import os
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import local modules using relative imports (now a standalone repo)
from src.utils.utils import format_currency, validate_holding_amount, ValidationState
from src.utils.error_handler import ErrorHandler
from src.config.config import Config
from src.config.theme import Theme
from src.config.features import FeatureFlags
from src.widgets.price_display import PriceDisplayWidget
from src.analytics.model_comparison import ModelComparisonWidget
from src.core.usage_tracker import UsageWorker, BalanceInfo, APIKeyUsage
from src.core.worker_factory import APIWorkerFactory
from src.widgets.vvv_display import BalanceDisplayWidget, APIKeyUsageWidget
from src.widgets.enhanced_balance_widget import HeroBalanceWidget
from src.widgets.action_buttons import ActionButtonWidget
from src.widgets.usage_leaderboard import UsageLeaderboardWidget
from src.widgets.backend_status_bar import BackendStatusBar
from src.core.web_usage import WebUsageWorker, WebUsageMetrics
from src.core.unified_usage import UnifiedUsageIntegrator
from src.widgets.cost_optimization_widget import CostOptimizationWidget
from src.core.price_worker import PriceWorker
from src.core.cost_analysis_worker import CostAnalysisWorker
from src.core.model_cache import ModelCacheManager
from src.core.venice_api_client import VeniceAPIClient

# --- Suppress Warnings (Use with caution) ---
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)


# --- Logging Configuration ---
def setup_logging():
    """
    Configure application-wide logging with proper levels and handlers.
    Replaces scattered print() statements with proper logging.
    """
    # Determine log level from config
    log_level = logging.DEBUG if Config.DEBUG_MODE else logging.INFO
    
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
        
        # Initialize model cache early to fetch current models/pricing
        logger.info("Initializing model cache from Venice API...")
        self.model_cache = ModelCacheManager()
        cache_success = self.model_cache.fetch_models()
        if cache_success:
            logger.info(f"Model cache initialized with {len(self.model_cache.models)} models")
        else:
            logger.warning("Model cache initialization failed, using local cache if available")
        
        # Initialize Venice API client for workers
        self.api_client = VeniceAPIClient(Config.VENICE_API_KEY)
        
        # Populate models_data from cache for Models & Compare tabs
        # This ensures these widgets use the same fresh data as the cache
        if self.model_cache.raw_api_data:
            self.models_data = self.model_cache.raw_api_data
            logger.info(f"Models tab will use {len(self.models_data.get('data', []))} models from cache")
        else:
            self.models_data = None
            logger.warning("No model data available for Models tab")
            
        self.setWindowTitle("Venice AI Models & CoinGecko Price Viewer")
        self.setMinimumSize(1200, 850)  # Increased minimum size for better chart display
        
        # Set a good default size for 1470x956 display
        self.resize(1280, 920)
        
        # Extract model types from cached data
        self.model_types = ["all"]
        if self.models_data:
            types = set(model.get('type', 'Unknown') for model in self.models_data.get('data', []))
            types = {str(t) if t is not None else 'Unknown' for t in types}
            self.model_types = ["all"] + sorted(list(types))
            logger.info(f"Available model types: {self.model_types}")
        
        self.price_data = {
            'usd': {'price': None, 'total': None},
            'aud': {'price': None, 'total': None}
        }
        self.holding_amount = Config.COINGECKO_HOLDING_AMOUNT
        self.validation_state = ValidationState.VALID
        
        # DIEM token price tracking
        self.diem_price_data = {
            'usd': {'price': None, 'total': None},
            'aud': {'price': None, 'total': None}
        }
        self.diem_holding_amount = Config.DIEM_HOLDING_AMOUNT
        self.diem_validation_state = ValidationState.VALID
        
        # Initialize API usage tracking components
        self.usage_worker = None
        self.web_usage_worker = None
        self.web_usage_metrics = None
        self.balance_display = None
        self.api_key_widgets = []
        self.current_usage_data = []
        self.current_balance_data = None
        self.current_daily_usage = {}  # Store daily usage totals
        
        # Price worker scheduling guard
        self._price_update_scheduled = False
        self._diem_price_update_scheduled = False
        
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
        
        # Connect theme change signal before initializing UI
        self.theme.theme_changed.connect(self._on_theme_changed)
        
        # Initialize UI
        self.init_ui()
    
    def get_combobox_style(self):
        """Get the modern combobox stylesheet"""
        self.theme.background
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
        self.theme.background
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
        
        # Create comprehensive backend status bar
        self.status_bar = BackendStatusBar(self.theme)
        self.setStatusBar(self.status_bar)
        self.status_bar.set_process_running(self.status_bar.PROCESS_MODELS, "Initializing...")
        
        # Connect status bar signals
        self.status_bar.refresh_all_requested.connect(self.refresh_all_action)
        self.status_bar.clear_errors_requested.connect(self._on_clear_status_errors)
        
        # Update initial status
        self.status_bar.set_process_success(self.status_bar.PROCESS_MODELS, "Ready")
        self.status_bar.set_process_success(self.status_bar.PROCESS_PRICES, "Ready")
        
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
        
        # Create price display components - Venice Token
        self.price_display_usd = PriceDisplayWidget(self.theme)
        self.price_display_aud = PriceDisplayWidget(self.theme)
        
        # Create price display components - DIEM Token
        self.price_display_diem_usd = PriceDisplayWidget(self.theme)
        self.price_display_diem_aud = PriceDisplayWidget(self.theme)

        # Create price container with horizontal layout for both tokens
        self.price_container = QWidget()
        self.price_container.setStyleSheet(f"background-color: {self.theme.background};")
        price_layout = QVBoxLayout(self.price_container)
        price_layout.setSpacing(10)
        price_layout.setContentsMargins(10, 10, 10, 10)

        # Create horizontal layout for Venice and DIEM tokens side by side
        tokens_horizontal_layout = QHBoxLayout()
        tokens_horizontal_layout.setSpacing(20)
        
        # --- VENICE TOKEN (Left Side) ---
        venice_container = QWidget()
        venice_layout = QVBoxLayout(venice_container)
        venice_layout.setSpacing(10)
        venice_layout.setContentsMargins(0, 0, 0, 0)
        
        # Venice Token name
        token_name_text = Config.COINGECKO_TOKEN_ID.replace('-', ' ').capitalize()
        self.token_name_label = QLabel(token_name_text)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.token_name_label.setFont(font)
        self.token_name_label.setStyleSheet(f"color: {self.theme.text};")
        self.token_name_label.setAlignment(Qt.AlignCenter)
        venice_layout.addWidget(self.token_name_label)

        # Venice Holding amount
        self.holding_frame = QFrame()
        self.holding_frame.setStyleSheet(f"background-color: {self.theme.background};")
        holding_layout = QHBoxLayout(self.holding_frame)
        holding_layout.setContentsMargins(0, 0, 0, 0)

        holding_label = QLabel("Holding:")
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

        venice_layout.addWidget(self.holding_frame, alignment=Qt.AlignCenter)

        # Venice Price displays
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

        venice_layout.addWidget(self.prices_frame)

        # Venice Price status
        self.price_status_label = QLabel("Initializing...")
        self.price_status_label.setStyleSheet(f"color: {self.theme.text};")
        self.price_status_label.setAlignment(Qt.AlignCenter)
        venice_layout.addWidget(self.price_status_label)
        
        tokens_horizontal_layout.addWidget(venice_container)
        
        # --- DIEM TOKEN (Right Side) ---
        diem_container = QWidget()
        diem_layout = QVBoxLayout(diem_container)
        diem_layout.setSpacing(10)
        diem_layout.setContentsMargins(0, 0, 0, 0)
        
        # DIEM Token name
        diem_token_name_text = "DIEM Token"
        self.diem_token_name_label = QLabel(diem_token_name_text)
        diem_font = QFont()
        diem_font.setPointSize(16)
        diem_font.setBold(True)
        self.diem_token_name_label.setFont(diem_font)
        self.diem_token_name_label.setStyleSheet(f"color: {self.theme.text};")
        self.diem_token_name_label.setAlignment(Qt.AlignCenter)
        diem_layout.addWidget(self.diem_token_name_label)
        
        # DIEM Holding amount
        self.diem_holding_frame = QFrame()
        self.diem_holding_frame.setStyleSheet(f"background-color: {self.theme.background};")
        diem_holding_layout = QHBoxLayout(self.diem_holding_frame)
        diem_holding_layout.setContentsMargins(0, 0, 0, 0)
        
        diem_holding_label = QLabel("Holding:")
        diem_holding_label.setStyleSheet(f"color: {self.theme.text};")
        diem_holding_layout.addWidget(diem_holding_label)
        
        self.diem_holding_entry = QLineEdit(str(Config.DIEM_HOLDING_AMOUNT))
        self.diem_holding_entry.setFixedWidth(80)
        self.diem_holding_entry.textChanged.connect(self._on_diem_holding_text_changed)
        self.diem_holding_entry.editingFinished.connect(self.update_diem_holding_amount)
        self.diem_holding_entry.setValidator(QDoubleValidator(0.0, 1000000.0, 2))
        diem_holding_layout.addWidget(self.diem_holding_entry)
        
        diem_token_label = QLabel("tokens")
        diem_token_label.setStyleSheet(f"color: {self.theme.text};")
        diem_holding_layout.addWidget(diem_token_label)
        
        diem_layout.addWidget(self.diem_holding_frame, alignment=Qt.AlignCenter)
        
        # DIEM Price displays
        self.diem_prices_frame = QFrame()
        self.diem_prices_frame.setStyleSheet(f"background-color: {self.theme.background};")
        diem_prices_layout = QHBoxLayout(self.diem_prices_frame)
        diem_prices_layout.setSpacing(10)
        
        # DIEM USD Display
        self.diem_usd_group = QGroupBox(" USD ")
        self.diem_usd_group.setStyleSheet(f"""
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
        diem_usd_layout = QVBoxLayout(self.diem_usd_group)
        diem_usd_layout.addWidget(self.price_display_diem_usd)
        diem_prices_layout.addWidget(self.diem_usd_group)
        
        # DIEM AUD Display
        self.diem_aud_group = QGroupBox(" AUD ")
        self.diem_aud_group.setStyleSheet(f"""
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
        diem_aud_layout = QVBoxLayout(self.diem_aud_group)
        diem_aud_layout.addWidget(self.price_display_diem_aud)
        diem_prices_layout.addWidget(self.diem_aud_group)
        
        diem_layout.addWidget(self.diem_prices_frame)
        
        # DIEM Price status
        self.diem_price_status_label = QLabel("Initializing...")
        self.diem_price_status_label.setStyleSheet(f"color: {self.theme.text};")
        self.diem_price_status_label.setAlignment(Qt.AlignCenter)
        diem_layout.addWidget(self.diem_price_status_label)
        
        tokens_horizontal_layout.addWidget(diem_container)
        
        # Add the horizontal layout to main price layout
        price_layout.addLayout(tokens_horizontal_layout)

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
        
        # Initialize Models tab and Compare tab with cached data
        # This populates them immediately on startup without requiring "Connect" button
        self._init_models_tabs_from_cache()

        # Initialize holding entry with proper value format
        self.holding_entry.setText(str(int(Config.COINGECKO_HOLDING_AMOUNT)) if Config.COINGECKO_HOLDING_AMOUNT.is_integer() else f"{Config.COINGECKO_HOLDING_AMOUNT:.2f}")
        
        # Initialize usage tracking
        self._init_usage_tracking()
        
        # Phase 2: Initialize analytics and exchange rate services
        self._init_phase2_services()
        
        # Start periodic updates
        QTimer.singleShot(Config.COINGECKO_INITIAL_DELAY_MS, self.update_price_label)
        QTimer.singleShot(Config.COINGECKO_INITIAL_DELAY_MS + 1000, self.update_diem_price_label)  # Stagger DIEM updates
        QTimer.singleShot(1000, self._start_usage_updates)  # Start usage updates after a short delay
        
        # Apply theme after all widgets are created (important for Windows)
        self.theme.apply_palette(QApplication.instance())
        self._apply_theme()
        
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
            # Set to error state on error
            self.validation_state = ValidationState.ERROR
            self.price_display_usd.set_validation_state(ValidationState.ERROR.value)
            self.price_display_aud.set_validation_state(ValidationState.ERROR.value)
    
    def _on_diem_holding_text_changed(self, text: str):
        """Validate DIEM holding amount input as user types."""
        try:
            state = validate_holding_amount(text)
            self.diem_validation_state = state
            self.price_display_diem_usd.set_validation_state(state.value)
            self.price_display_diem_aud.set_validation_state(state.value)
        except Exception as e:
            logging.error(f"Error validating DIEM holding amount input: {e}")
            # Set to error state on error
            self.diem_validation_state = ValidationState.ERROR
            self.price_display_diem_usd.set_validation_state(ValidationState.ERROR.value)
            self.price_display_diem_aud.set_validation_state(ValidationState.ERROR.value)
    
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
    
    def update_diem_holding_amount(self):
        """Validates and processes user input for DIEM holding amount."""
        try:
            new_amount = float(self.diem_holding_entry.text())
            if new_amount < 0:  # Allow 0 for DIEM
                raise ValueError("Amount must be non-negative")
            self.diem_holding_amount = new_amount
            for currency in Config.COINGECKO_CURRENCIES:
                if self.diem_price_data[currency]['price'] is not None:
                    self.diem_price_data[currency]['total'] = self.diem_price_data[currency]['price'] * self.diem_holding_amount
            
            # Update price displays
            self._update_diem_price_display()
            
            # Update status
            self.diem_price_status_label.setText(f"Holding amount updated to {new_amount:.2f}. Price updates automatically.")
            self.diem_price_status_label.setStyleSheet(f"color: {self.theme.text};")
            
            # Update theme for all components
            self._apply_theme()
        
        except ValueError:
            self.diem_holding_entry.setText(str(int(self.diem_holding_amount)) if self.diem_holding_amount.is_integer() else f"{self.diem_holding_amount:.2f}")
            self.diem_price_status_label.setText("Invalid holding amount. Must be a non-negative number.")
            self.diem_price_status_label.setStyleSheet(f"color: {self.theme.error};")
            # Ensure price display is updated with current valid holding amount
            self._update_diem_price_display()
    
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
    
    def _update_diem_price_display(self):
        """Update DIEM price display based on current diem_price_data and diem_holding_amount"""
        # Update USD display
        if self.diem_price_data['usd']['price'] is not None:
            self.price_display_diem_usd.set_price(self.diem_price_data['usd']['price'])
            self.price_display_diem_usd.set_holding_value(self.diem_price_data['usd']['total'])
        else:
            self.price_display_diem_usd.set_price(0)
            self.price_display_diem_usd.set_holding_value(0)
        
        # Update AUD display
        if self.diem_price_data['aud']['price'] is not None:
            self.price_display_diem_aud.set_price(self.diem_price_data['aud']['price'])
            self.price_display_diem_aud.set_holding_value(self.diem_price_data['aud']['total'])
        else:
            self.price_display_diem_aud.set_price(0)
            self.price_display_diem_aud.set_holding_value(0)
    
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
        
        # Update usage frame (API key cards container)
        if hasattr(self, 'usage_frame'):
            self.usage_frame.setStyleSheet(f"background-color: {bg_color};")
        
        # Update Models tab containers
        if hasattr(self, 'display_frame'):
            self.display_frame.setStyleSheet(f"background-color: {bg_color};")
        if hasattr(self, 'models_tab'):
            self.models_tab.setStyleSheet(f"background-color: {bg_color};")
        
        # Update tab containers
        if hasattr(self, 'balance_tab'):
            self.balance_tab.setStyleSheet(f"background-color: {bg_color};")
        if hasattr(self, 'cost_optimization_tab'):
            self.cost_optimization_tab.setStyleSheet(f"background-color: {bg_color};")
        if hasattr(self, 'comparison_tab'):
            self.comparison_tab.setStyleSheet(f"background-color: {bg_color};")
        if hasattr(self, 'leaderboard_tab'):
            self.leaderboard_tab.setStyleSheet(f"background-color: {bg_color};")
        
        # Update main tabs widget
        if hasattr(self, 'main_tabs'):
            self.main_tabs.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: 1px solid {border_color};
                    background-color: {bg_color};
                }}
                QTabBar::tab {{
                    background-color: {card_bg};
                    color: {text_color};
                    padding: 8px 16px;
                    border: 1px solid {border_color};
                    margin-right: 2px;
                }}
                QTabBar::tab:selected {{
                    background-color: {accent_color};
                    color: {text_color};
                }}
                QTabBar::tab:hover {{
                    background-color: {accent_color};
                }}
            """)
        
        # Update token name label
        self.token_name_label.setStyleSheet(f"color: {text_color};")
        
        # Update holding frame
        self.holding_frame.setStyleSheet(f"background-color: {bg_color};")
        for child in self.holding_frame.findChildren(QLabel):
            child.setStyleSheet(f"color: {text_color};")
        
        # Update holding entry input
        if hasattr(self, 'holding_entry'):
            self.holding_entry.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {card_bg};
                    color: {text_color};
                    border: 1px solid {border_color};
                    border-radius: 4px;
                    padding: 4px;
                }}
            """)
        
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
        
        # Update DIEM token components
        self.diem_token_name_label.setStyleSheet(f"color: {text_color};")
        
        # Update DIEM holding frame
        self.diem_holding_frame.setStyleSheet(f"background-color: {bg_color};")
        for child in self.diem_holding_frame.findChildren(QLabel):
            child.setStyleSheet(f"color: {text_color};")
        
        # Update DIEM holding entry input
        if hasattr(self, 'diem_holding_entry'):
            self.diem_holding_entry.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {card_bg};
                    color: {text_color};
                    border: 1px solid {border_color};
                    border-radius: 4px;
                    padding: 4px;
                }}
            """)
        
        # Update DIEM price frames
        self.diem_prices_frame.setStyleSheet(f"background-color: {bg_color};")
        for group in [self.diem_usd_group, self.diem_aud_group]:
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
        
        # Update DIEM status label
        self.diem_price_status_label.setStyleSheet(f"color: {text_color};")
        
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
        
        # Update models tab display frame background
        if hasattr(self, 'display_frame'):
            self.display_frame.setStyleSheet(f"background-color: {bg_color};")
    
    def toggle_theme(self, theme_name):
        """Toggle between dark and light themes using signal-based updates."""
        new_mode = 'dark' if theme_name == "Dark" else 'light'
        self.theme.set_mode(new_mode)
        
        # Apply global palette to application
        self.theme.apply_palette(QApplication.instance())
        
        # Apply global stylesheet to main window for consistent backgrounds
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {self.theme.background};
                color: {self.theme.text};
            }}
        """)
        
        # Trigger local UI updates
        self._apply_theme()
        
        # Update validation state display
        self.price_display_usd.set_validation_state(self.validation_state.value)
        self.price_display_aud.set_validation_state(self.validation_state.value)
        self.price_display_diem_usd.set_validation_state(self.diem_validation_state.value)
        self.price_display_diem_aud.set_validation_state(self.diem_validation_state.value)
    
    def _on_theme_changed(self, new_mode):
        """Handle theme change signal from Theme class.
        
        This method is called whenever theme.set_mode() is invoked,
        providing automatic theme propagation to all connected widgets.
        
        Args:
            new_mode: 'dark' or 'light'
        """
        # Update price display widgets
        for widget in [self.price_display_usd, self.price_display_aud, 
                       self.price_display_diem_usd, self.price_display_diem_aud]:
            if hasattr(widget, 'update_theme'):
                widget.update_theme(self.theme)
            else:
                widget.theme = self.theme
        
        # Update balance display widget
        if hasattr(self, 'balance_display') and self.balance_display:
            if hasattr(self.balance_display, 'set_theme_colors'):
                self.balance_display.set_theme_colors(self.theme.theme_colors)
        
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
        
        # Update leaderboard theme and delegates
        if hasattr(self, 'leaderboard_widget') and self.leaderboard_widget:
            self.leaderboard_widget.theme_colors = self.theme.theme_colors
            self.leaderboard_widget.theme = self.theme
            # Update delegates with new theme
            if hasattr(self.leaderboard_widget, 'bar_delegate_7day'):
                self.leaderboard_widget.bar_delegate_7day.theme = self.theme
            if hasattr(self.leaderboard_widget, 'bar_delegate_daily'):
                self.leaderboard_widget.bar_delegate_daily.theme = self.theme
            self.leaderboard_widget.apply_theme()
        
        # Update cost optimizer widget theme
        if hasattr(self, 'cost_optimizer_widget') and self.cost_optimizer_widget:
            self.cost_optimizer_widget.theme = self.theme
            self.cost_optimizer_widget._apply_theme()
        
        # Update all dynamically created API key widgets
        if hasattr(self, 'api_key_widgets'):
            for widget in self.api_key_widgets:
                if hasattr(widget, 'set_theme_colors'):
                    widget.set_theme_colors(self.theme.theme_colors)
        
        # Update model comparison widget theme and redraw charts
        if hasattr(self, 'model_comparison_widget') and self.model_comparison_widget:
            self.model_comparison_widget.update_theme(self.theme)
        
        # Re-display models if they're currently shown to update theme
        if hasattr(self, 'models_data') and self.models_data and hasattr(self, 'display_layout'):
            # Check if there are currently displayed models
            if self.display_layout.count() > 0:
                # Re-run display to update all model cards with new theme
                self.display_filtered_models()
        
        logger.debug(f"Theme changed to {new_mode} mode via signal")
    
    def _create_cost_optimization_tab(self):
        """Create the Cost Optimization & Analytics tab"""
        self.cost_optimization_tab = QWidget()
        cost_tab_layout = QVBoxLayout(self.cost_optimization_tab)
        cost_tab_layout.setContentsMargins(5, 5, 5, 5)
        cost_tab_layout.setSpacing(10)
        
        # Create cost optimization widget with model cache
        self.cost_optimizer_widget = CostOptimizationWidget(self.theme, model_cache=self.model_cache, parent=self)
        self.cost_optimizer_widget.refresh_requested.connect(self._refresh_cost_analysis)
        cost_tab_layout.addWidget(self.cost_optimizer_widget)
        
        # Add tab to main tabs
        self.main_tabs.addTab(self.cost_optimization_tab, "💰 Cost Optimization")
        
        logger.debug("Cost optimization tab created successfully")
    
    def _refresh_cost_analysis(self):
        """Refresh cost optimization analysis via worker thread (non-blocking)."""
        try:
            # Clean up any existing worker before creating a new one
            if hasattr(self, 'cost_analysis_worker') and self.cost_analysis_worker is not None:
                try:
                    from shiboken6 import isValid
                    if not isValid(self.cost_analysis_worker):
                        self.cost_analysis_worker = None
                    else:
                        if self.cost_analysis_worker.isRunning():
                            self.cost_analysis_worker.quit()
                            self.cost_analysis_worker.wait(2000)
                        try:
                            self.cost_analysis_worker.billing_data_ready.disconnect()
                            self.cost_analysis_worker.error_occurred.disconnect()
                            self.cost_analysis_worker.status_update.disconnect()
                        except (RuntimeError, TypeError):
                            pass
                        self.cost_analysis_worker = None
                except Exception:
                    self.cost_analysis_worker = None
            
            # Create and start the cost analysis worker
            self.cost_analysis_worker = CostAnalysisWorker(
                admin_key=Config.VENICE_ADMIN_KEY,
                analysis_days=7,
                parent=self
            )
            self.cost_analysis_worker.billing_data_ready.connect(self._handle_billing_data_ready)
            self.cost_analysis_worker.error_occurred.connect(self._handle_cost_analysis_error)
            self.cost_analysis_worker.status_update.connect(self._handle_cost_analysis_status)
            self.cost_analysis_worker.finished.connect(self.cost_analysis_worker.deleteLater)
            self.cost_analysis_worker.start()
            
            logger.debug("Cost analysis worker started")
            
        except Exception as e:
            logger.error(f"Failed to start cost analysis: {type(e).__name__}: {e}")
    
    def _handle_billing_data_ready(self, billing_data: list, api_keys_data: list, analysis_days: int):
        """Handle billing data received from worker thread."""
        if billing_data:
            self.cost_optimizer_widget.update_analysis(billing_data, api_keys_data, analysis_days)
            logger.info(f"Cost analysis updated with {len(billing_data)} billing records")
        else:
            logger.warning("No billing data available for cost analysis")
    
    def _handle_cost_analysis_error(self, error_msg: str):
        """Handle cost analysis error from worker thread."""
        logger.error(f"Cost analysis error: {error_msg}")
        # Could update UI to show error state if needed
    
    def _handle_cost_analysis_status(self, status_msg: str):
        """Handle status updates from cost analysis worker."""
        logger.debug(f"Cost analysis: {status_msg}")
    
    def _start_price_worker(self):
        """Start the price worker thread to fetch CoinGecko prices."""
        # Prevent duplicate scheduling and check if already running
        if self._price_update_scheduled:
            logger.debug("Price update already scheduled, skipping duplicate")
            return
        
        # Check if worker is already running
        if hasattr(self, 'price_worker') and self.price_worker and self.price_worker.isRunning():
            logger.debug("Price worker already running, skipping duplicate start")
            return
        
        # Update status bar
        self.status_bar.set_process_running(
            self.status_bar.PROCESS_PRICES,
            "Fetching Venice prices..."
        )
        
        # Clean up any existing worker before creating a new one
        if hasattr(self, 'price_worker') and self.price_worker is not None:
            # Check if C++ object still exists
            try:
                from shiboken6 import isValid
                if not isValid(self.price_worker):
                    self.price_worker = None
                else:
                    if self.price_worker.isRunning():
                        self.price_worker.quit()
                        self.price_worker.wait(2000)
                    try:
                        self.price_worker.price_updated.disconnect()
                        self.price_worker.error_occurred.disconnect()
                    except (RuntimeError, TypeError):
                        pass
                    self.price_worker = None
            except Exception:
                self.price_worker = None
        
        # Create and configure worker
        self.price_worker = PriceWorker(
            token_id=Config.COINGECKO_TOKEN_ID,
            currencies=Config.COINGECKO_CURRENCIES,
            parent=self
        )
        self.price_worker.price_updated.connect(self._handle_price_update)
        self.price_worker.error_occurred.connect(self._handle_price_error)
        self.price_worker.finished.connect(self.price_worker.deleteLater)
        self._price_update_scheduled = True
        self.price_worker.start()
    
    def _handle_price_update(self, price_data: dict):
        """Handle price data received from worker thread."""
        # Clear the scheduling guard
        self._price_update_scheduled = False
        
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
                status_messages.append(f"{currency.upper()}: N/A")
        
        if failed_currencies:
            status_str = f"Partial update: {', '.join(status_messages)} | {time.strftime('%H:%M:%S')}"
            status_color = self.theme.warning if hasattr(self.theme, 'warning') else self.theme.error
        else:
            status_str = f"Prices: {', '.join(status_messages)} | {time.strftime('%H:%M:%S')}"
            status_color = self.theme.text
        
        self.price_status_label.setText(status_str)
        self.price_status_label.setStyleSheet(f"color: {status_color};")
        
        # Update status bar
        if failed_currencies:
            self.status_bar.set_process_warning(
                self.status_bar.PROCESS_PRICES,
                f"Partial: {', '.join(status_messages)}"
            )
        else:
            self.status_bar.set_process_success(
                self.status_bar.PROCESS_PRICES,
                f"Updated: {', '.join(status_messages)}"
            )
        
        # Update price displays
        self._update_price_display()
        
        # Schedule next update only if not already scheduled
        if not self._price_update_scheduled:
            QTimer.singleShot(Config.COINGECKO_REFRESH_INTERVAL_MS, self._start_price_worker)
    
    def _handle_price_error(self, error_msg: str):
        """Handle price fetch error from worker thread."""
        # Clear the scheduling guard
        self._price_update_scheduled = False
        
        logger.error(f"Price fetch error: {error_msg}")
        self.price_status_label.setText(f"Price update failed | {time.strftime('%H:%M:%S')}")
        self.price_status_label.setStyleSheet(f"color: {self.theme.error};")
        
        # Update status bar
        self.status_bar.set_process_error(self.status_bar.PROCESS_PRICES, "Price fetch failed")
        
        # Schedule retry only if not already scheduled
        if not self._price_update_scheduled:
            QTimer.singleShot(Config.COINGECKO_REFRESH_INTERVAL_MS, self._start_price_worker)
    
    def update_price_label(self):
        """Start price update via worker thread (non-blocking)."""
        self._start_price_worker()
    
    def _start_diem_price_worker(self):
        """Start the DIEM price worker thread to fetch CoinGecko prices."""
        # Clean up any existing worker before creating a new one
        if hasattr(self, 'diem_price_worker') and self.diem_price_worker is not None:
            # Check if C++ object still exists
            try:
                from shiboken6 import isValid
                if not isValid(self.diem_price_worker):
                    self.diem_price_worker = None
                else:
                    if self.diem_price_worker.isRunning():
                        self.diem_price_worker.quit()
                        self.diem_price_worker.wait(2000)
                    try:
                        self.diem_price_worker.price_updated.disconnect()
                        self.diem_price_worker.error_occurred.disconnect()
                    except (RuntimeError, TypeError):
                        pass
                    self.diem_price_worker = None
            except Exception:
                self.diem_price_worker = None
        
        # Create and configure worker
        self.diem_price_worker = PriceWorker(
            token_id=Config.DIEM_TOKEN_ID,
            currencies=Config.COINGECKO_CURRENCIES,
            parent=self
        )
        self.diem_price_worker.price_updated.connect(self._handle_diem_price_update)
        self.diem_price_worker.error_occurred.connect(self._handle_diem_price_error)
        self.diem_price_worker.finished.connect(self.diem_price_worker.deleteLater)
        self.diem_price_worker.start()
    
    def _handle_diem_price_update(self, price_data: dict):
        """Handle DIEM price data received from worker thread."""
        status_messages = []
        failed_currencies = []
        
        for currency in Config.COINGECKO_CURRENCIES:
            if currency in price_data:
                self.diem_price_data[currency]['price'] = price_data[currency]
                self.diem_price_data[currency]['total'] = price_data[currency] * self.diem_holding_amount
                
                price_str = format_currency(price_data[currency], currency)
                status_messages.append(f"{currency.upper()}: {price_str}")
            else:
                failed_currencies.append(currency)
                status_messages.append(f"{currency.upper()}: N/A")
        
        if failed_currencies:
            status_str = f"Partial update: {', '.join(status_messages)} | {time.strftime('%H:%M:%S')}"
            status_color = self.theme.warning if hasattr(self.theme, 'warning') else self.theme.error
        else:
            status_str = f"Prices: {', '.join(status_messages)} | {time.strftime('%H:%M:%S')}"
            status_color = self.theme.text
        
        self.diem_price_status_label.setText(status_str)
        self.diem_price_status_label.setStyleSheet(f"color: {status_color};")
        
        # Update price displays
        self._update_diem_price_display()
        
        # Schedule next update
        QTimer.singleShot(Config.COINGECKO_REFRESH_INTERVAL_MS, self._start_diem_price_worker)
    
    def _handle_diem_price_error(self, error_msg: str):
        """Handle DIEM price fetch error from worker thread."""
        logger.error(f"DIEM price fetch error: {error_msg}")
        self.diem_price_status_label.setText(f"Price update failed | {time.strftime('%H:%M:%S')}")
        self.diem_price_status_label.setStyleSheet(f"color: {self.theme.error};")
        
        # Schedule retry
        QTimer.singleShot(Config.COINGECKO_REFRESH_INTERVAL_MS, self._start_diem_price_worker)
    
    def update_diem_price_label(self):
        """Start DIEM price update via worker thread (non-blocking)."""
        self._start_diem_price_worker()
    
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

            # Update status bar
            self.status_bar.set_process_success(self.status_bar.PROCESS_MODELS, "Connected")
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
            # Update status bar with error
            self.status_bar.set_process_error(self.status_bar.PROCESS_MODELS, "Connection failed")
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
        separator.setStyleSheet(f"color: {self.theme.border};")
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
    
    def _init_models_tabs_from_cache(self):
        """Initialize Models and Compare tabs with cached model data."""
        if not self.models_data:
            logger.warning("No models data available for tab initialization")
            return
        
        logger.info("Populating Models tab from cache...")
        
        # Populate the type combobox with available model types
        self.type_combobox.clear()
        self.type_combobox.blockSignals(True)
        self.type_combobox.addItems(self.model_types)
        self.type_combobox.setCurrentText("all")
        self.type_combobox.blockSignals(False)
        self.type_combobox.setEnabled(True)
        
        # Enable buttons
        self.display_button.setEnabled(True)
        self.view_styles_button.setEnabled(True)
        self.connect_button.setEnabled(True)
        
        # Display the "all" models on startup
        self.display_selected_models_action()
        
        # Update the comparison widget if available
        self.update_model_comparison_data()
    
    def _init_usage_tracking(self):
        """Initialize the usage tracking system."""
        # Create and connect the usage worker - pass self as parent to prevent GC
        self.usage_worker = UsageWorker(Config.VENICE_ADMIN_KEY, parent=self)
        self.usage_worker.usage_data_updated.connect(self._update_usage_display)
        self.usage_worker.balance_data_updated.connect(self._update_balance_display)
        self.usage_worker.daily_usage_updated.connect(self._update_daily_usage_display)
        self.usage_worker.error_occurred.connect(self._handle_usage_error)
        
        # Initialize web usage worker for unified leaderboard - pass self as parent
        self.web_usage_worker = WebUsageWorker(Config.VENICE_ADMIN_KEY, parent=self)
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
                    exchange_rate = rate_data.rate if rate_data else Config.DEFAULT_EXCHANGE_RATE
                except Exception as e:
                    logger.warning(f"Failed to get exchange rate: {e}")
                    exchange_rate = Config.DEFAULT_EXCHANGE_RATE
            else:
                exchange_rate = Config.DEFAULT_EXCHANGE_RATE
            
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
    
    def _on_clear_status_errors(self):
        """Handle clear errors request from status bar."""
        # Clear all error statuses in the status bar
        self.status_bar.clear_all_errors()
        
        # Reset models process to idle if it was in error
        current_status = self.status_bar.get_process_status(self.status_bar.PROCESS_MODELS)
        if current_status and current_status.status.value == "error":
            self.status_bar.set_process_idle(self.status_bar.PROCESS_MODELS)
    
    def _handle_usage_error(self, error_msg: str):
        """Handle errors from the usage worker."""
        logger.info(f"Usage tracking error: {error_msg}")
        
        # Update status bar
        self.status_bar.set_process_error(self.status_bar.PROCESS_USAGE, error_msg)
        self.status_bar.showMessage(f"Usage tracking error: {error_msg}")
        
        # Show error message if this is the first error or if it's different from the last one
        if not hasattr(self, '_last_usage_error') or self._last_usage_error != error_msg:
            QMessageBox.critical(self, "Usage Tracking Error", error_msg)
            self._last_usage_error = error_msg
    
    def _handle_video_quote_error(self, error_msg: str):
        """Handle errors from the video quote worker."""
        logger.error(f"Video quote error: {error_msg}")
        # For now, just log the error since video quotes are background operations
        # Could add a status indicator later if needed
    
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
                    border: 1px solid {self.theme.border};
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
        self.leaderboard_widget = UsageLeaderboardWidget(self.theme.theme_colors, theme=self.theme)
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
            
            # Start video quote worker to get base prices
            self._start_video_quote_worker()
        
        # Also update cost optimizer widget with dynamic model data
        if hasattr(self, 'cost_optimizer_widget') and self.cost_optimizer_widget:
            self.cost_optimizer_widget.update_models_data(self.models_data)

    def _start_video_quote_worker(self):
        """Start worker to fetch video base prices"""
        if not self.models_data or not hasattr(self, 'model_comparison_widget'):
            return
        
        # Get video models from the data
        video_models = [model for model in self.models_data.get('data', []) if model.get('type') == 'video']
        
        if not video_models:
            return
        
        # Update status bar - set to running
        self.status_bar.set_process_running(
            self.status_bar.PROCESS_VIDEO_QUOTES,
            f"Fetching {len(video_models)} video quotes..."
        )
        
        # Clean up any existing worker
        if hasattr(self, 'video_quote_worker') and self.video_quote_worker and self.video_quote_worker.isRunning():
            self.video_quote_worker.stop()
            self.video_quote_worker.wait()
        
        # Create and start new worker
        from src.core.video_quote_worker import VideoQuoteWorker
        self.video_quote_worker = VideoQuoteWorker(self.api_client, video_models)
        self.video_quote_worker.video_base_prices_updated.connect(self._handle_video_quotes_updated)
        self.video_quote_worker.progress_updated.connect(self._handle_video_quote_progress)
        self.video_quote_worker.error_occurred.connect(self._handle_video_quote_error)
        self.video_quote_worker.start()
    
    def _handle_video_quotes_updated(self, prices):
        """Handle video quotes updated - mark as success"""
        # Also update the comparison widget
        if hasattr(self, 'model_comparison_widget'):
            self.model_comparison_widget.update_video_base_prices(prices)
        
        self.status_bar.set_process_success(
            self.status_bar.PROCESS_VIDEO_QUOTES,
            f"Got {len(prices)} quotes"
        )
    
    def _handle_video_quote_progress(self, message):
        """Handle video quote progress updates"""
        self.status_bar.set_process_running(
            self.status_bar.PROCESS_VIDEO_QUOTES,
            message
        )

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
        logger.info("Close event triggered, cleaning up...")

        try:
            # Phase 2: Stop exchange rate service
            if hasattr(self, 'exchange_rate_service') and self.exchange_rate_service:
                logger.debug("Stopping exchange rate service...")
                self.exchange_rate_service.stop_automatic_updates()
            
            # Stop all timers
            for timer in self.findChildren(QTimer):
                if timer.isActive():
                    timer.stop()

            # Clean up threads - this may take some time
            self._cleanup_threads()

            # Clean up model comparison widget if it exists
            if hasattr(self, 'model_comparison_widget') and self.model_comparison_widget:
                if hasattr(self.model_comparison_widget, 'analytics_worker'):
                    if self.model_comparison_widget.analytics_worker and self.model_comparison_widget.analytics_worker.isRunning():
                        self.model_comparison_widget.analytics_worker.quit()
                        self.model_comparison_widget.analytics_worker.wait(5000)

            logger.info("Cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

        # Now allow the window to close
        event.accept()

    def _cleanup_threads(self):
        """Clean up all active threads to prevent crashes"""
        logger.debug("Cleaning up threads...")

        # Clean up API worker
        if hasattr(self, 'api_worker') and self.api_worker and self.api_worker.isRunning():
            logger.debug("Waiting for API worker to finish...")
            self.api_worker.wait(5000)

        # Clean up style worker
        if hasattr(self, 'style_worker') and self.style_worker and self.style_worker.isRunning():
            logger.debug("Waiting for style worker to finish...")
            self.style_worker.wait(5000)

        # Clean up traits worker
        if hasattr(self, 'traits_worker') and self.traits_worker and self.traits_worker.isRunning():
            logger.debug("Waiting for traits worker to finish...")
            self.traits_worker.wait(5000)

        # Clean up usage worker
        if self.usage_worker and self.usage_worker.isRunning():
            logger.debug("Stopping usage worker...")
            self.usage_worker.stop()
            self.usage_worker.wait(5000)

        # Clean up web usage worker
        if self.web_usage_worker and self.web_usage_worker.isRunning():
            logger.debug("Stopping web usage worker...")
            self.web_usage_worker.stop()
            self.web_usage_worker.wait(5000)

        # Clean up price worker
        if hasattr(self, 'price_worker') and self.price_worker and self.price_worker.isRunning():
            logger.debug("Stopping price worker...")
            self.price_worker.stop()
            self.price_worker.wait(5000)

        # Clean up DIEM price worker
        if hasattr(self, 'diem_price_worker') and self.diem_price_worker and self.diem_price_worker.isRunning():
            logger.debug("Stopping DIEM price worker...")
            self.diem_price_worker.stop()
            self.diem_price_worker.wait(5000)

        # Clean up cost analysis worker
        if hasattr(self, 'cost_analysis_worker') and self.cost_analysis_worker and self.cost_analysis_worker.isRunning():
            logger.debug("Stopping cost analysis worker...")
            self.cost_analysis_worker.stop()
            self.cost_analysis_worker.wait(5000)

        # Clean up video quote worker
        if hasattr(self, 'video_quote_worker') and self.video_quote_worker and self.video_quote_worker.isRunning():
            logger.debug("Stopping video quote worker...")
            self.video_quote_worker.stop()
            self.video_quote_worker.wait(5000)

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
            getattr(self.exchange_rate_service.current_rate, 'rate', Config.DEFAULT_EXCHANGE_RATE) if self.exchange_rate_service.current_rate else Config.DEFAULT_EXCHANGE_RATE
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
                    Config.DEFAULT_EXCHANGE_RATE  # Fallback rate
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
