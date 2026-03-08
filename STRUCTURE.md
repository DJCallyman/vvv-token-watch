# VVV Token Watch — Project Structure

The project has two deployable applications that share core Venice API logic:

1. **Desktop app** (`src/`, `run.py`) — PySide6 Qt6 application
2. **Web app** (`backend/`, `web/`) — FastAPI + Next.js, Docker-packaged

---

## Repository Layout

```
vvv-token-watch/
│
├── run.py                        # Desktop app entry point (adds src/ to path)
├── requirements.txt              # Desktop app Python dependencies
├── requirements-dev.txt          # Test/dev dependencies
├── .env.example                  # Environment variable reference
├── dev.sh                        # Local development launcher (web app)
├── docker-compose.dev.yml        # Dev: PostgreSQL only in Docker
│
├── src/                          # Desktop app source
│   ├── main.py                   # Main window (QMainWindow)
│   ├── config/
│   │   ├── config.py             # Config loader (reads .env via python-dotenv)
│   │   └── theme.py              # Dark/light QPalette theme system
│   ├── core/
│   │   ├── venice_api_client.py  # Base HTTP client (retry, auth)
│   │   ├── usage_tracker.py      # Balance + billing usage fetchers
│   │   ├── web_usage.py          # Web app usage tracking
│   │   └── unified_usage.py      # Unified usage dataclass
│   ├── services/
│   │   ├── exchange_rate_service.py
│   │   └── venice_key_management.py
│   ├── widgets/                  # QWidget UI components
│   ├── analytics/                # Usage reports, model comparison
│   ├── utils/                    # Currency formatting, date helpers
│   └── cli/                      # CLI model browser
│
├── backend/                      # Web app — FastAPI backend
│   ├── main.py                   # FastAPI app, lifespan, middleware
│   ├── config.py                 # Pydantic Settings (reads .env)
│   ├── database.py               # SQLAlchemy async engine + init_db
│   ├── requirements.txt          # Backend Python dependencies
│   ├── core/
│   │   ├── venice_api_client.py  # HTTP client (shared logic with src/)
│   │   ├── usage_tracker.py      # Epoch-aware billing fetcher (net of refunds)
│   │   └── unified_usage.py
│   ├── services/
│   │   ├── exchange_rate_service.py
│   │   └── venice_key_management.py
│   └── api/routes/
│       ├── health.py             # GET /api/health
│       ├── balance.py            # GET /api/balance
│       ├── usage.py              # GET /api/usage/daily, /keys, /history
│       ├── prices.py             # GET /api/prices
│       └── models.py             # GET /api/models
│
├── web/                          # Web app — Next.js frontend
│   ├── app/                      # App Router pages
│   │   ├── page.tsx              # Dashboard
│   │   ├── usage/page.tsx        # Usage page
│   │   ├── balance/page.tsx      # Balance page
│   │   └── prices/page.tsx       # Prices page
│   ├── components/
│   │   ├── dashboard/            # Dashboard, HeroBalanceCard, TodayUsageCard, PriceCards, UsageLeaderboardCard
│   │   ├── usage/                # UsageView
│   │   ├── balance/              # BalanceView
│   │   ├── layout/               # Sidebar, Header
│   │   └── ui/                   # shadcn/ui primitives
│   ├── lib/
│   │   ├── api.ts                # Typed API client
│   │   ├── hooks.ts              # React Query hooks
│   │   └── utils.ts              # formatCurrency, formatNumber, cn
│   └── next.config.js            # /api/* rewrites to FastAPI on port 8000
│
├── docker/
│   ├── Dockerfile                # Multi-stage: Next.js build → Python runtime
│   ├── docker-compose.yml        # Production: app + PostgreSQL
│   ├── start.sh                  # Container entrypoint (uvicorn + node server.js)
│   └── .env.example
│
├── unraid/
│   └── vvv-token-watch.xml       # Unraid Community Applications template
│
├── data/                         # Runtime data (gitignored except structure)
│   ├── logs/                     # app.log (persistent across container restarts)
│   └── *.json                    # Caches (model cache, billing cache, etc.)
│
├── tests/                        # Test suite (pytest)
├── scripts/                      # (empty — ad-hoc inspection scripts go here temporarily)
└── assets/                       # Icons and images
```

---

## Key Design Notes

### Billing usage is epoch-based, not UTC-date-based
The Venice API epoch resets at a fixed UTC time each day (not midnight for all timezones). The backend queries `/api_keys/rate_limits` to find `nextEpochBegins`, subtracts 24h to get epoch start, then queries `/billing/usage` across that window. Amounts are netted (charges negative, refunds positive) so cancelled jobs don't inflate consumed totals.

### Desktop app threading
All API calls MUST run in `QThread` workers — never from the main thread. Workers emit typed dataclass objects via Qt signals. See `src/core/usage_tracker.py` for worker patterns.

### Import paths
- Desktop app: `from src.config.config import Config`
- Web backend: `from backend.config import get_settings`
- Always run the desktop app via `python run.py` (not `python src/main.py`)

### Portfolio value
VVV and DIEM holdings are tracked separately. The prices endpoint returns `portfolio.vvv_value_usd` and `portfolio.diem_value_usd` as distinct fields, not a combined total.
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
