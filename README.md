# VVV Token Watch

A PySide6 desktop application for monitoring Venice AI API usage, model catalogs, and cryptocurrency prices (Venice VVV & DIEM tokens).

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

### Venice AI API Monitoring
- **Real-time API Usage Tracking** - Monitor usage across all API keys
- **Balance & Billing Dashboard** - Hero card display with balance, daily limits, and usage trends
- **Per-Key Usage Leaderboard** - 7-day trailing metrics with visual indicators
- **Admin Key Support** - Access comprehensive billing data with Admin API keys
- **Cost Optimization** - Automated recommendations to reduce API costs
- **Cache Tracking** - Monitor cache hit rates and savings

### Model Management
- **Model Catalog Browser** - Browse complete Venice AI model catalog
- **Detailed Specifications** - View capabilities, constraints, and pricing
- **Advanced Filtering** - Filter by type (text, image, audio) and traits
- **Real-time Search** - Search models by ID, type, or traits
- **Model Comparison** - Compare pricing and features across models
- **Style Presets** - View available image generation styles

### Cryptocurrency Price Tracking
- **Venice Token (VVV)** - Real-time price monitoring in USD/AUD
- **DIEM Token** - Secondary token price tracking
- **Portfolio Value** - Calculate total value based on holdings
- **Price Alerts** - Visual indicators for price changes
- **Auto-refresh** - Configurable update intervals

### User Experience
- **System Tray Integration** - Minimize to tray with native notifications
- **Dark/Light Themes** - Full theme support with signal-based updates
- **Keyboard Shortcuts** - Quick navigation with hotkeys
- **Responsive UI** - Non-blocking updates using background threads
- **Model Search** - Instant search across all models
- **Status Bar** - Real-time backend process status indicators

### macOS Integration
- **Native App Bundle** - Build as standalone macOS application
- **Menu Bar Support** - Proper macOS menu integration
- **Code Signing** - Support for signed app distribution
- **DMG Creation** - Build distributable disk images

## Requirements

- Python 3.8+
- PySide6 >= 6.0.0
- requests >= 2.32.0
- python-dotenv >= 1.0.0
- matplotlib >= 3.7.0 (for charts)
- tenacity >= 8.2.0 (for retries)

## Installation

### Quick Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/DJCallyman/vvv-token-watch.git
cd vvv-token-watch

# Run the setup wizard
python setup.py
```

The setup wizard will:
- ✓ Check Python version (3.8+ required)
- ✓ Create virtual environment
- ✓ Install all dependencies
- ✓ Guide you through API key configuration
- ✓ Test your Venice Admin key
- ✓ Create `.env` file with proper settings

### Manual Setup

#### macOS/Linux

```bash
# Clone repository
git clone https://github.com/DJCallyman/vvv-token-watch.git
cd vvv-token-watch

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your API keys
```

#### Windows

```cmd
git clone https://github.com/DJCallyman/vvv-token-watch.git
cd vvv-token-watch

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

copy .env.example .env
# Edit .env with your API keys
```

## Configuration

### Getting Your API Keys

1. Visit https://venice.ai/settings/api
2. Create an **Admin** API key (NOT "Inference Only")
   - Click "Create API Key"
   - Set description: "VVV Token Watch"
   - Select key type: **Admin**
   - **Save immediately** (shown only once!)

**⚠️ Important**: Admin keys are required for billing/usage monitoring. "Inference Only" keys will fail with 401 Unauthorized.

### Configuration File

Create `.env` file with your settings:

```env
# REQUIRED: Venice Admin API Key
VENICE_ADMIN_KEY=your_admin_key_here

# CoinGecko Settings
COINGECKO_HOLDING_AMOUNT=2750    # Your VVV holdings
DIEM_HOLDING_AMOUNT=0            # Your DIEM holdings

# Application Settings
THEME_MODE=dark                       # 'dark' or 'light'
MINIMIZE_TO_TRAY=true                 # Minimize to system tray
ENABLE_NOTIFICATIONS=true             # Native notifications
USAGE_REFRESH_INTERVAL_MS=30000       # 30 seconds
COINGECKO_REFRESH_INTERVAL_MS=60000   # 1 minute
```

See [.env.example](.env.example) for complete configuration options.

## Usage

### Running from Source

#### macOS/Linux
```bash
source venv/bin/activate
python run.py
```

#### Windows
```cmd
venv\Scripts\activate
python run.py
```

### Keyboard Shortcuts

- **Cmd/Ctrl + 1-6** - Switch between tabs
- **Cmd/Ctrl + R** - Refresh all data
- **Cmd/Ctrl + F** - Focus model search
- **Cmd/Ctrl + T** - Toggle theme
- **Cmd/Ctrl + Q** - Quit application

### System Tray

When `MINIMIZE_TO_TRAY=true`:
- Minimizing the window hides it to the system tray
- Click the tray icon to restore the window
- Right-click tray icon for menu (Show/Refresh/Quit)
- Notifications appear for price alerts

## Building macOS App

### Prerequisites
- macOS 10.14+
- Python 3.8+
- Xcode Command Line Tools (for code signing)

### Build Steps

```bash
# Install PyInstaller if not already installed
pip install pyinstaller

# Build the app (unsigned)
./build_macos.sh

# Build with code signing (requires Apple Developer account)
export CODESIGN_IDENTITY="Developer ID Application: Your Name"
./build_macos.sh
```

Output:
- `dist/VVV Token Watch.app` - Application bundle
- `dist/VVV Token Watch-1.0.0.dmg` - Installer DMG (optional)

### Distribute

```bash
# Create zip for distribution
cd dist
zip -r "VVV Token Watch.zip" "VVV Token Watch.app"
```

## Testing

Install development dependencies first:

```bash
pip install -r requirements-dev.txt
```

Run the comprehensive test suite:

```bash
# Run all tests
python run_tests.py

# Run with coverage report
python run_tests.py -c

# Run specific test file
python -m pytest tests/test_config.py -v

# Alternative: Install test dependencies directly
pip install pytest pytest-cov pytest-mock
```

Test coverage includes:
- Configuration management
- Theme system
- Utility functions
- API client operations
- Worker thread management

## Project Structure

```
vvv-token-watch/
├── src/                          # Source code
│   ├── main.py                   # Main application entry
│   ├── config/                   # Configuration modules
│   ├── core/                     # API clients & workers
│   ├── utils/                    # Utility functions
│   └── widgets/                  # UI components
├── tests/                        # Test suite
├── data/                         # Data storage
├── assets/                       # Images & icons
├── run.py                        # Application launcher
├── setup.py                      # Setup wizard
├── build_macos.sh               # macOS build script
├── requirements.txt             # Dependencies
└── .env.example                 # Configuration template
```

## Architecture

### Multi-threaded Design
- **API Workers** - Background threads for API calls
- **Price Workers** - Real-time price updates
- **Usage Workers** - Usage data tracking
- **Main Thread** - UI updates and user interaction

### Theme System
- Signal-based theme changes
- Persistent theme selection
- Real-time UI updates
- QPalette integration

### Error Handling
- Centralized error handler
- Graceful degradation
- User-friendly error messages
- Comprehensive logging

## Logging

Application logs are stored with automatic rotation:

- `app.log` - Main application log (max 10MB, 5 backups)
- `error_log.txt` - Error-only log (max 5MB, 3 backups)

View logs:
```bash
tail -f app.log
tail -f error_log.txt
```

## Troubleshooting

### Common Issues

**401 Unauthorized Error**
- Ensure you're using an **Admin** API key, not "Inference Only"
- Check that VENICE_ADMIN_KEY is set correctly in `.env`

**Window Appears Blank After Minimize**
- This was a bug in earlier versions - update to latest
- Check that MINIMIZE_TO_TRAY is configured properly

**App Won't Fully Quit**
- Click the tray icon and select "Quit"
- Or right-click dock icon and select "Quit"
- This was fixed in recent versions

**Tests Failing**
- Ensure you're in the project root directory
- Run `python run_tests.py --install-deps` first
- Some tests require the cache file to exist

### Getting Help

- Check the [TRAY_BUGFIX.md](TRAY_BUGFIX.md) for system tray issues
- Review [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for recent changes
- Open an issue on GitHub with:
  - Error messages from logs
  - Python version (`python --version`)
  - Operating system and version

## Development

### Code Style
- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings to public methods

### Running Tests
```bash
# Run tests
python run_tests.py

# With coverage
python run_tests.py -c

# Specific file
python -m pytest tests/test_config.py -v
```

### Adding Features
1. Create feature branch: `git checkout -b feature/new-feature`
2. Add tests for new functionality
3. Implement feature
4. Run test suite: `python run_tests.py`
5. Submit pull request

## API Reference

### Venice AI API
- Models: `GET /api/v1/models`
- Usage: `GET /api/v1/billing/usage`
- API Keys: `GET /api/v1/api_keys`
- Rate Limits: `GET /api/v1/api_keys/rate_limits`

See [venice-api-docs](https://github.com/venice-ai/venice-api-docs) for complete API documentation.

## License

MIT License - See [LICENSE](LICENSE) for details

## Credits

- Venice AI API - https://venice.ai
- CoinGecko API - https://coingecko.com
- PySide6 - Qt for Python
- Contributors and testers

## Changelog

### v1.0.0 (Current)
- ✅ System tray integration with minimize to tray
- ✅ Native notifications support
- ✅ Model search functionality
- ✅ Keyboard shortcuts
- ✅ Log rotation (prevents 1GB+ files)
- ✅ Comprehensive test suite
- ✅ macOS app bundle support
- ✅ Dark/light theme system
- ✅ Real-time price tracking
- ✅ Usage monitoring dashboard
- ✅ Cost optimization recommendations

---

**Note**: This project is not affiliated with Venice AI. It's an independent monitoring tool for Venice AI API users.
