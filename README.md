# VVV Token Watch

A PySide6 desktop application for monitoring Venice AI API usage, model status, and cryptocurrency prices (Venice & DIEM tokens).

## Features

- **Venice AI API Monitoring**
  - Real-time API usage tracking for all keys
  - Balance and daily limit visualization
  - Per-key usage leaderboard with 7-day trailing metrics
  - Admin key support for accessing all API key data
  
- **Model Management**
  - Browse Venice AI model catalog
  - View model capabilities, constraints, and pricing
  - Filter by model type (chat, image, audio, etc.)
  
- **Cryptocurrency Price Tracking**
  - Venice Token (VVV) price monitoring (USD/AUD)
  - DIEM Token price monitoring (USD/AUD)
  - Customizable holding amounts
  - Auto-refresh with configurable intervals
  
- **UI/UX**
  - Dark and light theme support
  - Responsive tabbed interface
  - Real-time updates without blocking

## Requirements

- Python 3.8+
- PySide6 (Qt6)
- requests
- python-dotenv

## Installation

### Quick Setup (Recommended)

The easiest way to get started is using the interactive setup script:

```bash
# Clone the repository
git clone https://github.com/DJCallyman/vvv-token-watch.git
cd vvv-token-watch

# Run the setup wizard
python setup.py
```

The setup wizard will:
- ✓ Check your Python version (3.8+ required)
- ✓ Create a virtual environment
- ✓ Install all dependencies
- ✓ Guide you through API key configuration
- ✓ Test your Venice Admin key (optional)
- ✓ Create your `.env` file with proper settings

### Manual Setup

If you prefer manual installation:

#### macOS/Linux

```bash
# Clone the repository
git clone https://github.com/DJCallyman/vvv-token-watch.git
cd vvv-token-watch

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from template
cp .env.example .env
# Edit .env with your API keys
nano .env
```

#### Windows

```cmd
# Clone the repository
git clone https://github.com/DJCallyman/vvv-token-watch.git
cd vvv-token-watch

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from template
copy .env.example .env
# Edit .env with your API keys
notepad .env
```

## Configuration

### Getting Your API Keys

1. Go to https://venice.ai/settings/api
2. Create an **Admin** API key (NOT "Inference Only")
   - Click "Create API Key"
   - Set description: "VVV Token Watch"
   - Select key type: **Admin**
   - Save the key immediately (shown only once!)

**⚠️ Important**: Regular "Inference Only" keys will fail with 401 Unauthorized. This monitoring application requires Admin keys to access billing/usage data.

### Configuration Options

The `.env.example` file contains all available settings with documentation. Key settings:

```env
# REQUIRED: Venice Admin API Key (for usage monitoring)
VENICE_ADMIN_KEY=your_admin_api_key_here

# OPTIONAL: Venice Inference API Key (for future features)
VENICE_API_KEY=

# CoinGecko Token Tracking
COINGECKO_TOKEN_ID=venice-token
COINGECKO_HOLDING_AMOUNT=2750  # Your VVV holdings
DIEM_HOLDING_AMOUNT=0          # Your DIEM holdings

# Application Settings
THEME_MODE=dark                      # or 'light'
USAGE_REFRESH_INTERVAL_MS=30000      # 30 seconds
COINGECKO_REFRESH_INTERVAL_MS=60000  # 1 minute
```

See [.env.example](.env.example) for complete documentation of all settings.

## Usage

### macOS/Linux
```bash
# Activate virtual environment
source venv/bin/activate

# Run application
python run.py
```

### Windows
```cmd
# Option 1: Use batch launcher (auto-activates venv)
run.bat

# Option 2: Manual activation
venv\Scripts\activate
python run.py
```

## Development

- Run tests: `python -m unittest discover`
- Format code: `black .`
- Check style: `flake8`
