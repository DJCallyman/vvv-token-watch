import sys
import json
import threading
import traceback
import time
import queue
from datetime import datetime
from typing import Dict, Any, Optional
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

# Add the project directory to Python path
sys.path.insert(0, '/Users/djcal/GIT/assorted-code')

# Import local modules using absolute imports
from vvv_token_watch.currency_utils import format_currency
from vvv_token_watch.config import Config

# --- Suppress Warnings (Use with caution) ---
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

# --- Error Logging Configuration ---
logging.basicConfig(
    filename='vvv_token_watch/error_log.txt',
    level=logging.ERROR,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Color Constants ---
COLOR_BOOL_YES = "#00FF00"
COLOR_BOOL_NO = "#FF0000"
COLOR_PRICE_LABEL = "#FFFFFF"
COLOR_STATUS_LABEL = "#AAAAAA"
COLOR_ERROR_LABEL = "#FF6B6B"
COLOR_BACKGROUND = "#2E2E2E"
COLOR_FRAME_BACKGROUND = "#3C3C3C"

class WorkerSignals(QObject):
    """Signals for worker threads to communicate with main thread"""
    result = Signal(dict)

class APIWorker(QThread):
    """Worker thread for API calls"""
    def __init__(self, url: str, headers: Dict[str, str], params: Optional[Dict] = None):
        super().__init__()
        self.url = url
        self.headers = headers
        self.params = params
        self.signals = WorkerSignals()

    def run(self):
        """Execute the API request in a separate thread"""
        result = {'success': False, 'data': None, 'error': None}
        try:
            response = requests.get(self.url, headers=self.headers, params=self.params, timeout=20)
            response.raise_for_status()
            data = response.json()
            if data and 'data' in data:
                result['success'] = True
                result['data'] = data
            else:
                result['error'] = "API response missing 'data' key or is empty."
                logging.error(result['error'])
        except requests.exceptions.RequestException as e:
            result['error'] = f"API Connection Error: {e}"
            logging.error(result['error'])
        
        self.signals.result.emit(result)

class StylePresetWorker(QThread):
    """Worker thread for fetching style presets"""
    def __init__(self, url: str, headers: Dict[str, str]):
        super().__init__()
        self.url = url
        self.headers = headers
        self.signals = WorkerSignals()

    def run(self):
        """Fetch style presets in a separate thread"""
        result = {'success': False, 'data': [], 'error': None}
        try:
            response = requests.get(self.url, headers=self.headers, timeout=20)
            response.raise_for_status()
            style_presets = response.json()
            if style_presets and 'data' in style_presets:
                result['success'] = True
                result['data'] = style_presets['data']
        except requests.exceptions.RequestException as e:
            result['error'] = f"Style Preset API Error: {e}"
            logging.error(result['error'])

        self.signals.result.emit(result)

class CombinedViewerApp(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        print("DEBUG: Initializing CombinedViewerApp...")
        
        # Validate configuration before starting
        is_valid, error_msg = Config.validate()
        if not is_valid:
            QMessageBox.critical(self, "Configuration Error", error_msg)
            sys.exit(1)
            
        self.setWindowTitle("Venice AI Models & CoinGecko Price Viewer")
        self.setMinimumSize(850, 750)
        
        self.models_data = None
        self.model_types = ["all"]
        self.price_data = {
            'usd': {'price': None, 'total': None},
            'aud': {'price': None, 'total': None}
        }
        self.holding_amount = Config.COINGECKO_HOLDING_AMOUNT
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Click 'Connect' for models. Price updates automatically.")
        
        # Create splitter for price and model sections
        self.main_splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(self.main_splitter)
        
        # Create price display section
        self._create_price_display()
        
        # Create model viewer section
        self._create_model_viewer()
        
        # Set initial splitter sizes to match original proportions
        self.main_splitter.setSizes([250, self.height() - 250])
        
        # Initialize holding entry with proper value format after it's created
        self.holding_entry.setText(str(int(Config.COINGECKO_HOLDING_AMOUNT)) if Config.COINGECKO_HOLDING_AMOUNT.is_integer() else f"{Config.COINGECKO_HOLDING_AMOUNT:.2f}")
        
        # Initial actions
        QTimer.singleShot(Config.COINGECKO_INITIAL_DELAY_MS, self.update_price_label)
        
        print("DEBUG: CombinedViewerApp initialization complete.")
    
    def _create_price_display(self):
        """Creates the CoinGecko price display widgets."""
        price_widget = QWidget()
        price_widget.setObjectName("price_widget")
        price_widget.setStyleSheet(f"background-color: {COLOR_BACKGROUND};")
        price_layout = QVBoxLayout(price_widget)
        price_layout.setSpacing(10)
        price_layout.setContentsMargins(10, 10, 10, 10)
        
        # Token name
        token_name_text = Config.COINGECKO_TOKEN_ID.replace('-', ' ').capitalize()
        self.token_name_label = QLabel(token_name_text)
        self.token_name_label.setObjectName("token_name_label")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.token_name_label.setFont(font)
        self.token_name_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
        self.token_name_label.setAlignment(Qt.AlignCenter)
        price_layout.addWidget(self.token_name_label)
        
        # Holding amount
        holding_frame = QFrame()
        holding_frame.setObjectName("holding_frame")
        holding_frame.setStyleSheet(f"background-color: {COLOR_BACKGROUND};")
        holding_layout = QHBoxLayout(holding_frame)
        holding_layout.setContentsMargins(0, 0, 0, 0)
        
        holding_label = QLabel("Holding Amount:")
        holding_label.setObjectName("holding_label")
        holding_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
        holding_layout.addWidget(holding_label)
        
        self.holding_var = ""
        self.holding_entry = QLineEdit(str(Config.COINGECKO_HOLDING_AMOUNT))
        self.holding_entry.setObjectName("holding_entry")
        self.holding_entry.setFixedWidth(80)
        self.holding_entry.setStyleSheet("border: 1px solid #555555; border-radius: 3px; padding: 2px;")
        self.holding_entry.textChanged.connect(self._on_holding_text_changed)
        self.holding_entry.editingFinished.connect(self.update_holding_amount)
        self.holding_entry.setValidator(QDoubleValidator(0.0, 1000000.0, 2))
        holding_layout.addWidget(self.holding_entry)
        
        token_label = QLabel("tokens")
        token_label.setObjectName("token_label")
        token_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
        holding_layout.addWidget(token_label)
        
        price_layout.addWidget(holding_frame, alignment=Qt.AlignCenter)
        
        # Loading indicator
        self.loading_var = ""
        self.loading_label = QLabel("")
        self.loading_label.setObjectName("loading_label")
        self.loading_label.setStyleSheet(f"color: {COLOR_STATUS_LABEL};")
        self.loading_label.setAlignment(Qt.AlignCenter)
        price_layout.addWidget(self.loading_label)
        
        # Price frames
        prices_frame = QFrame()
        prices_frame.setObjectName("prices_frame")
        prices_frame.setStyleSheet(f"background-color: {COLOR_BACKGROUND};")
        prices_layout = QHBoxLayout(prices_frame)
        prices_layout.setSpacing(10)
        
        # USD Frame
        usd_frame = QGroupBox(" USD ")
        usd_frame.setObjectName("usd_frame")
        usd_frame.setStyleSheet(f"""
            QGroupBox {{
                background-color: {COLOR_BACKGROUND};
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
                color: {COLOR_PRICE_LABEL};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                background-color: {COLOR_BACKGROUND};
            }}
        """)
        usd_layout = QVBoxLayout(usd_frame)
        
        price_font = QFont()
        price_font.setPointSize(28)
        price_font.setBold(True)
        
        self.usd_price_label = QLabel("Loading...")
        self.usd_price_label.setObjectName("usd_price_label")
        self.usd_price_label.setFont(price_font)
        self.usd_price_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
        self.usd_price_label.setAlignment(Qt.AlignCenter)
        usd_layout.addWidget(self.usd_price_label)
        
        holding_font = QFont()
        holding_font.setPointSize(14)
        
        self.usd_holding_label = QLabel("Holding: Calculating...")
        self.usd_holding_label.setObjectName("usd_holding_label")
        self.usd_holding_label.setFont(holding_font)
        self.usd_holding_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
        self.usd_holding_label.setAlignment(Qt.AlignCenter)
        usd_layout.addWidget(self.usd_holding_label)
        
        prices_layout.addWidget(usd_frame)
        
        # AUD Frame
        aud_frame = QGroupBox(" AUD ")
        aud_frame.setObjectName("aud_frame")
        aud_frame.setStyleSheet(f"""
            QGroupBox {{
                background-color: {COLOR_BACKGROUND};
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
                color: {COLOR_PRICE_LABEL};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                background-color: {COLOR_BACKGROUND};
            }}
        """)
        aud_layout = QVBoxLayout(aud_frame)
        
        self.aud_price_label = QLabel("Loading...")
        self.aud_price_label.setObjectName("aud_price_label")
        self.aud_price_label.setFont(price_font)
        self.aud_price_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
        self.aud_price_label.setAlignment(Qt.AlignCenter)
        aud_layout.addWidget(self.aud_price_label)
        
        self.aud_holding_label = QLabel("Holding: Calculating...")
        self.aud_holding_label.setObjectName("aud_holding_label")
        self.aud_holding_label.setFont(holding_font)
        self.aud_holding_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
        self.aud_holding_label.setAlignment(Qt.AlignCenter)
        aud_layout.addWidget(self.aud_holding_label)
        
        prices_layout.addWidget(aud_frame)
        
        price_layout.addWidget(prices_frame)
        
        # Price status
        self.price_status_label = QLabel("Initializing...")
        self.price_status_label.setObjectName("price_status_label")
        self.price_status_label.setStyleSheet(f"color: {COLOR_STATUS_LABEL};")
        self.price_status_label.setAlignment(Qt.AlignCenter)
        price_layout.addWidget(self.price_status_label)
        
        # Add to splitter
        self.main_splitter.addWidget(price_widget)
        self.main_splitter.setSizes([250, self.height() - 250])
    
    def _on_holding_text_changed(self, text):
        """Handle text changes in the holding entry"""
        self.holding_var = text
    
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
            
            # Update USD display
            if self.price_data['usd']['price'] is not None:
                self.usd_price_label.setText(format_currency(self.price_data['usd']['price'], 'usd'))
                self.usd_price_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
                self.usd_holding_label.setText(f"Holding: {format_currency(self.price_data['usd']['total'], 'usd')}")
                self.usd_holding_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
            else:
                self.usd_price_label.setText("Loading...")
                self.usd_holding_label.setText("Holding: Calculating...")
            
            # Update AUD display
            if self.price_data['aud']['price'] is not None:
                self.aud_price_label.setText(format_currency(self.price_data['aud']['price'], 'aud'))
                self.aud_price_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
                self.aud_holding_label.setText(f"Holding: {format_currency(self.price_data['aud']['total'], 'aud')}")
                self.aud_holding_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
            else:
                self.aud_price_label.setText("Loading...")
                self.aud_holding_label.setText("Holding: Calculating...")
            
            # Update status
            self.price_status_label.setText(f"Holding amount updated to {new_amount:.2f}. Price updates automatically.")
            self.price_status_label.setStyleSheet(f"color: {COLOR_STATUS_LABEL};")
            
        except ValueError:
            self.holding_entry.setText(str(int(self.holding_amount)) if self.holding_amount.is_integer() else f"{self.holding_amount:.2f}")
            self.price_status_label.setText("Invalid holding amount. Must be a positive number.")
            self.price_status_label.setStyleSheet(f"color: {COLOR_ERROR_LABEL};")
            # Ensure price display is updated with current valid holding amount
            self._update_price_display()
    
    def _update_price_display(self):
        """Update price display based on current price_data and holding_amount"""
        # Update USD display
        if self.price_data['usd']['price'] is not None:
            self.usd_price_label.setText(format_currency(self.price_data['usd']['price'], 'usd'))
            self.usd_price_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
            self.usd_holding_label.setText(f"Holding: {format_currency(self.price_data['usd']['total'], 'usd')}")
            self.usd_holding_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
        else:
            self.usd_price_label.setText("Loading...")
            self.usd_holding_label.setText("Holding: Calculating...")
        
        # Update AUD display
        if self.price_data['aud']['price'] is not None:
            self.aud_price_label.setText(format_currency(self.price_data['aud']['price'], 'aud'))
            self.aud_price_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
            self.aud_holding_label.setText(f"Holding: {format_currency(self.price_data['aud']['total'], 'aud')}")
            self.aud_holding_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
        else:
            self.aud_price_label.setText("Loading...")
            self.aud_holding_label.setText("Holding: Calculating...")
    
    def _create_model_viewer(self):
        """Creates the Venice AI model viewer widgets with proper scrolling."""
        model_widget = QWidget()
        model_widget.setObjectName("model_widget")
        model_widget.setStyleSheet(f"background-color: {COLOR_BACKGROUND};")
        model_layout = QVBoxLayout(model_widget)
        model_layout.setContentsMargins(10, 10, 10, 10)
        
        # Control frame
        control_frame = QFrame()
        control_frame.setObjectName("control_frame")
        control_frame.setStyleSheet(f"background-color: {COLOR_BACKGROUND};")
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(5, 5, 5, 5)
        
        self.connect_button = QPushButton("Connect Models")
        self.connect_button.setObjectName("connect_button")
        self.connect_button.clicked.connect(self.connect_thread)
        control_layout.addWidget(self.connect_button)
        
        type_label = QLabel("Filter by Type:")
        type_label.setObjectName("type_label")
        type_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
        control_layout.addWidget(type_label)
        
        self.model_type_var = "all"
        self.type_combobox = QComboBox()
        self.type_combobox.setObjectName("type_combobox")
        self.type_combobox.addItems(self.model_types)
        self.type_combobox.setCurrentText("all")
        self.type_combobox.currentTextChanged.connect(self._on_type_changed)
        self.type_combobox.setEnabled(False)
        control_layout.addWidget(self.type_combobox)
        
        self.display_button = QPushButton("Display Models")
        self.display_button.setObjectName("display_button")
        self.display_button.clicked.connect(self.display_selected_models_action)
        self.display_button.setEnabled(False)
        control_layout.addWidget(self.display_button)
        
        self.view_styles_button = QPushButton("View Style Presets")
        self.view_styles_button.setObjectName("view_styles_button")
        self.view_styles_button.clicked.connect(self.view_style_presets_action)
        self.view_styles_button.setEnabled(False)
        control_layout.addWidget(self.view_styles_button)
        
        model_layout.addWidget(control_frame)
        
        # Scroll area for model display
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("scroll_area")
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLOR_FRAME_BACKGROUND};
                border: 1px solid #555555;
                border-radius: 5px;
            }}
            QScrollBar:vertical {{
                background: #2E2E2E;
                width: 15px;
                border-radius: 7px;
            }}
            QScrollBar::handle:vertical {{
                background: #555555;
                min-height: 20px;
                border-radius: 7px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #777777;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.display_frame = QWidget()
        self.display_frame.setObjectName("display_frame")
        self.display_frame.setStyleSheet(f"background-color: {COLOR_FRAME_BACKGROUND};")
        self.display_layout = QVBoxLayout(self.display_frame)
        self.display_layout.setSpacing(10)
        self.display_layout.setContentsMargins(5, 5, 5, 5)
        
        self.scroll_area.setWidget(self.display_frame)
        model_layout.addWidget(self.scroll_area)
        
        # Add to splitter
        self.main_splitter.addWidget(model_widget)
        self.main_splitter.setSizes([250, self.height() - 250])
    
    def _on_type_changed(self, text):
        """Handle type combobox changes"""
        self.model_type_var = text
    
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
                response = requests.get(url, params=params, timeout=15)
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
                print(error_msg)
                logging.error(error_msg)
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return None
    
    def update_price_label(self):
        """Updates price display for all configured currencies."""
        self.loading_label.setText("Updating prices...")
        
        price_data = self.get_coingecko_price()
        
        if price_data:
            status_messages = []
            failed_currencies = []
            
            for currency in Config.COINGECKO_CURRENCIES:
                if currency in price_data:
                    self.price_data[currency]['price'] = price_data[currency]
                    self.price_data[currency]['total'] = price_data[currency] * self.holding_amount
                    
                    price_str = format_currency(price_data[currency], currency)
                    total_str = format_currency(self.price_data[currency]['total'], currency)
                    
                    if currency == 'usd':
                        self.usd_price_label.setText(price_str)
                        self.usd_price_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
                        self.usd_holding_label.setText(f"Holding: {total_str}")
                        self.usd_holding_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
                    elif currency == 'aud':
                        self.aud_price_label.setText(price_str)
                        self.aud_price_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
                        self.aud_holding_label.setText(f"Holding: {total_str}")
                        self.aud_holding_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
                    
                    status_messages.append(f"{currency.upper()}: {price_str}")
                else:
                    failed_currencies.append(currency)
                    if currency == 'usd':
                        self.usd_price_label.setText("N/A")
                        self.usd_price_label.setStyleSheet(f"color: {COLOR_ERROR_LABEL};")
                        self.usd_holding_label.setText("Holding: N/A")
                        self.usd_holding_label.setStyleSheet(f"color: {COLOR_ERROR_LABEL};")
                    elif currency == 'aud':
                        self.aud_price_label.setText("N/A")
                        self.aud_price_label.setStyleSheet(f"color: {COLOR_ERROR_LABEL};")
                        self.aud_holding_label.setText("Holding: N/A")
                        self.aud_holding_label.setStyleSheet(f"color: {COLOR_ERROR_LABEL};")
                    status_messages.append(f"{currency.upper()}: Error")
            
            if failed_currencies:
                if len(failed_currencies) == len(Config.COINGECKO_CURRENCIES):
                    status_str = "Price Update Error. Retrying..."
                    status_color = COLOR_ERROR_LABEL
                    QMessageBox.warning(self, "Price Update Failed", "Failed to retrieve price data from CoinGecko API. Retrying...")
                else:
                    failed_str = ", ".join([c.upper() for c in failed_currencies])
                    status_str = f"Partial update: {failed_str} failed | {', '.join(status_messages)} | Last updated: {time.strftime('%H:%M:%S')}"
                    status_color = COLOR_ERROR_LABEL
                    QMessageBox.warning(self, "Partial Price Update", f"Failed to retrieve {failed_str} prices. Other prices updated successfully.")
            else:
                status_str = f"Prices updated: {', '.join(status_messages)} | Last updated: {time.strftime('%H:%M:%S')}"
                status_color = COLOR_STATUS_LABEL
            
            self.price_status_label.setText(status_str)
            self.price_status_label.setStyleSheet(f"color: {status_color};")
        else:
            for currency in Config.COINGECKO_CURRENCIES:
                if currency == 'usd':
                    self.usd_price_label.setText("API Error")
                    self.usd_price_label.setStyleSheet(f"color: {COLOR_ERROR_LABEL};")
                    self.usd_holding_label.setText("Holding: N/A")
                    self.usd_holding_label.setStyleSheet(f"color: {COLOR_ERROR_LABEL};")
                elif currency == 'aud':
                    self.aud_price_label.setText("API Error")
                    self.aud_price_label.setStyleSheet(f"color: {COLOR_ERROR_LABEL};")
                    self.aud_holding_label.setText("Holding: N/A")
                    self.aud_holding_label.setStyleSheet(f"color: {COLOR_ERROR_LABEL};")
            
            self.price_status_label.setText("Price Update Error. Retrying...")
            self.price_status_label.setStyleSheet(f"color: {COLOR_ERROR_LABEL};")
            QMessageBox.warning(self, "Price Update Failed", "Failed to connect to CoinGecko API. Retrying...")
        
        self.loading_label.setText("")
        
        QTimer.singleShot(Config.COINGECKO_REFRESH_INTERVAL_MS, self.update_price_label)
    
    def connect_thread(self):
        """Starts the API connection in a separate thread."""
        self.connect_button.setEnabled(False)
        self.display_button.setEnabled(False)
        self.view_styles_button.setEnabled(False)
        self.type_combobox.setEnabled(False)
        self.clear_display_frame()
        self.status_bar.showMessage("Connecting to Venice API...")
        
        # Ensure scroll area is reset
        self.scroll_area.verticalScrollBar().setValue(0)
        
        # Clear layout
        for i in reversed(range(self.display_layout.count())):
            self.display_layout.takeAt(i).widget().deleteLater()
        
        # Add connecting label
        connecting_label = QLabel("Connecting to Venice API...")
        connecting_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
        self.display_layout.addWidget(connecting_label, alignment=Qt.AlignCenter)
        
        # Create and start worker thread
        url = 'https://api.venice.ai/api/v1/models'
        headers = {'Accept': 'application/json', 'Authorization': f'Bearer {Config.VENICE_API_KEY}'}
        params = {'type': 'all'}
        
        self.api_worker = APIWorker(url, headers, params)
        self.api_worker.signals.result.connect(self._update_gui_after_connect)
        self.api_worker.start()
    
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
        fetching_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
        self.display_layout.addWidget(fetching_label, alignment=Qt.AlignCenter)
        
        # Create and start worker thread
        url = 'https://api.venice.ai/api/v1/image/styles'
        headers = {'Accept': 'application/json', 'Authorization': f'Bearer {Config.VENICE_API_KEY}'}
        
        self.style_worker = StylePresetWorker(url, headers)
        self.style_worker.signals.result.connect(self._update_gui_after_fetch_style_presets)
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
            self.type_combobox.setCurrentText("all")
            self.type_combobox.setEnabled(True)
            self.display_button.setEnabled(True)
            self.view_styles_button.setEnabled(True)
            self.status_bar.showMessage("Model API Connected. Select type and 'Display Models'.")
            
            # Add instruction label
            instruction_label = QLabel("Select model type and click 'Display Models'.")
            instruction_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
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
            
            # Add error label
            error_label = QLabel("Model Connection failed.")
            error_label.setStyleSheet(f"color: {COLOR_ERROR_LABEL};")
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
            section_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL}; padding: 10px 0px 1px 0px;")
            self.display_layout.addWidget(section_label)
            
            text_widget = QTextEdit()
            text_widget.setReadOnly(True)
            text_widget.setStyleSheet(f"""
                background-color: {COLOR_FRAME_BACKGROUND};
                color: {COLOR_PRICE_LABEL};
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
        heading.setStyleSheet(f"color: {COLOR_PRICE_LABEL}; padding: 5px 0px 1px 0px;")
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
        key_label.setStyleSheet(f"color: {COLOR_PRICE_LABEL};")
        key_label.setAlignment(Qt.AlignRight)
        key_label.setFixedWidth(120)
        row_layout.addWidget(key_label)
        
        value_text = str(value) if value is not None else "N/A"
        value_color = COLOR_PRICE_LABEL
        if isinstance(value, bool):
            value_text = "Yes" if value else "No"
            value_color = COLOR_BOOL_YES if value else COLOR_BOOL_NO
        
        value_label = QLabel(value_text)
        value_label.setStyleSheet(f"color: {value_color};")
        value_label.setWordWrap(True)
        row_layout.addWidget(value_label)
        
        layout.addLayout(row_layout)
        return 0
    
    def display_filtered_models(self):
        """Display models filtered by selected type."""
        selected_type = self.model_type_var
        self.clear_display_frame()
        
        # Ensure scroll area is reset
        self.scroll_area.verticalScrollBar().setValue(0)
        
        if not self.models_data or 'data' not in self.models_data:
            error_label = QLabel("No model data available.")
            error_label.setStyleSheet(f"color: orange;")
            self.display_layout.addWidget(error_label, alignment=Qt.AlignCenter)
            return
            
        found_models = False
        models_container = QWidget()
        container_layout = QVBoxLayout(models_container)
        container_layout.setSpacing(10)
        container_layout.setContentsMargins(5, 5, 5, 5)
        
        for model in self.models_data['data']:
            model_id = model.get('id', 'N/A')
            model_type = model.get('type', 'Unknown')
            
            if selected_type == "all" or model_type == selected_type:
                found_models = True
                model_spec = model.get('model_spec', {})
                
                # Create model frame
                model_frame = QGroupBox(f" {model_id} ")
                model_frame.setStyleSheet(f"""
                    QGroupBox {{
                        background-color: {COLOR_FRAME_BACKGROUND};
                        border: 1px solid #555555;
                        border-radius: 5px;
                        margin-top: 10px;
                        padding: 10px;
                        color: {COLOR_PRICE_LABEL};
                    }}
                    QGroupBox::title {{
                        subcontrol-origin: margin;
                        subcontrol-position: top center;
                        padding: 0 5px;
                        background-color: {COLOR_FRAME_BACKGROUND};
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
                            if key == 'steps' and isinstance(value, dict):
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
                    
        if not found_models:
            not_found_label = QLabel(f"No models found for type: '{selected_type}'")
            not_found_label.setStyleSheet(f"color: orange;")
            self.display_layout.addWidget(not_found_label, alignment=Qt.AlignCenter)
        else:
            self.display_layout.addWidget(models_container)
        
        # Ensure scroll area updates
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(0))
        self.status_bar.showMessage(f"Displayed '{selected_type}' models. Price updates automatically.")

# Main application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CombinedViewerApp()
    window.show()
    sys.exit(app.exec())
