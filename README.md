# vvv_token_watch

A monitoring application for Venice AI models, cryptocurrency prices, and API usage tracking.

## Features

- Monitor Venice AI model availability and status
- View model details (type, capabilities, constraints, etc.)
- Monitor cryptocurrency prices from CoinGecko
- Support for multiple currencies
- Dark and light theme options
- API usage tracking for all API keys
- Display of overall VCU/USD balance and limit usage
- Per-key usage visualization with 7-day trailing metrics
- Admin key support for accessing all API key data

## Requirements

- Python 3.8+
- PySide6
- requests

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root with your API keys:

```env
VENICE_API_KEY=your_venice_api_key
VENICE_ADMIN_KEY=your_admin_api_key  # Required for usage tracking of all keys
COINGECKO_TOKEN_ID=your_token_id
COINGECKO_CURRENCIES=usd,aud
COINGECKO_HOLDING_AMOUNT=1000
THEME_MODE=dark
USAGE_REFRESH_INTERVAL_MS=30000  # Refresh interval for usage data in milliseconds
```

## Usage

```bash
python combined_app.py
```

## Development

- Run tests: `python -m unittest discover`
- Format code: `black .`
- Check style: `flake8`
