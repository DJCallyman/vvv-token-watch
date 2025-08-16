# Implementation Plan

[Overview]
Add multi-currency support (USD and AUD) to the token price viewer while enhancing UI usability through dynamic layout improvements and user-configurable parameters.

This implementation addresses the hardcoded USD-only display by creating a flexible currency system that maintains the application's dark theme aesthetic while significantly improving data visibility. The changes will allow users to simultaneously monitor token values in both USD and AUD, with proper localization formatting and dynamic holding amount configuration. These improvements maintain backward compatibility with existing functionality while introducing new user-facing features that enhance the practical utility of the application for Australian users.

[Types]  
Define structured data types for currency management and UI state.

Detailed type definitions:
- `CurrencyConfig`: Named tuple containing currency_code (str), symbol (str), and label (str)
- `PriceData`: Dictionary structure with keys for 'usd' and 'aud' containing price and total_value
- `UIState`: Tracking variables for current holding amount and active currency display mode

[Files]
Refactor currency handling across multiple application components.

Detailed breakdown:
- **New files to be created**:
  - `assorted_coding/vvv_token_watch/currency_utils.py`: Contains currency formatting and conversion logic
  - `assorted_coding/vvv_token_watch/ui_components.py`: Modular UI components for currency display

- **Existing files to be modified**:
  - `assorted_coding/vvv_token_watch/combined_app.py`:
    * Update configuration section with multi-currency support
    * Refactor price display creation and update logic
    * Add dynamic holding amount input field
    * Implement dual-currency formatting
    * Enhance status messaging with currency context

- **Configuration file updates**:
  - Add `COINGECKO_CURRENCIES = ['usd', 'aud']` to configuration
  - Replace hardcoded `COINGECKO_VS_CURRENCY` with multi-currency parameter

[Functions]
Implement new currency handling functions while modifying existing price update logic.

Detailed breakdown:
- **New functions**:
  - `format_currency(value: float, currency: str) -> str` (currency_utils.py)
    * Returns properly formatted currency string with symbol and decimal places
    * Handles AUD-specific formatting (A$) vs USD ($)
  - `create_currency_display(parent, currency_config)` (ui_components.py)
    * Creates standardized UI component for a single currency display
  - `update_holding_amount(event)` (combined_app.py)
    * Validates and processes user input for holding amount

- **Modified functions**:
  - `get_coingecko_price()` (combined_app.py)
    * Updated to request multiple currencies: `vs_currencies=usd,aud`
    * Returns dictionary with prices for all configured currencies
  - `update_price_label()` (combined_app.py)
    * Processes multiple currency values
    * Updates both USD and AUD display components
    * Handles partial API failures (e.g., one currency succeeds while other fails)
  - `_create_price_display()` (combined_app.py)
    * Redesigned layout with dual-currency display
    * Added input field for dynamic holding amount
    * Implemented visual separation between currency displays

[Classes]
Enhance CombinedViewerApp with multi-currency capabilities.

Detailed breakdown:
- **Modified classes**:
  - `CombinedViewerApp` (combined_app.py)
    * Added `self.currencies = ['usd', 'aud']` configuration
    * Added `self.holding_amount_var = tk.StringVar(value=str(COINGECKO_HOLDING_AMOUNT))`
    * Added `self.price_data = {'usd': {'price': None, 'total': None}, 'aud': {'price': None, 'total': None}}`
    * Added new UI elements:
      - Dual-currency display frames with clear visual separation
      - Entry field for holding amount with validation
      - Currency-specific status indicators
    * Modified initialization to set up multi-currency UI components
    * Enhanced error handling to differentiate between currency-specific failures

[Dependencies]
No new external dependencies required.

Details:
- CoinGecko API already supports multiple currencies in single request
- Existing tkinter and requests libraries sufficient for implementation
- No version changes needed for current dependencies

[Testing]
Verify multi-currency functionality through targeted test cases.

Test file requirements:
- **New test cases**:
  - Verify both USD and AUD values display when API returns both
  - Confirm proper formatting for AUD (A$) vs USD ($)
  - Validate holding amount input accepts valid numbers only
  - Test partial API failure (one currency succeeds, other fails)
  - Check layout maintains integrity at minimum window size

- **Existing test modifications**:
  - Update price display tests to handle dual-currency output
  - Modify status message assertions to include currency context
  - Enhance UI layout tests to verify new component positioning

[Implementation Order]
Sequential implementation ensures stable intermediate states.

Numbered steps:
1. Create currency utility module with formatting functions
2. Update configuration section with multi-currency parameters
3. Modify CoinGecko API call to request multiple currencies
4. Implement data structures for storing multiple currency values
5. Redesign price display UI with dual-currency layout
6. Add dynamic holding amount input field with validation
7. Update price update logic to handle multiple currencies
8. Implement error handling for partial currency failures
9. Enhance status messages with currency-specific information
10. Verify layout responsiveness across window sizes
