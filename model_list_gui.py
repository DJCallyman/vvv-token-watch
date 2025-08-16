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
import queue # Import the queue module

# --- Suppress Warnings (Use with caution) ---
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

# --- API Key (Load securely in real app) ---
API_KEY = 'gqhvkz3l58GIcuJV88G2MiiWayN3BCpRanuO00oWMa' # Replace or load securely

# --- Color Constants ---
COLOR_BOOL_YES = "green"
COLOR_BOOL_NO = "red"
COLOR_ERROR_TEXT = "red"

# --- GUI Application Class ---
class ModelViewerApp:
    def __init__(self, master):
        print("DEBUG: Initializing ModelViewerApp...")
        self.master = master
        master.title("Venice AI Model Viewer")
        master.geometry("800x650")

        self.models_data = None
        self.model_types = ["all"]
        
        # --- Create a queue for thread communication ---
        self.api_queue = queue.Queue()

        # --- Themed Styles ---
        style = ttk.Style()
        style.configure("Key.TLabel", font=("TkDefaultFont", 10, "bold"))
        style.configure("Section.TLabel", font=("TkDefaultFont", 10, "italic"), padding=(0, 5, 0, 1))

        # --- UI Elements ---
        self._create_widgets()
        print("DEBUG: UI elements created.")

        # --- Initial Actions ---
        self.process_api_queue() # Start the queue processor
        print("DEBUG: ModelViewerApp initialization complete.")

    def _create_widgets(self):
        """Creates and packs all the GUI widgets."""
        control_frame = ttk.Frame(self.master, padding="10")
        control_frame.pack(pady=5, fill=tk.X, side=tk.TOP)

        self.connect_button = ttk.Button(control_frame, text="Connect", command=self.connect_thread)
        self.connect_button.pack(side=tk.LEFT, padx=5)

        ttk.Label(control_frame, text="Filter by Type:").pack(side=tk.LEFT, padx=(10, 2))

        self.model_type_var = tk.StringVar(value="all")
        self.type_combobox = ttk.Combobox(control_frame, textvariable=self.model_type_var, state=tk.DISABLED, values=self.model_types, width=15)
        self.type_combobox.pack(side=tk.LEFT, padx=5)

        self.display_button = ttk.Button(control_frame, text="Display Models", command=self.display_selected_models_action, state=tk.DISABLED)
        self.display_button.pack(side=tk.LEFT, padx=5)

        self.view_styles_button = ttk.Button(control_frame, text="View Style Presets", command=self.view_style_presets_action, state=tk.DISABLED)
        self.view_styles_button.pack(side=tk.LEFT, padx=5)

        display_container = ttk.Frame(self.master, borderwidth=1, relief=tk.SUNKEN)
        display_container.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        display_container.grid_rowconfigure(0, weight=1)
        display_container.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(display_container, borderwidth=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(display_container, orient="vertical", command=self.canvas.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=vsb.set)

        self.display_frame = ttk.Frame(self.canvas, padding=(5, 5))
        self.canvas.create_window((0, 0), window=self.display_frame, anchor="nw", tags="self.display_frame")

        self.display_frame.bind("<Configure>", self.on_frame_configure)
        self._bind_mouse_wheel()

        self.status_var = tk.StringVar(value="Ready. Click 'Connect'.")
        status_bar = ttk.Label(self.master, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def process_api_queue(self):
        """Processes items from the API queue in the main GUI thread."""
        try:
            callback, data = self.api_queue.get_nowait()
            callback(data)
        except queue.Empty:
            pass
        finally:
            self.master.after(100, self.process_api_queue)

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

    # --- Core Logic (Refactored for Queue) ---

    def _connect_api_worker(self):
        """Fetches model data in a worker thread."""
        print("DEBUG: Thread: Starting API call for models...")
        url = 'https://api.venice.ai/api/v1/models'
        headers = {'Accept': 'application/json', 'Authorization': f'Bearer {API_KEY}'}
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
            result['error'] = f"API Connection Error: {e}"
            print(f"ERROR: Thread: {result['error']}")
        
        self.api_queue.put((self._update_gui_after_connect, result))

    def _fetch_style_presets_worker(self):
        """Fetches style presets in a worker thread."""
        print("DEBUG: Thread: Starting API call for style presets...")
        url = 'https://api.venice.ai/api/v1/image/styles'
        headers = {'Accept': 'application/json', 'Authorization': f'Bearer {API_KEY}'}
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
            result['error'] = f"API Connection Error: {e}"
            print(f"ERROR: Thread: {result['error']}")
        
        self.api_queue.put((self._update_gui_after_fetch_style_presets, result))

    def connect_thread(self):
        """Handles the 'Connect' button click."""
        print("DEBUG: Connect button clicked, starting thread.")
        self.connect_button.config(state=tk.DISABLED)
        self.display_button.config(state=tk.DISABLED)
        self.view_styles_button.config(state=tk.DISABLED)
        self.type_combobox.config(state=tk.DISABLED)
        self.clear_display_frame()
        self.status_var.set("Connecting to API...")
        ttk.Label(self.display_frame, text="Connecting...").pack(pady=20)
        self.on_frame_configure()
        thread = threading.Thread(target=self._connect_api_worker, daemon=True)
        thread.start()

    def view_style_presets_action(self):
        """Handles the 'View Style Presets' button click."""
        if self.models_data is None:
            messagebox.showwarning("No Data", "Please connect to the API first.", parent=self.master)
            return
        self.status_var.set("Fetching style presets...")
        self.clear_display_frame()
        ttk.Label(self.display_frame, text="Fetching Style Presets...").pack(pady=20)
        self.on_frame_configure()
        thread = threading.Thread(target=self._fetch_style_presets_worker, daemon=True)
        thread.start()

    def _update_gui_after_connect(self, result):
        """Updates GUI after the model connection attempt."""
        print(f"DEBUG: MainThread: Running _update_gui_after_connect, success={result['success']}")
        self.connect_button.config(state=tk.NORMAL)
        self.clear_display_frame()

        if result['success']:
            self.models_data = result['data']
            types = set(model.get('type', 'Unknown') for model in self.models_data['data'])
            self.model_types = ["all"] + sorted(list(types))
            
            self.type_combobox['values'] = self.model_types
            self.type_combobox.set("all")
            self.type_combobox.config(state="readonly")
            self.display_button.config(state=tk.NORMAL)
            self.view_styles_button.config(state=tk.NORMAL)
            self.status_var.set("Connected. Select model type and click 'Display Models'.")
            ttk.Label(self.display_frame, text="Select model type and click 'Display Models'.").pack(pady=20)
        else:
            self.models_data = None
            self.type_combobox['values'] = ["all"]
            self.type_combobox.set("all")
            self.type_combobox.config(state=tk.DISABLED)
            self.display_button.config(state=tk.DISABLED)
            self.view_styles_button.config(state=tk.DISABLED)
            self.status_var.set("Connection failed. Check logs or API key.")
            ttk.Label(self.display_frame, text="Connection failed. Cannot display models.", foreground=COLOR_ERROR_TEXT).pack(pady=20)
            if result['error']:
                self._show_api_error("API Error", result['error'])

        self.on_frame_configure()

    def _update_gui_after_fetch_style_presets(self, result):
        """Updates GUI after fetching style presets."""
        self.clear_display_frame()
        if result['success']:
            style_presets = result['data']
            ttk.Label(self.display_frame, text="Available Style Presets:").pack(pady=10)
            text_widget = tk.Text(self.display_frame, height=15, width=80, wrap=tk.WORD, borderwidth=0, padx=5, pady=5)
            for preset in style_presets:
                text_widget.insert(tk.END, preset + "\n")
            text_widget.config(state=tk.DISABLED)
            text_widget.pack(pady=5, fill=tk.BOTH, expand=True)
            self.status_var.set("Displayed available style presets.")
        else:
            ttk.Label(self.display_frame, text="No style presets available or error occurred.", foreground="orange").pack(pady=20)
            if result['error']:
                self._show_api_error("API Error", result['error'])
        
        self.on_frame_configure()

    def _show_api_error(self, title, error_message):
         messagebox.showerror(title, error_message, parent=self.master)

    def display_selected_models_action(self):
        if self.models_data is None:
            messagebox.showwarning("No Data", "Please connect to the API first.", parent=self.master)
            return
        self.display_filtered_models()

    # --- Display Logic (Largely Unchanged) ---

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
        value_color = {}
        if isinstance(value, bool):
            value_text = "Yes" if value else "No"
            value_color = {'foreground': COLOR_BOOL_YES if value else COLOR_BOOL_NO}
        value_label = ttk.Label(parent, text=value_text, wraplength=500, justify=tk.LEFT, **value_color)
        value_label.grid(row=row, column=1, sticky="nw", padx=2, pady=1)
        return row + 1

    def display_filtered_models(self):
        selected_type = self.model_type_var.get()
        self.clear_display_frame()
        if not self.models_data or 'data' not in self.models_data:
             ttk.Label(self.display_frame, text="No model data available.", foreground="orange").pack(pady=20)
             self.on_frame_configure()
             return
        found_models = False
        for model in self.models_data['data']:
            model_id = model.get('id', 'N/A')
            model_type = model.get('type', 'Unknown')
            if selected_type == "all" or model_type == selected_type:
                found_models = True
                model_spec = model.get('model_spec', {})
                model_frame = ttk.LabelFrame(self.display_frame, text=f" {model_id} ", padding=10)
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
            ttk.Label(self.display_frame, text=f"No models found for type: '{selected_type}'", foreground="orange").pack(pady=20)
        self.master.after(50, self.on_frame_configure)

# --- Run the Application ---
if __name__ == "__main__":
    print("DEBUG: Script starting...")
    try:
        root = tk.Tk()
        s = ttk.Style()
        try:
            if sys.platform == "win32": s.theme_use('vista')
            elif sys.platform == "darwin": s.theme_use('aqua')
            else: s.theme_use('clam')
        except tk.TclError:
            print("DEBUG: Selected theme not available, using default.")
        app = ModelViewerApp(root)
        root.mainloop()
    except Exception as e:
        print("\n--- UNHANDLED EXCEPTION CAUGHT ---")
        traceback.print_exc()
        input("Press Enter to exit...")
