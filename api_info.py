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
# import webbrowser # Keep commented for now, needed for clickable links later

# --- Suppress Warnings (Use with caution) ---
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

# --- API Key (Load securely in real app) ---
API_KEY = 'gqhvkz3l58GIcuJV88G2MiiWayN3BCpRanuO00oWMa' # Replace or load securely

# --- Color Constants ---
COLOR_BOOL_YES = "green"
COLOR_BOOL_NO = "red"
# COLOR_LINK = "blue" # For clickable links later

# --- GUI Application Class ---
class ModelViewerApp:
    def __init__(self, master):
        print("DEBUG: Initializing ModelViewerApp...")
        self.master = master
        master.title("Venice AI Model Viewer")
        master.geometry("800x650") # Increased height slightly

        self.models_data = None
        self.model_types = ["all"]
        # Use a themed font style for keys
        style = ttk.Style()
        style.configure("Key.TLabel", font=("TkDefaultFont", 10, "bold"))
        # Style for Section headings within a LabelFrame
        style.configure("Section.TLabel", font=("TkDefaultFont", 10, "italic"), padding=(0, 5, 0, 1))


        # --- UI Elements ---
        print("DEBUG: Creating UI elements...")
        control_frame = ttk.Frame(master, padding="10")
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

        # --- Scrollable Display Area ---
        display_container = ttk.Frame(master, borderwidth=1, relief=tk.SUNKEN)
        display_container.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        display_container.grid_rowconfigure(0, weight=1)
        display_container.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(display_container, borderwidth=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(display_container, orient="vertical", command=self.canvas.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=vsb.set)

        self.display_frame = ttk.Frame(self.canvas, padding=(5, 5)) # Add padding to inner frame
        self.canvas.create_window((0, 0), window=self.display_frame, anchor="nw", tags="self.display_frame")

        self.display_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        if sys.platform.startswith('linux'):
             self.canvas.bind_all("<Button-4>", self._on_mousewheel)
             self.canvas.bind_all("<Button-5>", self._on_mousewheel)


        # --- Status Bar ---
        self.status_var = tk.StringVar(value="Ready. Click 'Connect'.")
        status_bar = ttk.Label(master, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        print("DEBUG: UI elements created.")
        print("DEBUG: ModelViewerApp initialization complete.")

    def on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        if sys.platform == "darwin":
            scroll_units = -1 * event.delta
            self.canvas.yview_scroll(scroll_units, "units")
        elif sys.platform.startswith('linux'):
            if event.num == 4: self.canvas.yview_scroll(-1, "units")
            elif event.num == 5: self.canvas.yview_scroll(1, "units")
        else:
             scroll_units = -1 * int(event.delta / 120)
             self.canvas.yview_scroll(scroll_units, "units")


    # --- Core Logic Functions ---
    # _connect_api, connect_thread, _connect_sync, _update_gui_after_connect,
    # _show_api_error, display_selected_models_action remain unchanged

    def _connect_api(self):
        # (This function remains the same as the previous version)
        print("DEBUG: Thread: Starting API call for connect...")
        url = 'https://api.venice.ai/api/v1/models'
        headers = {'Accept': 'application/json', 'Authorization': f'Bearer {API_KEY}'}
        params = {'type': 'all'}
        try:
            self.master.after(0, self.status_var.set, "Connecting to API and fetching models...")
            response = requests.get(url, headers=headers, params=params, timeout=20)
            print(f"DEBUG: Thread: API response status code: {response.status_code}")
            response.raise_for_status()
            self.models_data = response.json()
            if self.models_data and 'data' in self.models_data:
                 types = set(model.get('type', 'Unknown') for model in self.models_data['data'])
                 self.model_types = ["all"] + sorted(list(types))
                 print(f"DEBUG: Thread: Found model types: {self.model_types}")
                 self.master.after(0, self._update_gui_after_connect, True)
            else:
                 print("DEBUG: Thread: API response missing 'data' key or is empty.")
                 self.models_data = None
                 self.master.after(0, self._update_gui_after_connect, False)
            return True
        except requests.exceptions.RequestException as e:
            self.models_data = None
            error_message = f"API Connection Error: {e}"
            print(f"ERROR: Thread: {error_message}")
            self.master.after(0, self._show_api_error, error_message)
            self.master.after(0, self._update_gui_after_connect, False)
            return False

    def _fetch_style_presets(self):
        print("DEBUG: Thread: Starting API call for style presets...")
        url = 'https://api.venice.ai/api/v1/image/styles'
        headers = {'Accept': 'application/json', 'Authorization': f'Bearer {API_KEY}'}
        try:
            self.master.after(0, self.status_var.set, "Fetching style presets...")
            response = requests.get(url, headers=headers, timeout=20)
            print(f"DEBUG: Thread: API response status code: {response.status_code}")
            response.raise_for_status()
            style_presets = response.json()
            if style_presets and 'data' in style_presets:
                self.master.after(0, self._update_gui_after_fetch_style_presets, style_presets['data'])
            else:
                print("DEBUG: Thread: API response missing 'data' key or is empty.")
                self.master.after(0, self._update_gui_after_fetch_style_presets, [])
        except requests.exceptions.RequestException as e:
            error_message = f"API Connection Error: {e}"
            print(f"ERROR: Thread: {error_message}")
            self.master.after(0, self._show_api_error, error_message)
            self.master.after(0, self._update_gui_after_fetch_style_presets, [])

    def _update_gui_after_fetch_style_presets(self, style_presets):
        print(f"DEBUG: MainThread: Running _update_gui_after_fetch_style_presets with {len(style_presets)} presets.")
        self.clear_display_frame()
        if style_presets:
            ttk.Label(self.display_frame, text="Available Style Presets:").pack(pady=10)
            for preset in style_presets:
                ttk.Label(self.display_frame, text=preset).pack(pady=5)
        else:
            ttk.Label(self.display_frame, text="No style presets available.", foreground="orange").pack(pady=20)
        self.on_frame_configure()
        print("DEBUG: MainThread: _update_gui_after_fetch_style_presets complete.")

    def view_style_presets_action(self):
        print("DEBUG: View Style Presets button clicked.")
        if self.models_data is None:
            print("DEBUG: No model data available to display.")
            messagebox.showwarning("No Data", "Please connect to the API first using the 'Connect' button.")
            return
        thread = threading.Thread(target=self._fetch_style_presets, daemon=True)
        thread.start()

    def connect_thread(self):
        # (This function remains the same as the previous version)
        print("DEBUG: Connect button clicked, starting thread.")
        self.connect_button.config(state=tk.DISABLED)
        self.display_button.config(state=tk.DISABLED)
        self.type_combobox.config(state=tk.DISABLED)
        self.clear_display_frame()
        ttk.Label(self.display_frame, text="Connecting...").pack(pady=20)
        self.on_frame_configure()

        thread = threading.Thread(target=self._connect_sync, daemon=True)
        thread.start()

    def _connect_sync(self):
        # (This function remains the same as the previous version)
        print("DEBUG: Thread: Running _connect_sync")
        self._connect_api()
        print("DEBUG: Thread: API call finished in thread.")

    def _update_gui_after_connect(self, success):
        # (This function remains mostly the same, but clears frame differently)
        print(f"DEBUG: MainThread: Running _update_gui_after_connect, success={success}")
        self.connect_button.config(state=tk.NORMAL)
        self.clear_display_frame()

        if success and self.models_data:
             print("DEBUG: MainThread: Updating combobox values and enabling controls.")
             self.type_combobox['values'] = self.model_types
             self.type_combobox.set("all")
             self.type_combobox.config(state="readonly")
             self.display_button.config(state=tk.NORMAL)
             self.view_styles_button.config(state=tk.NORMAL)
             self.status_var.set("Connected. Select model type and click 'Display Models'.")
             ttk.Label(self.display_frame, text="Select model type and click 'Display Models'.").pack(pady=20)
        else:
             print("DEBUG: MainThread: Connect failed or no data, keeping controls disabled.")
             self.type_combobox['values'] = ["all"]
             self.type_combobox.set("all")
             self.type_combobox.config(state=tk.DISABLED)
             self.display_button.config(state=tk.DISABLED)
             self.view_styles_button.config(state=tk.DISABLED)
             self.status_var.set("Connection failed. Check logs or API key.")
             ttk.Label(self.display_frame, text="Connection failed. Cannot display models.", foreground="red").pack(pady=20)

        self.on_frame_configure()
        print("DEBUG: MainThread: _update_gui_after_connect complete.")


    def _show_api_error(self, error_message):
         # (This function remains the same as the previous version)
         print(f"DEBUG: MainThread: Showing API error messagebox.")
         messagebox.showerror("API Error", error_message)

    def display_selected_models_action(self):
        # (This function remains the same as the previous version)
        print("DEBUG: Display Models button clicked.")
        if self.models_data is None:
            print("DEBUG: No model data available to display.")
            messagebox.showwarning("No Data", "Please connect to the API first using the 'Connect' button.")
            return
        self.display_filtered_models()

    # --- Display Logic ---

    def clear_display_frame(self):
        """Destroys all widgets inside the display_frame."""
        print("DEBUG: Clearing display frame...")
        for widget in self.display_frame.winfo_children():
            widget.destroy()
        self.canvas.yview_moveto(0)

    def _add_separator(self, parent, row):
         """Adds a separator line."""
         sep = ttk.Separator(parent, orient='horizontal')
         sep.grid(row=row, column=0, columnspan=2, sticky='ew', padx=5, pady=8)
         return row + 1

    def _add_section_heading(self, parent, text, row):
         """Adds an italic section heading."""
         heading = ttk.Label(parent, text=text, style="Section.TLabel")
         heading.grid(row=row, column=0, columnspan=2, sticky='nw', padx=5, pady=(8, 1))
         return row + 1

    def _add_detail(self, parent, key, value, row):
        """Helper function to add a key-value label pair to the grid."""
        # Use the ttk Style for the key label
        key_label = ttk.Label(parent, text=f"{key}:", style="Key.TLabel")
        key_label.grid(row=row, column=0, sticky="ne", padx=(10, 2), pady=1) # Right align keys

        # Determine value text and color
        value_text = str(value) if value is not None else "N/A"
        value_color = {} # Empty dict means default color
        if isinstance(value, bool):
            if value:
                value_text = "Yes"
                value_color = {'foreground': COLOR_BOOL_YES}
            else:
                value_text = "No"
                value_color = {'foreground': COLOR_BOOL_NO}

        value_label = ttk.Label(parent, text=value_text, wraplength=500, justify=tk.LEFT, **value_color) # Apply color if needed
        value_label.grid(row=row, column=1, sticky="nw", padx=2, pady=1)
        return row + 1 # Return next available row

    def display_filtered_models(self):
        """Clears and updates the display_frame with structured model info."""
        selected_type = self.model_type_var.get()
        print(f"DEBUG: Displaying models for type: {selected_type}")
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

                # --- Create LabelFrame for this model ---
                # Use model_id as the label text for the frame
                model_frame = ttk.LabelFrame(self.display_frame, text=f" {model_id} ", padding=10) # Add space around title
                model_frame.pack(pady=10, padx=5, fill=tk.X, expand=True) # Increased pady
                model_frame.columnconfigure(1, weight=1) # Allow value column to expand

                # --- Add details using helper ---
                current_row = 0
                # Basic Info Section (no heading needed)
                current_row = self._add_detail(model_frame, "Type", model_type, current_row)
                if model_type == "text":
                    current_row = self._add_detail(model_frame, "Context Tokens", model_spec.get('availableContextTokens'), current_row)

                # Separator
                current_row = self._add_separator(model_frame, current_row)

                # --- Type-specific sections ---
                if model_type == "text":
                    # Capabilities Section
                    caps = model_spec.get('capabilities')
                    if caps and isinstance(caps, dict):
                        current_row = self._add_section_heading(model_frame, "Capabilities", current_row)
                        for key, value in caps.items():
                           current_row = self._add_detail(model_frame, key, value, current_row)
                        current_row = self._add_separator(model_frame, current_row)

                    # Constraints Section
                    const = model_spec.get('constraints')
                    if const and isinstance(const, dict):
                        current_row = self._add_section_heading(model_frame, "Constraints", current_row)
                        for key, value in const.items():
                             if isinstance(value, dict):
                                 for sub_key, sub_value in value.items():
                                      current_row = self._add_detail(model_frame, f"{key} ({sub_key})", sub_value, current_row)
                             else:
                                 current_row = self._add_detail(model_frame, key, value, current_row)
                        current_row = self._add_separator(model_frame, current_row)

                elif model_type == "image":
                    # Constraints Section
                    const = model_spec.get('constraints')
                    if const and isinstance(const, dict):
                        current_row = self._add_section_heading(model_frame, "Constraints", current_row)
                        for key, value in const.items():
                            if key == 'steps' and isinstance(value, dict):
                                for sub_key, sub_value in value.items():
                                     current_row = self._add_detail(model_frame, f"{key} ({sub_key})", sub_value, current_row)
                            else:
                                current_row = self._add_detail(model_frame, key, value, current_row)
                        current_row = self._add_separator(model_frame, current_row)

                elif model_type == "tts":
                     # Voices Section (Treat as list for now)
                     voices = model_spec.get('voices', [])
                     if voices:
                         current_row = self._add_section_heading(model_frame, "Voices", current_row)
                         # Display as comma-separated list for now, adjust wraplength if needed
                         current_row = self._add_detail(model_frame, "Available", ", ".join(voices), current_row)
                         current_row = self._add_separator(model_frame, current_row)


                # Traits Section (Common)
                traits = model_spec.get('traits', [])
                if traits:
                     current_row = self._add_section_heading(model_frame, "Traits", current_row)
                     current_row = self._add_detail(model_frame, "Assigned", ", ".join(traits), current_row)
                     current_row = self._add_separator(model_frame, current_row)


                # Other Info Section
                # Check if any of these fields exist before adding heading
                other_info_exists = any(k in model_spec for k in ['modelSource', 'beta', 'offline'])
                if other_info_exists:
                    current_row = self._add_section_heading(model_frame, "Other Info", current_row)
                    current_row = self._add_detail(model_frame, "Source", model_spec.get('modelSource'), current_row)
                    current_row = self._add_detail(model_frame, "Beta", model_spec.get('beta'), current_row)
                    current_row = self._add_detail(model_frame, "Offline", model_spec.get('offline'), current_row)
                # No separator needed after the last section


        if not found_models:
            ttk.Label(self.display_frame, text=f"No models found for the selected type: '{selected_type}'", foreground="orange").pack(pady=20)

        # Update scrollregion
        self.master.after(50, self.on_frame_configure) # Use slightly longer delay after adding many widgets
        print("DEBUG: Display frame updated with model widgets.")


# --- Run the Application ---
if __name__ == "__main__":
    print("DEBUG: Script starting...")
    try:
        print("DEBUG: Creating main Tk window...")
        root = tk.Tk()
        # --- Theme Application (Optional) ---
        # Ttk comes with themes, 'clam' or 'alt' often look better than default
        s = ttk.Style()
        try:
            # Try themes available on most platforms
            if sys.platform == "win32":
                s.theme_use('vista') # Or 'xpnative'
            elif sys.platform == "darwin":
                 s.theme_use('aqua') # Default on mac, but explicit doesn't hurt
            else:
                 s.theme_use('clam') # Good default for linux
        except tk.TclError:
            print("DEBUG: Selected theme not available, using default.")
        # ------------------------------------

        print("DEBUG: Tk window created.")
        print("DEBUG: Instantiating ModelViewerApp...")
        app = ModelViewerApp(root)
        print("DEBUG: ModelViewerApp instantiated.")
        print("DEBUG: Starting Tk main event loop...")
        root.mainloop()
        print("DEBUG: Tk main event loop finished.")
    except Exception as e:
        print("\n--- UNHANDLED EXCEPTION CAUGHT ---")
        print(f"An error occurred: {e}")
        print("Traceback:")
        traceback.print_exc()
        print("--- END OF EXCEPTION ---")
        input("Press Enter to exit...") # Keep terminal open
