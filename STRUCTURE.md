# VVV Token Watch - Project Structure

## Directory Organization

```
vvv-token-watch/
├── run.py                    # Main entry point - run this to start the application
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (API keys)
├── .gitignore               # Git ignore rules
│
├── src/                      # Source code root
│   ├── __init__.py
│   ├── main.py              # Main application window
│   │
│   ├── config/              # Configuration
│   │   ├── config.py        # Application configuration (loads from .env)
│   │   └── theme.py         # UI theme configuration
│   │
│   ├── core/                # Core business logic
│   │   ├── venice_api_client.py    # Venice API client base class
│   │   ├── usage_tracker.py         # Usage tracking for API keys
│   │   ├── web_usage.py             # Web app usage tracking
│   │   └── unified_usage.py         # Unified usage data model
│   │
│   ├── services/            # External services
│   │   ├── exchange_rate_service.py  # Currency exchange rates
│   │   └── venice_key_management.py  # Venice API key management
│   │
│   ├── widgets/             # UI components
│   │   ├── action_buttons.py           # Action button components
│   │   ├── enhanced_balance_widget.py  # Balance display widget
│   │   ├── key_management_widget.py    # API key management UI
│   │   ├── price_display.py            # Price display widget
│   │   ├── status_indicator.py         # Status indicators
│   │   ├── topup_widget.py             # Top-up widget
│   │   ├── usage_leaderboard.py        # Usage leaderboard table
│   │   └── vvv_display.py              # Token display widgets
│   │
│   ├── analytics/           # Analytics and reporting
│   │   ├── usage_analytics.py    # Usage trend analysis
│   │   ├── usage_reports.py      # Usage report generation
│   │   └── model_comparison.py   # Model comparison charts
│   │
│   ├── utils/               # Utility functions
│   │   ├── utils.py         # Currency/validation utilities
│   │   └── date_utils.py    # Date formatting utilities
│   │
│   └── cli/                 # Command-line tools
│       ├── model_list_cli.py   # CLI model listing
│       └── model_viewer.py     # Model viewer widget
│
├── scripts/                 # Development/test scripts
│   ├── get_usage.py         # Test script for usage API
│   └── get_webapp_usage.py  # Test script for web usage API
│
├── data/                    # Data files
│   ├── usage_history.json   # Historical usage data
│   └── usage_reports_history.json  # Historical reports (auto-created)
│
└── tests/                   # Unit tests (to be implemented)
    └── __init__.py
```

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Configure your API keys in .env file
# See .env.example for required variables

# Run the application
python run.py
```

## Import Structure

The project uses a modular import structure. All imports reference the `src` package:

```python
# Example imports
from src.config.config import Config
from src.core.venice_api_client import VeniceAPIClient
from src.widgets.usage_leaderboard import UsageLeaderboardWidget
```

## Development

- **Adding new widgets:** Place in `src/widgets/` and update `src/widgets/__init__.py`
- **Adding new services:** Place in `src/services/` and update `src/services/__init__.py`
- **Adding new utilities:** Place in `src/utils/` and update `src/utils/__init__.py`
- **Data files:** Store in `data/` directory
- **Test scripts:** Place in `scripts/` directory
