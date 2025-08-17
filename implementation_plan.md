# Implementation Plan

[Overview]
Migrate the Venice AI Models & CoinGecko Price Viewer application from Tkinter to PySide6 to modernize the UI framework while preserving all functionality and visual styling. This refactoring will improve maintainability, leverage Qt's robust features, and provide better cross-platform consistency.

[Types]  
Define Qt-specific type aliases for clarity in signal/slot communication.

```python
# Type definitions for signal communication
from typing import TypedDict, Union, Callable

class APIResult(TypedDict):
    success: bool
    data: Union[dict, list, None]
    error: Union[str, None]
```

[Files]
Document file modifications required for the migration.

- **Modified**: `vvv_token_watch/combined_app.py` (complete framework replacement)
- **New**: `vvv_token_watch/qt_utils.py` (optional helper module for Qt-specific utilities)
- **Modified**: `vvv_token_watch/requirements.txt` (add PySide6 dependency)

[Functions]
Document function modifications and additions.

### New Functions
- `setup_main_window()`: Initialize Qt application structure
- `create_price_display_layout()`: Build CoinGecko price section with Qt widgets
- `create_model_viewer_layout()`: Rebuild model viewer with QScrollArea
- `setup_signals()`: Connect Qt signals/slots for event handling
- `apply_qss_styles()`: Apply styling via Qt Style Sheets

### Modified Functions
- `_create_price_display()` → `create_price_display_layout()`: Complete rewrite using QVBoxLayout/QHBoxLayout
- `_create_model_viewer()` → `create_model_viewer_layout()`: Replace Tkinter canvas with QScrollArea
- `process_api_queue()` → `handle_api_result()`: Convert to signal/slot pattern
- `_bind_mouse_wheel()` → Remove (handled automatically by QScrollArea)

[Classes]
Document class modifications and additions.

### Modified Class
**CombinedViewerApp** (now inherits from `QMainWindow` instead of Tkinter root)

Key changes:
- Replace Tkinter geometry managers with Qt layout system
- Implement custom signal for thread-safe API communication:
  ```python
  class WorkerSignals(QObject):
      result = Signal(dict)
  ```
- Replace ttk widgets with Qt equivalents:
  - `ttk.Frame` → `QFrame`
  - `ttk.Label` → `QLabel`
  - `ttk.Button` → `QPushButton`
  - `ttk.Combobox` → `QComboBox`
- Replace manual scrollbar management with `QScrollArea`

### New Classes
**ModelDisplayWidget** (QFrame subclass for individual model cards)
- Handles layout and styling of model information
- Implements mouse event handling for interaction

[Dependencies]
Document dependency modifications.

- Add `PySide6>=6.7.0` to requirements.txt
- Remove Tkinter-specific dependencies (none explicitly listed, but implied)

[Testing]
Document testing approach.

- Verify all API functionality works identically
- Confirm visual appearance matches original (colors, spacing, layout)
- Test mouse wheel scrolling in model viewer
- Validate thread safety during API calls
- Check configuration loading and error handling

[Implementation Order]
Document the logical implementation sequence.

1. Set up basic Qt application structure with window and main layout
2. Migrate price display section with currency formatting
3. Implement model viewer with QScrollArea and dynamic content
4. Convert threading model to Qt signals/slots
5. Apply Qt Style Sheets to match original visual design
6. Test and debug edge cases (empty states, API errors)
7. Update documentation and requirements
8. Final validation and documentation update
