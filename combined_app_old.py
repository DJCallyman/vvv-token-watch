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
# import webbrowser # Keep commented for now, needed for clickable links later

# --- Suppress Warnings (Use with caution) ---
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

# --- Configuration ---
# Venice AI API Key (Load securely in real app)
VENICE_API_KEY = 'gqhvkz3l58GIcuJV88G2MiiWayN3BCpRanuO00oWMa' # Replace or load securely

# CoinGecko Configuration
COINGECKO_TOKEN_ID = 'venice-token'
COINGECKO_VS_CURRENCY = 'usd'
COINGECKO_HOLDING_AMOUNT = 2345
COINGECKO_REFRESH_INTERVAL_MS = 60000 # 60 seconds
COINGECKO_INITIAL_DELAY_MS = 500 # Slightly longer delay

# --- Color Constants ---
COLOR_BOOL_YES = "green"
COLOR_BOOL_NO = "red"
COLOR_PRICE_LABEL = "#FFFFFF"
COLOR_STATUS_LABEL = "#AAAAAA"
COLOR_ERROR_LABEL = "#FF6B6B"
# COLOR_LINK = "blue" # For clickable links later

# --- GUI Application Class ---
class CombinedViewerApp:
    def __init__(self, master):
        print("DEBUG: Initializing CombinedViewerApp...")
        self.master = master
        master.title("Venice AI Models & CoinGecko Price Viewer")
        master.geometry("850x750") # Adjusted size
        master.configure(bg='#2E2E2E') # Background from vvv_display

        self.models_data = None
        self.model_types = ["all"]
        self.coingecko_price = None
        self.coingecko_total_value = None

        # Use themed font style for keys
        style = ttk.Style()
        style.configure("TFrame", background='#2E2E2E') # Style frames
        style.configure("TLabel", background='#2E2E2E', foreground=COLOR_PRICE_LABEL) # Style labels
        style.configure("TButton", padding=5)
        style.configure("TCombobox", padding=5)
        style.configure("Key.TLabel", font=("TkDefaultFont", 10, "bold"), background='#2E2E2E', foreground=COLOR_PRICE_LABEL)
        style.configure("Section.TLabel", font=("TkDefaultFont", 10, "italic"), padding=(0, 5, 0, 1), background='#2E2E2E', foreground=COLOR_PRICE_LABEL)
        style.configure("Status.TLabel", font=("Helvetica", 10), background='#2E2E2E', foreground=COLOR_STATUS_LABEL)
        style.configure("Price.TLabel", font=("Helvetica", 28, "bold"), background='#2E2E2E', foreground=COLOR_PRICE_LABEL)
        style.configure("Holding.TLabel", font=("Helvetica", 14), background='#2E2E2E', foreground=COLOR_PRICE_LABEL)
        style.configure("TokenName.TLabel", font=("Helvetica", 16, "bold"), background='#2E2E2E', foreground=COLOR_PRICE_LABEL)

        # Themed scrollbar
        style.configure("Vertical.TScrollbar", background='#555555', troughcolor='#2E2E2E', bordercolor='#2E2E2E', arrowcolor=COLOR_PRICE_LABEL)
        style.map("Vertical.TScrollbar",
            background=[('active', '#777777')],
            arrowcolor=[('pressed', 'black'), ('active', 'white')]
        )


        # --- Main Paned Window (to separate sections) ---
        main_pane = tk.PanedWindow(master, orient=tk.VERTICAL, sashwidth=8, bg='#2E2E2E', bd=0)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Top Frame for Price Display ---
        price_frame = ttk.Frame(main_pane, padding="10", style="TFrame")
        main_pane.add(price_frame, height=150, minsize=100) # Add to pane

        self._create_price_display(price_frame)

        # --- Bottom Frame for Model Viewer ---
        model_frame = ttk.Frame(main_pane, padding="10", style="TFrame")
        main_pane.add(model_frame, stretch="always") # Add to pane

        self._create_model_viewer(model_frame)


        # --- Status Bar ---
        self.status_var = tk.StringVar(value="Ready. Click 'Connect' for models. Price updates automatically.")
        status_bar = ttk.Label(master, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, style="Status.TLabel")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        print("DEBUG: UI elements created.")

        # --- Initial Actions ---
        # Start the automatic price update loop
        self.master.after(COINGECKO_INITIAL_DELAY_MS, self.update_price_label)

        print("DEBUG: CombinedViewerApp initialization complete.")

    # --- UI Creation Helpers ---
    def _create_price_display(self, parent_frame):
        """Creates the CoinGecko price display widgets."""
        print("DEBUG: Creating Price Display UI...")
        parent_frame.columnconfigure(0, weight=1) # Center content

        # Token Name Label
        token_name_text = COINGECKO_TOKEN_ID.replace('-', ' ').capitalize()
        self.token_name_label = ttk.Label(parent_frame, text=token_name_text, style="TokenName.TLabel")
        self.token_name_label.grid(row=0, column=0, pady=5)

        # Price Label
        self.price_label = ttk.Label(parent_frame, text="Loading Price...", style="Price.TLabel")
        self.price_label.grid(row=1, column=0, pady=5)

        # Holding Value Label
        self.holding_value_label = ttk.Label(parent_frame, text="Calculating...", style="Holding.TLabel")
        self.holding_value_label.grid(row=2, column=0, pady=5)

        # Price Status Label (Separate from main status)
        self.price_status_label = ttk.Label(parent_frame, text="Initializing...", style="Status.TLabel")
        self.price_status_label.grid(row=3, column=0, pady=5)
        print("DEBUG: Price Display UI created.")

    def _create_model_viewer(self, parent_frame):
        """Creates the Venice AI model viewer widgets."""
        print("DEBUG: Creating Model Viewer UI...")
        parent_frame.rowconfigure(1, weight=1)
        parent_frame.columnconfigure(0, weight=1)

        # Control Frame for Model Viewer
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

        # Scrollable Display Area for Models
        display_container = ttk.Frame(parent_frame, borderwidth=1, relief=tk.SUNKEN, style="TFrame")
        display_container.grid(row=1, column=0, sticky="nsew")
        display_container.grid_rowconfigure(0, weight=1)
        display_container.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(display_container, borderwidth=0, background='#3C3C3C', highlightthickness=0) # Match background
        self.canvas.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(display_container, orient="vertical", command=self.canvas.yview, style="Vertical.TScrollbar")
        vsb.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=vsb.set)

        self.display_frame = ttk.Frame(self.canvas, padding=(5, 5), style="TFrame") # Frame inside canvas
        self.canvas.create_window((0, 0), window=self.display_frame, anchor="nw", tags="self.display_frame")

        self.display_frame.bind("<Configure>", self.on_frame_configure)
        # Mouse wheel binding needs to be adjusted for cross-platform
        self._bind_mouse_wheel()

        print("DEBUG: Model Viewer UI created.")

    def _bind_mouse_wheel(self):
        # Platform-specific mouse wheel binding
        if sys.platform == "darwin":
             self.canvas.bind_all("<MouseWheel>", self._on_mousewheel) # Might need adjustment
        elif sys.platform.startswith('linux'):
             self.canvas.bind_all("<Button-4>", self._on_mousewheel)
             self.canvas.bind_all("<Button-5>", self._on_mousewheel)
        else: # Windows
             self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def on_frame_configure(self, event=None):
        # Update scroll region when display frame size changes
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        # Handle mouse wheel scrolling
        if sys.platform == "darwin":
            scroll_units = -1 * event.delta
        elif sys.platform.startswith('linux'):
            if event.num == 4: scroll_units = -1
            elif event.num == 5: scroll_units = 1
            else: scroll_units = 0
        else: # Windows
             scroll_units = -1 * int(event.delta / 120)

        self.canvas.yview_scroll(scroll_units, "units")

    # --- CoinGecko Price Logic ---
    def get_coingecko_price(self):
        """Fetches the current price from CoinGecko API."""
        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': COINGECKO_TOKEN_ID,
            'vs_currencies': COINGECKO_VS_CURRENCY
        }
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            if COINGECKO_TOKEN_ID in data and COINGECKO_VS_CURRENCY in data[COINGECKO_TOKEN_ID]:
                return data[COINGECKO_TOKEN_ID][COINGECKO_VS_CURRENCY]
            else:
                print(f"Error: Could not find price data for '{COINGECKO_TOKEN_ID}' in '{COINGECKO_VS_CURRENCY}'. Response: {data}")
                return None
        except requests.exceptions.Timeout:
            print("Error: Request to CoinGecko API timed out.")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from CoinGecko API: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during price fetch: {e}")
            return None

    def update_price_label(self):
        """Fetches price, updates labels, and schedules the next update."""
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Fetching price for {COINGECKO_TOKEN_ID}...")
        price = self.get_coingecko_price()
        self.coingecko_price = price # Store the latest price

        if price is not None:
            self.coingecko_total_value = price * COINGECKO_HOLDING_AMOUNT
            try:
                price_str = f"${price:,.2f} {COINGECKO_VS_CURRENCY.upper()}"
                value_str = f"Holding: ${self.coingecko_total_value:,.2f}"
            except (ValueError, TypeError):
                 price_str = f"${price} {COINGECKO_VS_CURRENCY.upper()}"
                 value_str = f"Holding: ${self.coingecko_total_value}"

            status_str = f"Price Last updated: {time.strftime('%H:%M:%S')}"

            self.price_label.config(text=price_str, style="Price.TLabel") # Use correct style
            self.holding_value_label.config(text=value_str, style="Holding.TLabel")
            self.price_status_label.config(text=status_str, style="Status.TLabel", foreground=COLOR_STATUS_LABEL) # Reset status color
            print(f"Price updated: {price_str}")
            print(f"Holding value updated: {value_str}")

        else:
            self.coingecko_total_value = None
            # Update status to indicate error, keep last price/value if available
            if self.price_label.cget("text") == "Loading Price...":
                 self.price_label.config(text="N/A", style="Price.TLabel") # Indicate not available
                 self.holding_value_label.config(text="Holding: N/A", style="Holding.TLabel")
            self.price_status_label.config(text="Price Update Error. Retrying...", style="Status.TLabel", foreground=COLOR_ERROR_LABEL) # Red color
            print("Failed to update price.")

        # Schedule the next update
        self.master.after(COINGECKO_REFRESH_INTERVAL_MS, self.update_price_label)


    # --- Venice AI Model Logic ---
    def _connect_api(self):
        """Fetches model data from Venice AI API (runs in thread)."""
        print("DEBUG: Thread: Starting API call for models...")
        url = 'https://api.venice.ai/api/v1/models'
        headers = {'Accept': 'application/json', 'Authorization': f'Bearer {VENICE_API_KEY}'}
        params = {'type': 'all'}
        try:
            # Use after(0, ...) to schedule GUI updates from the worker thread
            self.master.after(0, self.status_var.set, "Connecting to Venice API...")
            response = requests.get(url, headers=headers, params=params, timeout=20)
            print(f"DEBUG: Thread: API response status code: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            if data and 'data' in data:
                 self.models_data = data # Store the full data
                 types = set(model.get('type', 'Unknown') for model in self.models_data['data'])
                 self.model_types = ["all"] + sorted(list(types))
                 print(f"DEBUG: Thread: Found model types: {self.model_types}")
                 self.master.after(0, self._update_gui_after_connect, True) # Schedule GUI update
            else:
                 print("DEBUG: Thread: Model API response missing 'data' key or is empty.")
                 self.models_data = None
                 self.master.after(0, self._update_gui_after_connect, False)
            return True # Indicate success/failure of the operation
        except requests.exceptions.RequestException as e:
            self.models_data = None
            error_message = f"Venice API Error: {e}"
            print(f"ERROR: Thread: {error_message}")
            self.master.after(0, self._show_api_error, "Venice API Connection Error", error_message)
            self.master.after(0, self._update_gui_after_connect, False)
            return False

    def _fetch_style_presets(self):
        """Fetches style presets from Venice AI API (runs in thread)."""
        print("DEBUG: Thread: Starting API call for style presets...")
        url = 'https://api.venice.ai/api/v1/image/styles'
        headers = {'Accept': 'application/json', 'Authorization': f'Bearer {VENICE_API_KEY}'}
        try:
            self.master.after(0, self.status_var.set, "Fetching style presets...")
            response = requests.get(url, headers=headers, timeout=20)
            print(f"DEBUG: Thread: Style API response status code: {response.status_code}")
            response.raise_for_status()
            style_presets = response.json()
            if style_presets and 'data' in style_presets:
                # Schedule GUI update with the fetched data
                self.master.after(0, self._update_gui_after_fetch_style_presets, style_presets['data'])
            else:
                print("DEBUG: Thread: Style API response missing 'data' key or is empty.")
                self.master.after(0, self._update_gui_after_fetch_style_presets, [])
        except requests.exceptions.RequestException as e:
            error_message = f"Style Preset API Error: {e}"
            print(f"ERROR: Thread: {error_message}")
            # Schedule error display and GUI update
            self.master.after(0, self._show_api_error, "Style Preset API Error", error_message)
            self.master.after(0, self._update_gui_after_fetch_style_presets, [])

    def _update_gui_after_fetch_style_presets(self, style_presets):
        """Updates the model display frame with style presets (runs in main thread)."""
        print(f"DEBUG: MainThread: Updating display with {len(style_presets)} style presets.")
        self.clear_display_frame()
        if style_presets:
            ttk.Label(self.display_frame, text="Available Style Presets:", style="Section.TLabel").pack(pady=10, anchor="w")
            # Use a Text widget for better scrollability and selection if many presets
            text_widget = tk.Text(self.display_frame, height=15, width=80, wrap=tk.WORD, borderwidth=0, background='#3C3C3C', foreground=COLOR_PRICE_LABEL, padx=5, pady=5)
            for preset in style_presets:
                text_widget.insert(tk.END, preset + "\n")
            text_widget.config(state=tk.DISABLED) # Make read-only
            text_widget.pack(pady=5, fill=tk.BOTH, expand=True)

        else:
            ttk.Label(self.display_frame, text="No style presets available.", foreground="orange", style="TLabel").pack(pady=20)
        self.on_frame_configure() # Update scroll region
        self.status_var.set("Displayed available style presets.")
        print("DEBUG: MainThread: Style preset display updated.")


    def connect_thread(self):
        """Starts the API connection in a separate thread."""
        print("DEBUG: Connect Models button clicked, starting thread.")
        self.connect_button.config(state=tk.DISABLED)
        self.display_button.config(state=tk.DISABLED)
        self.view_styles_button.config(state=tk.DISABLED)
        self.type_combobox.config(state=tk.DISABLED)
        self.clear_display_frame()
        ttk.Label(self.display_frame, text="Connecting to Venice API...", style="TLabel").pack(pady=20)
        self.on_frame_configure()

        # Run _connect_api in a daemon thread
        thread = threading.Thread(target=self._connect_api, daemon=True)
        thread.start()

    def view_style_presets_action(self):
        """Starts fetching style presets in a separate thread."""
        print("DEBUG: View Style Presets button clicked.")
        if self.models_data is None:
             messagebox.showwarning("No Model Data", "Please connect to the Model API first using 'Connect Models'.", parent=self.master)
             return

        self.clear_display_frame()
        ttk.Label(self.display_frame, text="Fetching Style Presets...", style="TLabel").pack(pady=20)
        self.on_frame_configure()

        # Run _fetch_style_presets in a daemon thread
        thread = threading.Thread(target=self._fetch_style_presets, daemon=True)
        thread.start()


    def _update_gui_after_connect(self, success):
        """Updates GUI elements after the model connection attempt (runs in main thread)."""
        print(f"DEBUG: MainThread: Running _update_gui_after_connect, success={success}")
        self.connect_button.config(state=tk.NORMAL) # Re-enable connect button
        self.clear_display_frame() # Clear "Connecting..." message

        if success and self.models_data:
             print("DEBUG: MainThread: Updating model combobox and enabling controls.")
             self.type_combobox['values'] = self.model_types
             self.type_combobox.set("all")
             self.type_combobox.config(state="readonly")
             self.display_button.config(state=tk.NORMAL)
             self.view_styles_button.config(state=tk.NORMAL)
             self.status_var.set("Model API Connected. Select type and 'Display Models'. Price updates automatically.")
             ttk.Label(self.display_frame, text="Select model type and click 'Display Models'.", style="TLabel").pack(pady=20)
        else:
             print("DEBUG: MainThread: Model connect failed or no data.")
             self.type_combobox['values'] = ["all"]
             self.type_combobox.set("all")
             self.type_combobox.config(state=tk.DISABLED)
             self.display_button.config(state=tk.DISABLED)
             self.view_styles_button.config(state=tk.DISABLED)
             # Don't overwrite price status, update main status bar only
             current_status = self.status_var.get()
             if "Price" not in current_status: # Avoid overwriting if price update happened
                 self.status_var.set("Model connection failed. Check logs or API key. Price updates automatically.")
             ttk.Label(self.display_frame, text="Model Connection failed. Cannot display models.", foreground=COLOR_ERROR_LABEL, style="TLabel").pack(pady=20)

        self.on_frame_configure() # Update scroll region
        print("DEBUG: MainThread: _update_gui_after_connect complete.")


    def _show_api_error(self, title, error_message):
         """Displays an error message box (runs in main thread)."""
         print(f"DEBUG: MainThread: Showing API error messagebox: {title}")
         messagebox.showerror(title, error_message, parent=self.master)

    def display_selected_models_action(self):
        """Handles the 'Display Models' button click."""
        print("DEBUG: Display Models button clicked.")
        if self.models_data is None:
            messagebox.showwarning("No Model Data", "Please connect to the Model API first using 'Connect Models'.", parent=self.master)
            return
        self.display_filtered_models()

    # --- Model Display Logic ---

    def clear_display_frame(self):
        """Destroys all widgets inside the model display_frame."""
        print("DEBUG: Clearing model display frame...")
        for widget in self.display_frame.winfo_children():
            widget.destroy()
        self.canvas.yview_moveto(0) # Scroll back to top

    def _add_separator(self, parent, row):
        """Adds a separator line to the grid."""
        sep = ttk.Separator(parent, orient='horizontal')
        sep.grid(row=row, column=0, columnspan=2, sticky='ew', padx=5, pady=8)
        return row + 1

    def _add_section_heading(self, parent, text, row):
        """Adds an italic section heading to the grid."""
        heading = ttk.Label(parent, text=text, style="Section.TLabel")
        heading.grid(row=row, column=0, columnspan=2, sticky='nw', padx=5, pady=(8, 1))
        return row + 1

    def _add_detail(self, parent, key, value, row):
        """Adds a key-value label pair to the grid."""
        key_label = ttk.Label(parent, text=f"{key}:", style="Key.TLabel")
        key_label.grid(row=row, column=0, sticky="ne", padx=(10, 2), pady=1)

        value_text = str(value) if value is not None else "N/A"
        value_style = "TLabel" # Default style
        value_color_opts = {}

        if isinstance(value, bool):
            if value:
                value_text = "Yes"
                value_color_opts = {'foreground': COLOR_BOOL_YES}
            else:
                value_text = "No"
                value_color_opts = {'foreground': COLOR_BOOL_NO}

        # Create a unique style for colored labels if needed, or configure directly
        value_label = ttk.Label(parent, text=value_text, wraplength=550, justify=tk.LEFT, style=value_style, **value_color_opts)
        value_label.grid(row=row, column=1, sticky="nw", padx=2, pady=1)
        return row + 1

    def display_filtered_models(self):
        """Clears and updates the model display_frame with filtered model info."""
        selected_type = self.model_type_var.get()
        print(f"DEBUG: Displaying models for type: {selected_type}")
        self.clear_display_frame()

        if not self.models_data or 'data' not in self.models_data:
             ttk.Label(self.display_frame, text="No model data available.", foreground="orange", style="TLabel").pack(pady=20)
             self.on_frame_configure()
             return

        found_models = False
        # Create a container frame *inside* display_frame to hold all model LabelFrames
        # This helps manage layout and potential future additions more easily.
        models_container = ttk.Frame(self.display_frame, style="TFrame")
        models_container.pack(fill=tk.BOTH, expand=True)

        for model in self.models_data['data']:
            model_id = model.get('id', 'N/A')
            model_type = model.get('type', 'Unknown')

            if selected_type == "all" or model_type == selected_type:
                found_models = True
                model_spec = model.get('model_spec', {})

                # Create LabelFrame for this model inside models_container
                model_frame = ttk.LabelFrame(models_container, text=f" {model_id} ", padding=10, style="TLabelframe")
                model_frame.pack(pady=10, padx=5, fill=tk.X, expand=True)
                model_frame.columnconfigure(1, weight=1) # Value column expands

                # Add details using helper functions
                current_row = 0
                current_row = self._add_detail(model_frame, "Type", model_type, current_row)
                if model_type == "text":
                    current_row = self._add_detail(model_frame, "Context Tokens", model_spec.get('availableContextTokens'), current_row)
                current_row = self._add_separator(model_frame, current_row)

                # Type-specific sections
                if model_type == "text":
                    caps = model_spec.get('capabilities')
                    if caps and isinstance(caps, dict):
                        current_row = self._add_section_heading(model_frame, "Capabilities", current_row)
                        for key, value in caps.items(): current_row = self._add_detail(model_frame, key, value, current_row)
                        current_row = self._add_separator(model_frame, current_row)

                    const = model_spec.get('constraints')
                    if const and isinstance(const, dict):
                        current_row = self._add_section_heading(model_frame, "Constraints", current_row)
                        for key, value in const.items():
                            if isinstance(value, dict):
                                for sub_key, sub_value in value.items(): current_row = self._add_detail(model_frame, f"{key} ({sub_key})", sub_value, current_row)
                            else: current_row = self._add_detail(model_frame, key, value, current_row)
                        current_row = self._add_separator(model_frame, current_row)

                elif model_type == "image":
                    const = model_spec.get('constraints')
                    if const and isinstance(const, dict):
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

                # Common Traits Section
                traits = model_spec.get('traits', [])
                if traits:
                     current_row = self._add_section_heading(model_frame, "Traits", current_row)
                     current_row = self._add_detail(model_frame, "Assigned", ", ".join(traits), current_row)
                     current_row = self._add_separator(model_frame, current_row)

                # Other Info Section
                other_info_exists = any(k in model_spec for k in ['modelSource', 'beta', 'offline'])
                if other_info_exists:
                    current_row = self._add_section_heading(model_frame, "Other Info", current_row)
                    current_row = self._add_detail(model_frame, "Source", model_spec.get('modelSource'), current_row)
                    current_row = self._add_detail(model_frame, "Beta", model_spec.get('beta'), current_row)
                    current_row = self._add_detail(model_frame, "Offline", model_spec.get('offline'), current_row)
                # Optional: Remove last separator if it exists
                # last_widget = model_frame.grid_slaves(row=current_row-1, column=0)[0]
                # if isinstance(last_widget, ttk.Separator): last_widget.destroy()


        if not found_models:
            ttk.Label(self.display_frame, text=f"No models found for type: '{selected_type}'", foreground="orange", style="TLabel").pack(pady=20)

        # Update scrollregion after a short delay
        self.master.after(50, self.on_frame_configure)
        self.status_var.set(f"Displayed '{selected_type}' models. Price updates automatically.")
        print("DEBUG: Model display frame updated.")


# --- Run the Application ---
if __name__ == "__main__":
    print("DEBUG: Combined script starting...")
    try:
        print("DEBUG: Creating main Tk window...")
        root = tk.Tk()

        # --- Theme Application ---
        s = ttk.Style()
        # Set theme based on platform
        try:
            if sys.platform == "win32": s.theme_use('vista')
            elif sys.platform == "darwin": s.theme_use('aqua')
            else: s.theme_use('clam')
        except tk.TclError:
            print("DEBUG: Selected theme not available, using default.")
        # Apply background color to the root window explicitly if needed
        # root.configure(bg='#2E2E2E') # Done in App init

        print("DEBUG: Instantiating CombinedViewerApp...")
        app = CombinedViewerApp(root)
        print("DEBUG: Starting Tk main event loop...")
        root.mainloop()
        print("DEBUG: Tk main event loop finished.")
    except Exception as e:
        print("\n--- UNHANDLED EXCEPTION CAUGHT ---")
        print(f"An error occurred: {e}")
        print("Traceback:")
        traceback.print_exc()
        print("--- END OF EXCEPTION ---")
        # Keep terminal open only if not running in an IDE typically
        # input("Press Enter to exit...")