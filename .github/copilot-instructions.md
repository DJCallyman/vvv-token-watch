# VVV Token Watch - Copilot Instructions

## Project Overview
PySide6 desktop application for monitoring Venice AI API usage, model status, and cryptocurrency prices. Built on Qt6 with threaded architecture for non-blocking API calls and real-time data updates.

## Features NOT Needed
- **Rate Limit Tracking** - Not a feature I use or need. Do not implement rate limit monitoring, `/api_keys/rate_limits/log` endpoint integration, or rate limit header parsing.

## Architecture & Core Patterns

### Threading Model (Critical)
All API calls MUST run in `QThread` workers to prevent UI freezing:
- `UsageWorker` - Venice API usage/billing data (emits: `usage_data_updated`, `balance_data_updated`, `daily_usage_updated`)
- `WebUsageWorker` - Web app usage tracking (emits: `web_usage_updated`)
- `PriceWorker` - CoinGecko price fetching (emits: `price_updated`, `error_occurred`)
- `CostAnalysisWorker` - Billing data for cost optimization (emits: `billing_data_ready`, `error_occurred`)
- `APIWorker` - Generic API requests (emits: `result` via `WorkerSignals`)

**Never call `requests.get()` directly from main thread** - always use worker threads.

### Entry Point
```bash
python run.py  # NOT python src/main.py
```
`run.py` adds `src/` to Python path, then imports `src.main:main()`. All imports use `src.` prefix: `from src.config.config import Config`

### API Client Architecture
`VeniceAPIClient` (in `src/core/venice_api_client.py`) is the base class for all API interactions:
```python
client = VeniceAPIClient(api_key)
response = client.get("/billing/usage", params={}, timeout=30)  # Has automatic retry with exponential backoff
data = response.json()
```
Provides shared config: `BASE_URL`, headers with Bearer auth, GET/POST methods with retry logic (3 attempts, exponential backoff). Workers inherit or instantiate this.

### Configuration System
`Config` class (in `src/config/config.py`) loads from `.env` via `python-dotenv`:
```python
Config.VENICE_API_KEY       # Regular API key
Config.VENICE_ADMIN_KEY     # Admin key (REQUIRED for /billing/usage endpoints)
Config.COINGECKO_TOKEN_ID   # Crypto token to track
Config.USAGE_REFRESH_INTERVAL_MS  # Polling interval (default 30s)
```
**Critical**: `/billing/usage` endpoint returns 401 with regular API keys - MUST use admin key.

## Data Models & State Management

### Core Data Structures (dataclasses)
```python
# src/core/usage_tracker.py
@dataclass
class BalanceInfo:
    diem: float
    usd: float
    daily_diem_limit: float
    daily_usd_limit: float

@dataclass
class APIKeyUsage:
    id: str
    name: str
    usage: UsageMetrics  # diem/usd
    created_at: str
    is_active: bool

# src/core/unified_usage.py
@dataclass
class UnifiedUsageEntry:
    key_name: str
    daily_diem: float
    daily_usd: float
    trailing_7day_diem: float  # From WebUsageMetrics
```

### Data Flow Pattern
1. Main window starts worker threads with QTimer intervals
2. Workers fetch data → emit signals with dataclass objects
3. Main window slots receive signals → update widget state
4. Widgets render data (no direct API calls)

Example:
```python
# In MainWindow
self.usage_worker = UsageWorker(Config.VENICE_ADMIN_KEY)
self.usage_worker.usage_data_updated.connect(self.handle_usage_data)
self.usage_worker.start()

def handle_usage_data(self, usage_list: List[APIKeyUsage]):
    self.leaderboard_widget.update_data(usage_list)
```

## Widget Composition Patterns

### Phase-Based Feature Loading
Code uses try/except imports for phased features:
```python
try:
    from src.widgets.key_management_widget import APIKeyManagementWidget
    PHASE3_AVAILABLE = True
except ImportError:
    APIKeyManagementWidget = None
    PHASE3_AVAILABLE = False

# Later in MainWindow.__init__:
if PHASE3_AVAILABLE:
    self.key_mgmt_widget = APIKeyManagementWidget(...)
```
Allows graceful degradation if modules not implemented yet.

### Custom Delegates for TableView
`UsageBarDelegate` (in `src/widgets/usage_leaderboard.py`) renders logarithmic usage bars:
```python
class UsageBarDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        usage_value = index.data(Qt.UserRole)
        log_value = math.log10(usage_value + 1)
        # Draw colored bar based on percentile
```
Use `QStyledItemDelegate` subclass for custom cell rendering in `QTableView`.

### Theme System
`Theme` class (in `src/config/theme.py`) provides dark/light mode palettes:
```python
Theme.apply_theme(app, Config.THEME_MODE)  # "dark" or "light"
```
Sets `QPalette` colors globally. Widgets inherit automatically.

## Developer Workflows

### Running the Application
```bash
# Setup
pip install -r requirements.txt
cp .env.example .env  # Then edit with real API keys

# Run
python run.py
```

### Adding New Widgets
1. Create file in `src/widgets/` inheriting `QWidget`
2. Add to `src/widgets/__init__.py` exports
3. Import in `src/main.py` with try/except if phased
4. Instantiate in `MainWindow.__init__()` and add to layout

### Adding New API Endpoints
1. Add method to `VeniceAPIClient` base class OR
2. Create new worker inheriting `QThread` with signals
3. Emit dataclass objects, not raw JSON
4. Connect signals in `MainWindow` to update UI

### Testing API Calls
Use `scripts/` for quick endpoint verification:
```bash
python scripts/get_usage.py        # Tests /billing/usage
python scripts/get_webapp_usage.py # Tests web usage endpoint
```
These are standalone scripts outside main app flow.

## Project-Specific Conventions

### Import Style
Always use absolute imports with `src.` prefix:
```python
from src.config.config import Config              # ✓ Correct
from src.core.venice_api_client import VeniceAPIClient
from config.config import Config                  # ✗ Wrong
```

### Error Handling
```python
# Log errors to file, display to user
logging.basicConfig(filename='error_log.txt', level=logging.ERROR)
try:
    response = client.get(endpoint)
except Exception as e:
    logging.error(f"API error: {e}")
    self.error_occurred.emit(f"Error: {str(e)}")  # From worker
```

### Suppressing Warnings
```python
# At top of main.py
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)
```
Used project-wide to suppress SSL warnings for internal API calls.

## Critical Gotchas

1. **Admin key requirement** - Regular API keys fail on `/billing/usage` endpoint with 401
2. **Thread safety** - NEVER call `requests.get()` from main thread, always use `QThread` workers
3. **Import path** - Run via `run.py` not `python src/main.py` or imports break
4. **Signal connections** - Must connect worker signals BEFORE calling `worker.start()`
5. **Dataclass usage** - Always emit typed dataclasses from workers, not raw dicts

## External Dependencies
- **PySide6** - Qt6 Python bindings for GUI
- **requests** - HTTP library for Venice API calls
- **python-dotenv** - Load `.env` files for configuration
- **matplotlib** - Charts in analytics widgets (Phase 2+)

## Directory Reference
- `src/core/` - Business logic, API clients, data models
- `src/widgets/` - UI components (inherit QWidget)
- `src/config/` - Config loader, theme system
- `src/services/` - External service integrations (exchange rates, key management)
- `src/analytics/` - Usage reports, trend analysis
- `src/utils/` - Currency formatting, date utilities
- `data/` - Persistent JSON files (usage_history.json)
- `scripts/` - Standalone test/debug scripts
