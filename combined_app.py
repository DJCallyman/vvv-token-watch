import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import requests
import warnings
import urllib3
import json
import threading
import traceback
import sys
import time
import queue # Import the queue module
from currency_utils import format_currency

# --- Suppress Warnings (Use with caution) ---
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

# --- Configuration ---
# Venice AI API Key (Load securely in real app)
VENICE_API_KEY = 'gqhvkz3l58GIcuJV88G2MiiWayN3BCpRanuO00oWMa' # Replace or load securely

# CoinGecko Configuration
COINGECKO_TOKEN_ID = 'venice-token'
COINGECKO_CURRENCIES = ['usd', 'aud']
COINGECKO_HOLDING_AMOUNT = 2500
COINGECKO_REFRESH_INTERVAL_MS = 60000 # 60 seconds
COINGECKO_INITIAL_DELAY_MS = 500 # Slightly longer delay

# --- Color Constants ---
COLOR_BOOL_YES = "green"
COLOR_BOOL_NO = "red"
COLOR_PRICE_LABEL = "#FFFFFF"
COLOR_STATUS_LABEL = "#AAAAAA"
COLOR_ERROR_LABEL = "#FF6B6B"

# --- GUI Application Class ---
class CombinedViewerApp:
    def __init__(self, master):
        print("DEBUG: Initializing CombinedViewerApp...")
        self.master = master
        master.title("Venice AI Models & CoinGecko Price Viewer")
        master.geometry("850x750")
        master.configure(bg='#2E2E2E')

        self.models_data = None
        self.model_types = ["all"]
        self.price_data = {
            'usd': {'price': None, 'total': None},
            'aud': {'price': None, 'total': None}
        }
        self.holding_amount = COINGECKO_HOLDING_AMOUNT
        
        # --- Create a queue for thread communication ---
        self.api_queue = queue.Queue()

        # --- Themed Styles ---
        style = ttk.Style()
        style.configure("TFrame", background='#2E2E2E')
        style.configure("TLabel", background='#2E2E2E', foreground=COLOR_PRICE_LABEL)
        style.configure("TButton", padding=5)
        style.configure("TCombobox", padding=5)
        style.configure("Key.TLabel", font=("TkDefaultFont", 10, "bold"), background='#2E2E2E', foreground=COLOR_PRICE_LABEL)
        style.configure("Section.TLabel", font=("TkDefaultFont", 10, "italic"), padding=(0, 5, 0, 1), background='#2E2E2E', foreground=COLOR_PRICE_LABEL)
        style.configure("Status.TLabel", font=("Helvetica", 10), background='#2E2E2E', foreground=COLOR_STATUS_LABEL)
        style.configure("Price.TLabel", font=("Helvetica", 28, "bold"), background='#2E2E2E', foreground=COLOR_PRICE_LABEL)
        style.configure("Holding.TLabel", font=("Helvetica", 14), background='#2E2E2E', foreground=COLOR_PRICE_LABEL)
        style.configure("TokenName.TLabel", font=("Helvetica", 16, "bold"), background='#2E2E2E', foreground=COLOR_PRICE_LABEL)
        style.configure("Vertical.TScrollbar", background='#555555', troughcolor='#2E2E2E', bordercolor='#2E2E2E', arrowcolor=COLOR_PRICE_LABEL)
        style.map("Vertical.TScrollbar",
            background=[('active', '#777777')],
            arrowcolor=[('pressed', 'black'), ('active', 'white')]
        )

        # --- Main Paned Window ---
        # --- Status Bar ---
        self.status_var = tk.StringVar(value="Ready. Click 'Connect' for models. Price updates automatically.")
        status_bar = ttk.Label(master, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, style="Status.TLabel")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        main_pane = tk.PanedWindow(master, orient=tk.VERTICAL, sashwidth=8, bg='#2E2E2E', bd=0)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Top Frame for Price Display ---
        price_frame = ttk.Frame(main_pane, padding="10", style="TFrame")
        main_pane.add(price_frame, height=220, minsize=100)
        self._create_price_display(price_frame)

        # --- Bottom Frame for Model Viewer ---
        model_frame = ttk.Frame(main_pane, padding="10", style="TFrame")
        main_pane.add(model_frame, stretch="always")
        self._create_model_viewer(model_frame)

        print("DEBUG: UI elements created.")
        print("DEBUG: UI elements created.")

        # --- Initial Actions ---
        self.master.after(COINGECKO_INITIAL_DELAY_MS, self.update_price_label)
        self.process_api_queue() # Start the queue processor

        print("DEBUG: CombinedViewerApp initialization complete.")

    def process_api_queue(self):
        """
        Process items from the API queue. This runs in the main GUI thread.
        """
        try:
            message = self.api_queue.get_nowait()
            # message is a tuple: (callback_function, data)
            callback, data = message
            callback(data)
        except queue.Empty:
            pass # No messages to process
        finally:
            # Schedule to run again after 100ms
            self.master.after(100, self.process_api_queue)

        # --- UI Creation Helpers ---
    def _create_price_display(self, parent_frame):
        """Creates the CoinGecko price display widgets with dual-currency support and dynamic holding input."""
        # Configure grid layout
        parent_frame.columnconfigure(0, weight=1)
        parent_frame.columnconfigure(1, weight=1)
        
        # Token name at the top
        token_name_text = COINGECKO_TOKEN_ID.replace('-', ' ').capitalize()
        self.token_name_label = ttk.Label(parent_frame, text=token_name_text, style="TokenName.TLabel")
        self.token_name_label.grid(row=0, column=0, columnspan=2, pady=5)
        
        # Holding amount input
        holding_frame = ttk.Frame(parent_frame, style="TFrame")
        holding_frame.grid(row=1, column=0, columnspan=2, pady=5)
        ttk.Label(holding_frame, text="Holding Amount:", style="TLabel").pack(side=tk.LEFT, padx=(0, 5))
        self.holding_var = tk.StringVar(value=str(COINGECKO_HOLDING_AMOUNT))
        self.holding_entry = ttk.Entry(holding_frame, textvariable=self.holding_var, width=10)
        self.holding_entry.pack(side=tk.LEFT)
        ttk.Label(holding_frame, text="tokens", style="TLabel").pack(side=tk.LEFT, padx=(5, 0))
        self.holding_entry.bind('<Return>', self.update_holding_amount)
        self.holding_entry.bind('<FocusOut>', self.update_holding_amount)
        
        # USD Display Frame
        usd_frame = ttk.LabelFrame(parent_frame, text=" USD ", padding=10, style="TLabelframe")
        usd_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        usd_frame.columnconfigure(0, weight=1)
        
        self.usd_price_label = ttk.Label(usd_frame, text="Loading...", style="Price.TLabel")
        self.usd_price_label.grid(row=0, column=0, pady=(0, 5))
        
        self.usd_holding_label = ttk.Label(usd_frame, text="Holding: Calculating...", style="Holding.TLabel")
        self.usd_holding_label.grid(row=1, column=0, pady=(0, 5))
        
        # AUD Display Frame
        aud_frame = ttk.LabelFrame(parent_frame, text=" AUD ", padding=10, style="TLabelframe")
        aud_frame.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")
        aud_frame.columnconfigure(0, weight=1)
        
        self.aud_price_label = ttk.Label(aud_frame, text="Loading...", style="Price.TLabel")
        self.aud_price_label.grid(row=0, column=0, pady=(0, 5))
        
        self.aud_holding_label = ttk.Label(aud_frame, text="Holding: Calculating...", style="Holding.TLabel")
        self.aud_holding_label.grid(row=1, column=0, pady=(0, 5))
        
        # Status label at the bottom
        self.price_status_label = ttk.Label(parent_frame, text="Initializing...", style="Status.TLabel")
        self.price_status_label.grid(row=3, column=0, columnspan=2, pady=5)

    def update_holding_amount(self, event=None):
        """Validates and processes user input for holding amount."""
        try:
            new_amount = float(self.holding_var.get())
            if new_amount <= 0:
                raise ValueError("Amount must be positive")
            self.holding_amount = new_amount
            # Update total values for each currency
            for currency in COINGECKO_CURRENCIES:
                if self.price_data[currency]['price'] is not None:
                    self.price_data[currency]['total'] = self.price_data[currency]['price'] * self.holding_amount
            # Update the UI labels
            self.usd_price_label.config(text=format_currency(self.price_data['usd']['price'], 'usd'), foreground=COLOR_PRICE_LABEL)
            self.usd_holding_label.config(text=f"Holding: {format_currency(self.price_data['usd']['total'], 'usd')}", foreground=COLOR_PRICE_LABEL)
            self.aud_price_label.config(text=format_currency(self.price_data['aud']['price'], 'aud'), foreground=COLOR_PRICE_LABEL)
            self.aud_holding_label.config(text=f"Holding: {format_currency(self.price_data['aud']['total'], 'aud')}", foreground=COLOR_PRICE_LABEL)
            self.price_status_label.config(
                text=f"Holding amount updated to {new_amount:.2f}. Price updates automatically.",
                foreground=COLOR_STATUS_LABEL
            )
        except ValueError:
            self.holding_var.set(str(self.holding_amount))
            self.price_status_label.config(
                text="Invalid holding amount. Must be a positive number.",
                foreground=COLOR_ERROR_LABEL
            )

    def _create_model_viewer(self, parent_frame):
        """Creates the Venice AI model viewer widgets."""
        parent_frame.rowconfigure(1, weight=1)
        parent_frame.columnconfigure(0, weight=1)
        control_frame = ttk.Frame(parent_frame, padding="5", style="TFrame")
        control_frame.grid(row=0, column=0, pady=(0,5), sticky="ew")
        self.connect_button = ttk.Button(control_frame, text="Connect Models", command=self.connect_thread)
        self.connect_button.pack(side=tk.LEFT, padx=5)
        ttk.Label(control_frame, text="Filter by Type:", style="TLabel").pack(side=tk.LEFT, padx=(10, 2))
        self.model_type_var = tk.StringVar(value="all")
        self.type_combobox = ttk.Combobox(control_frame, textvariable=self.model_type_var, state=tk.DISABLED, values=self.model_types, width=15, style="TCombobox")
        self.type_combobox.pack(side=tk.LEFT, padx=5)
        self.display_button = ttk.Button(control_frame, text="Display Models", command=self.display_selected_models_action, state=tk.DISABLED)
        self.display_button.pack(side=tk.LEFT, padx=5)
        self.view_styles_button = ttk.Button(control_frame, text="View Style Presets", command=self.view_style_presets_action, state=tk.DISABLED)
        self.view_styles_button.pack(side=tk.LEFT, padx=5)
        display_container = ttk.Frame(parent_frame, borderwidth=1, relief=tk.SUNKEN, style="TFrame")
        display_container.grid(row=1, column=0, sticky="nsew")
        display_container.grid_rowconfigure(0, weight=1)
        display_container.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(display_container, borderwidth=0, background='#3C3C3C', highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(display_container, orient="vertical", command=self.canvas.yview, style="Vertical.TScrollbar")
        vsb.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=vsb.set)
        self.display_frame = ttk.Frame(self.canvas, padding=(5, 5), style="TFrame")
        self.canvas.create_window((0, 0), window=self.display_frame, anchor="nw", tags="self.display_frame")
        self.display_frame.bind("<Configure>", self.on_frame_configure)
        self._bind_mouse_wheel()

    def _bind_mouse_wheel(self):
        if sys.platform == "darwin": self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        elif sys.platform.startswith('linux'):
             self.canvas.bind_all("<Button-4>", self._on_mousewheel)
             self.canvas.bind_all("<Button-5>", self._on_mousewheel)
        else: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        if sys.platform == "darwin": scroll_units = -1 * event.delta
        elif sys.platform.startswith('linux'):
            if event.num == 4: scroll_units = -1
            elif event.num == 5: scroll_units = 1
            else: scroll_units = 0
        else: scroll_units = -1 * int(event.delta / 120)
        self.canvas.yview_scroll(scroll_units, "units")

    # --- CoinGecko Price Logic (Unchanged) ---
    def get_coingecko_price(self):
        """Fetch prices for all configured currencies from CoinGecko API."""
        url = f"https://api.coingecko.com/api/v3/simple/price"
        vs_currencies_str = ','.join(COINGECKO_CURRENCIES)
        params = {
            'ids': COINGECKO_TOKEN_ID,
            'vs_currencies': vs_currencies_str
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if COINGECKO_TOKEN_ID in data:
                price_data = {}
                for currency in COINGECKO_CURRENCIES:
                    if currency in data[COINGECKO_TOKEN_ID]:
                        price_data[currency] = data[COINGECKO_TOKEN_ID][currency]
                return price_data
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from CoinGecko API: {e}")
            return None

    def update_price_label(self):
        """Updates price display for all configured currencies with proper formatting and error handling."""
        price_data = self.get_coingecko_price()
        
        if price_data:
            status_messages = []
            failed_currencies = []
            
            for currency in COINGECKO_CURRENCIES:
                if currency in price_data:
                    # Update price and total value
                    self.price_data[currency]['price'] = price_data[currency]
                    self.price_data[currency]['total'] = price_data[currency] * self.holding_amount
                    
                    # Format and update UI labels
                    price_str = format_currency(price_data[currency], currency)
                    total_str = format_currency(self.price_data[currency]['total'], currency)
                    
                    if currency == 'usd':
                        self.usd_price_label.config(text=price_str, foreground=COLOR_PRICE_LABEL)
                        self.usd_holding_label.config(text=f"Holding: {total_str}", foreground=COLOR_PRICE_LABEL)
                    elif currency == 'aud':
                        self.aud_price_label.config(text=price_str, foreground=COLOR_PRICE_LABEL)
                        self.aud_holding_label.config(text=f"Holding: {total_str}", foreground=COLOR_PRICE_LABEL)
                    
                    status_messages.append(f"{currency.upper()}: {price_str}")
                else:
                    # Handle missing currency data
                    failed_currencies.append(currency)
                    if currency == 'usd':
                        self.usd_price_label.config(text="N/A", foreground=COLOR_ERROR_LABEL)
                        self.usd_holding_label.config(text="Holding: N/A", foreground=COLOR_ERROR_LABEL)
                    elif currency == 'aud':
                        self.aud_price_label.config(text="N/A", foreground=COLOR_ERROR_LABEL)
                        self.aud_holding_label.config(text="Holding: N/A", foreground=COLOR_ERROR_LABEL)
                    status_messages.append(f"{currency.upper()}: Error")
            
            # Determine status message and color based on failure type
            if failed_currencies:
                if len(failed_currencies) == len(COINGECKO_CURRENCIES):
                    # Complete failure (shouldn't happen since price_data exists, but just in case)
                    status_str = "Price Update Error. Retrying..."
                    status_color = COLOR_ERROR_LABEL
                else:
                    # Partial failure
                    failed_str = ", ".join([c.upper() for c in failed_currencies])
                    status_str = f"Partial update: {failed_str} failed | {', '.join(status_messages)} | Last updated: {time.strftime('%H:%M:%S')}"
                    status_color = COLOR_ERROR_LABEL
            else:
                # Complete success
                status_str = f"Prices updated: {', '.join(status_messages)} | Last updated: {time.strftime('%H:%M:%S')}"
                status_color = COLOR_STATUS_LABEL
            
            self.price_status_label.config(text=status_str, foreground=status_color)
        else:
            # Handle complete API failure
            for currency in COINGECKO_CURRENCIES:
                if currency == 'usd':
                    self.usd_price_label.config(text="API Error", foreground=COLOR_ERROR_LABEL)
                    self.usd_holding_label.config(text="Holding: N/A", foreground=COLOR_ERROR_LABEL)
                elif currency == 'aud':
                    self.aud_price_label.config(text="API Error", foreground=COLOR_ERROR_LABEL)
                    self.aud_holding_label.config(text="Holding: N/A", foreground=COLOR_ERROR_LABEL)
            
            self.price_status_label.config(text="Price Update Error. Retrying...", foreground=COLOR_ERROR_LABEL)
        
        self.master.after(COINGECKO_REFRESH_INTERVAL_MS, self.update_price_label)

    # --- Venice AI Model Logic (Refactored for Queue) ---
    def _connect_api_worker(self):
        """Fetches model data from Venice AI API (runs in thread)."""
        print("DEBUG: Thread: Starting API call for models...")
        url = 'https://api.venice.ai/api/v1/models'
        headers = {'Accept': 'application/json', 'Authorization': f'Bearer {VENICE_API_KEY}'}
        params = {'type': 'all'}
        result = {'success': False, 'data': None, 'error': None}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=20)
            print(f"DEBUG: Thread: API response status code: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            if data and 'data' in data:
                result['success'] = True
                result['data'] = data
            else:
                result['error'] = "API response missing 'data' key or is empty."
        except requests.exceptions.RequestException as e:
            result['error'] = f"Venice API Connection Error: {e}"
            print(f"ERROR: Thread: {result['error']}")
        
        # Put the result dictionary and the callback function into the queue
        self.api_queue.put((self._update_gui_after_connect, result))

    def _fetch_style_presets_worker(self):
        """Fetches style presets from Venice AI API (runs in thread)."""
        print("DEBUG: Thread: Starting API call for style presets...")
        url = 'https://api.venice.ai/api/v1/image/styles'
        headers = {'Accept': 'application/json', 'Authorization': f'Bearer {VENICE_API_KEY}'}
        result = {'success': False, 'data': [], 'error': None}
        try:
            response = requests.get(url, headers=headers, timeout=20)
            print(f"DEBUG: Thread: Style API response status code: {response.status_code}")
            response.raise_for_status()
            style_presets = response.json()
            if style_presets and 'data' in style_presets:
                result['success'] = True
                result['data'] = style_presets['data']
        except requests.exceptions.RequestException as e:
            result['error'] = f"Style Preset API Error: {e}"
            print(f"ERROR: Thread: {result['error']}")

        # Put the result and callback into the queue
        self.api_queue.put((self._update_gui_after_fetch_style_presets, result))

    def _update_gui_after_fetch_style_presets(self, result):
        """Updates the model display frame with style presets (runs in main thread)."""
        print(f"DEBUG: MainThread: Updating display with style presets.")
        self.clear_display_frame()
        
        if result['success']:
            style_presets = result['data']
            ttk.Label(self.display_frame, text="Available Style Presets:", style="Section.TLabel").pack(pady=10, anchor="w")
            text_widget = tk.Text(self.display_frame, height=15, width=80, wrap=tk.WORD, borderwidth=0, background='#3C3C3C', foreground=COLOR_PRICE_LABEL, padx=5, pady=5)
            for preset in style_presets:
                text_widget.insert(tk.END, preset + "\n")
            text_widget.config(state=tk.DISABLED)
            text_widget.pack(pady=5, fill=tk.BOTH, expand=True)
            self.status_var.set("Displayed available style presets.")
        else:
            ttk.Label(self.display_frame, text="No style presets available or error occurred.", foreground="orange", style="TLabel").pack(pady=20)
            if result['error']:
                self._show_api_error("Style Preset API Error", result['error'])
        
        self.on_frame_configure()
        print("DEBUG: MainThread: Style preset display updated.")


    def connect_thread(self):
        """Starts the API connection in a separate thread."""
        print("DEBUG: Connect Models button clicked, starting thread.")
        self.connect_button.config(state=tk.DISABLED)
        self.display_button.config(state=tk.DISABLED)
        self.view_styles_button.config(state=tk.DISABLED)
        self.type_combobox.config(state=tk.DISABLED)
        self.clear_display_frame()
        self.status_var.set("Connecting to Venice API...")
        ttk.Label(self.display_frame, text="Connecting to Venice API...", style="TLabel").pack(pady=20)
        self.on_frame_configure()
        thread = threading.Thread(target=self._connect_api_worker, daemon=True)
        thread.start()

    def view_style_presets_action(self):
        """Starts fetching style presets in a separate thread."""
        if self.models_data is None:
             messagebox.showwarning("No Model Data", "Please connect to the Model API first.", parent=self.master)
             return
        self.status_var.set("Fetching Style Presets...")
        self.clear_display_frame()
        ttk.Label(self.display_frame, text="Fetching Style Presets...", style="TLabel").pack(pady=20)
        self.on_frame_configure()
        thread = threading.Thread(target=self._fetch_style_presets_worker, daemon=True)
        thread.start()

    def _update_gui_after_connect(self, result):
        """Updates GUI elements after the model connection attempt (runs in main thread)."""
        print(f"DEBUG: MainThread: Running _update_gui_after_connect, success={result['success']}")
        self.connect_button.config(state=tk.NORMAL)
        self.clear_display_frame()

        if result['success']:
            self.models_data = result['data']
            types = set(model.get('type', 'Unknown') for model in self.models_data['data'])
            types = {str(t) if t is not None else 'Unknown' for t in types}
            self.model_types = ["all"] + sorted(list(types))
            
            print("DEBUG: MainThread: Updating model combobox and enabling controls.")
            self.type_combobox['values'] = self.model_types
            self.type_combobox.set("all")
            self.type_combobox.config(state="readonly")
            self.display_button.config(state=tk.NORMAL)
            self.view_styles_button.config(state=tk.NORMAL)
            self.status_var.set("Model API Connected. Select type and 'Display Models'.")
            ttk.Label(self.display_frame, text="Select model type and click 'Display Models'.", style="TLabel").pack(pady=20)
        else:
            print("DEBUG: MainThread: Model connect failed or no data.")
            self.models_data = None # Ensure data is cleared on failure
            self.type_combobox['values'] = ["all"]
            self.type_combobox.set("all")
            self.type_combobox.config(state=tk.DISABLED)
            self.display_button.config(state=tk.DISABLED)
            self.view_styles_button.config(state=tk.DISABLED)
            self.status_var.set("Model connection failed. Check logs or API key.")
            ttk.Label(self.display_frame, text="Model Connection failed.", foreground=COLOR_ERROR_LABEL, style="TLabel").pack(pady=20)
            if result['error']:
                self._show_api_error("Venice API Connection Error", result['error'])

        self.on_frame_configure()
        print("DEBUG: MainThread: _update_gui_after_connect complete.")

    def _show_api_error(self, title, error_message):
         print(f"DEBUG: MainThread: Showing API error messagebox: {title}")
         messagebox.showerror(title, error_message, parent=self.master)

    def display_selected_models_action(self):
        if self.models_data is None:
            messagebox.showwarning("No Model Data", "Please connect to the Model API first.", parent=self.master)
            return
        self.display_filtered_models()

    # --- Model Display Logic (Unchanged) ---
    def clear_display_frame(self):
        for widget in self.display_frame.winfo_children():
            widget.destroy()
        self.canvas.yview_moveto(0)

    def _add_separator(self, parent, row):
        sep = ttk.Separator(parent, orient='horizontal')
        sep.grid(row=row, column=0, columnspan=2, sticky='ew', padx=5, pady=8)
        return row + 1

    def _add_section_heading(self, parent, text, row):
        heading = ttk.Label(parent, text=text, style="Section.TLabel")
        heading.grid(row=row, column=0, columnspan=2, sticky='nw', padx=5, pady=(8, 1))
        return row + 1

    def _add_detail(self, parent, key, value, row):
        key_label = ttk.Label(parent, text=f"{key}:", style="Key.TLabel")
        key_label.grid(row=row, column=0, sticky="ne", padx=(10, 2), pady=1)
        value_text = str(value) if value is not None else "N/A"
        value_color_opts = {}
        if isinstance(value, bool):
            value_text = "Yes" if value else "No"
            value_color_opts = {'foreground': COLOR_BOOL_YES if value else COLOR_BOOL_NO}
        value_label = ttk.Label(parent, text=value_text, wraplength=550, justify=tk.LEFT, **value_color_opts)
        value_label.grid(row=row, column=1, sticky="nw", padx=2, pady=1)
        return row + 1

    def display_filtered_models(self):
        selected_type = self.model_type_var.get()
        self.clear_display_frame()
        if not self.models_data or 'data' not in self.models_data:
             ttk.Label(self.display_frame, text="No model data available.", foreground="orange", style="TLabel").pack(pady=20)
             self.on_frame_configure()
             return
        found_models = False
        models_container = ttk.Frame(self.display_frame, style="TFrame")
        models_container.pack(fill=tk.BOTH, expand=True)
        for model in self.models_data['data']:
            model_id = model.get('id', 'N/A')
            model_type = model.get('type', 'Unknown')
            if selected_type == "all" or model_type == selected_type:
                found_models = True
                model_spec = model.get('model_spec', {})
                model_frame = ttk.LabelFrame(models_container, text=f" {model_id} ", padding=10, style="TLabelframe")
                model_frame.pack(pady=10, padx=5, fill=tk.X, expand=True)
                model_frame.columnconfigure(1, weight=1)
                current_row = 0
                current_row = self._add_detail(model_frame, "Type", model_type, current_row)
                if model_type == "text":
                    current_row = self._add_detail(model_frame, "Context Tokens", model_spec.get('availableContextTokens'), current_row)
                current_row = self._add_separator(model_frame, current_row)
                if model_type == "text":
                    caps = model_spec.get('capabilities')
                    if caps:
                        current_row = self._add_section_heading(model_frame, "Capabilities", current_row)
                        for key, value in caps.items(): current_row = self._add_detail(model_frame, key, value, current_row)
                        current_row = self._add_separator(model_frame, current_row)
                    const = model_spec.get('constraints')
                    if const:
                        current_row = self._add_section_heading(model_frame, "Constraints", current_row)
                        for key, value in const.items():
                            if isinstance(value, dict):
                                for sub_key, sub_value in value.items(): current_row = self._add_detail(model_frame, f"{key} ({sub_key})", sub_value, current_row)
                            else: current_row = self._add_detail(model_frame, key, value, current_row)
                        current_row = self._add_separator(model_frame, current_row)
                elif model_type == "image":
                    const = model_spec.get('constraints')
                    if const:
                        current_row = self._add_section_heading(model_frame, "Constraints", current_row)
                        for key, value in const.items():
                            if key == 'steps' and isinstance(value, dict):
                                for sub_key, sub_value in value.items(): current_row = self._add_detail(model_frame, f"{key} ({sub_key})", sub_value, current_row)
                            else: current_row = self._add_detail(model_frame, key, value, current_row)
                        current_row = self._add_separator(model_frame, current_row)
                elif model_type == "tts":
                     voices = model_spec.get('voices', [])
                     if voices:
                         current_row = self._add_section_heading(model_frame, "Voices", current_row)
                         current_row = self._add_detail(model_frame, "Available", ", ".join(voices), current_row)
                         current_row = self._add_separator(model_frame, current_row)
                traits = model_spec.get('traits', [])
                if traits:
                     current_row = self._add_section_heading(model_frame, "Traits", current_row)
                     current_row = self._add_detail(model_frame, "Assigned", ", ".join(traits), current_row)
                     current_row = self._add_separator(model_frame, current_row)
                other_info_exists = any(k in model_spec for k in ['modelSource', 'beta', 'offline'])
                if other_info_exists:
                    current_row = self._add_section_heading(model_frame, "Other Info", current_row)
                    current_row = self._add_detail(model_frame, "Source", model_spec.get('modelSource'), current_row)
                    current_row = self._add_detail(model_frame, "Beta", model_spec.get('beta'), current_row)
                    current_row = self._add_detail(model_frame, "Offline", model_spec.get('offline'), current_row)
        if not found_models:
            ttk.Label(self.display_frame, text=f"No models found for type: '{selected_type}'", foreground="orange", style="TLabel").pack(pady=20)
        self.master.after(50, self.on_frame_configure)
        self.status_var.set(f"Displayed '{selected_type}' models. Price updates automatically.")

# --- Run the Application ---
if __name__ == "__main__":
    print("DEBUG: Combined script starting...")
    try:
        root = tk.Tk()
        s = ttk.Style()
        try:
            if sys.platform == "win32": s.theme_use('vista')
            elif sys.platform == "darwin": s.theme_use('aqua')
            else: s.theme_use('clam')
        except tk.TclError:
            print("DEBUG: Selected theme not available, using default.")
        app = CombinedViewerApp(root)
        root.mainloop()
    except Exception as e:
        print("\n--- UNHANDLED EXCEPTION CAUGHT ---")
        traceback.print_exc()
        print("--- END OF EXCEPTION ---")
