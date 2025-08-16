# Venice Token Watch - Multi-Currency Price Viewer

![Dark Theme UI Screenshot](screenshot.png)

A desktop application for monitoring cryptocurrency prices with dual-currency support (USD and AUD), featuring real-time price updates and dynamic holding calculations.

## Features

- **Dual-Currency Display**: Monitor prices simultaneously in USD and AUD with visual separation
- **Dynamic Holding Calculator**: Input your token holdings to see real-time portfolio value in both currencies
- **Responsive UI**: Clean dark-themed interface that adapts to window size changes
- **Currency-Specific Formatting**: Proper symbol display (USD: $, AUD: A$) with localization
- **Error Handling**: Clear status messages for API failures or partial currency data
- **Live Updates**: Automatic price refreshes at configurable intervals
- **Visual Differentiation**: Color-coded status indicators for normal operation and errors

## Installation

1. Ensure Python 3.8+ is installed
2. Install required dependencies:
```bash
pip install requests
```
3. Clone this repository or copy the project files to your local machine

## Configuration

Edit `combined_app.py` to configure:

```python
# Venice AI API Key (Load securely in real app)
VENICE_API_KEY = 'your_api_key_here'  # Replace with your actual API key

# CoinGecko Configuration
COINGECKO_TOKEN_ID = 'venice-token'  # Token ID on CoinGecko
COINGECKO_CURRENCIES = ['usd', 'aud']  # Supported currencies
COINGECKO_HOLDING_AMOUNT = 2500  # Default token holdings
COINGECKO_REFRESH_INTERVAL_MS = 60000  # Refresh interval in milliseconds (60 seconds)
```

## Usage

1. Run the application:
```bash
python combined_app.py
```
2. The application will:
   - Connect to CoinGecko API to fetch current prices
   - Display prices in USD and AUD side-by-side in dedicated frames
   - Show calculated portfolio value based on your holdings
3. To update holdings:
   - Enter your token amount in the "Holding Amount" field
   - Press Enter or click outside the field to update calculations
4. Status bar provides:
   - Last update time
   - Currency-specific status information
   - Error messages when API requests fail

## Project Structure

```
vvv_token_watch/
├── combined_app.py       # Main application code
├── currency_utils.py     # Currency formatting functions
├── implementation_plan.md # Development roadmap and specifications
└── README.md             # This documentation
```

## Dependencies

- Python 3.8+
- requests (for API calls)
- tkinter (standard library for GUI)

## Technical Implementation

The application implements several key technical patterns:

- **Multi-Currency Data Structures**: Dictionary-based storage for price and total value per currency
- **Thread-Safe UI Updates**: Queue-based communication between API threads and main UI thread
- **Dynamic Layout Management**: Grid-based responsive design that maintains proportions
- **Partial Failure Handling**: Individual currency error states without disrupting other data
- **Validation Logic**: Input validation for holding amounts to prevent calculation errors

## Testing

The application has been verified through:
- Successful display of prices in both USD and AUD
- Dynamic recalculation when holding amount changes
- Proper handling of API errors for individual currencies
- Responsive layout across various window sizes
- Validation of input fields to prevent invalid entries

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss proposed changes.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Acknowledgments

- [CoinGecko API](https://www.coingecko.com/en/api) for cryptocurrency price data
- Tkinter for the GUI framework
