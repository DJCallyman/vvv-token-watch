# VVV Token Watch

VVV Token Watch tracks Venice AI API use, account balance, and VVV and DIEM prices.

The app uses a **FastAPI** backend and a **Next.js** frontend. One Docker image contains both apps for self-hosting with Unraid or Docker Compose.

---

## Features

- **Account balance** — Shows remaining DIEM and USD credit, the epoch reset time, and consumption status.
- **Epoch usage** — Shows DIEM and USD use since the current epoch started. It subtracts refunds and cancellations.
- **API key leaderboard** — Shows use for each key over the last seven days.
- **Price tracking** — Gets current VVV and DIEM prices from VeniceStats. It converts USD to AUD with ECB rates and calculates portfolio value.
- **Model catalog** — Shows Venice AI models, capabilities, prices, and deprecation status.
- **Usage analytics** — Shows spending by model and API key.
- **Real-time refresh** — Refreshes data at configured intervals.

---

## Web App

One Docker image runs the FastAPI backend and Next.js frontend. Deploy the image with Unraid or Docker Compose.

### Architecture

```
browser → Next.js (port 3000) → /api/* proxy → FastAPI (port 8000) → Venice API / VeniceStats / Frankfurter
```

### Production (Docker)

```bash
cp .env.example .env
# Set VENICE_ADMIN_KEY and DB_PASSWORD in .env.
# For an isolated local deployment, you may also set:
# ALLOW_INSECURE_NO_AUTH=true
docker compose -f docker/docker-compose.yml up -d --build
```

Open `http://<host>:3000`.

The production Compose PostgreSQL service requires `DB_PASSWORD`. Compose uses
this value to build the default `DATABASE_URL`. For a custom database
connection, set `DB_PASSWORD` and `DATABASE_URL`. `APP_PASSWORD` can be empty
only when `ALLOW_INSECURE_NO_AUTH=true`. The application enforces this rule.

#### PostgreSQL permissions

The backend creates tables at startup. The PostgreSQL role in `DATABASE_URL`
needs permission to use the `public` schema and create objects in it.
PostgreSQL normally grants this permission to the database owner. An external
PostgreSQL installation can use a different owner. As a PostgreSQL
administrator, run this command once. Replace the role and database names with
the values in `DATABASE_URL`:

```sql
GRANT USAGE, CREATE ON SCHEMA public TO vvvwatch;
```

For a PostgreSQL Docker container, run this command:

```bash
docker exec -it <postgres-container> psql -U <admin-user> -d <database> \
	-c "GRANT USAGE, CREATE ON SCHEMA public TO vvvwatch;"
```

#### Unraid
Import `unraid/vvv-token-watch.xml` through the Community Applications template
manager. Set the variables in the template. An `.env` file is not required.

### Local Development (hot-reload)

The script runs the Next.js development server and uvicorn with `--reload` on
your machine. Docker runs only PostgreSQL.

**Prerequisites:** Docker, Node.js, and a Python virtual environment with
`backend/requirements.txt` installed.

```bash
source venv/bin/activate
./dev.sh
```

The first run asks for your API keys and creates a local `.env` file. Later runs
use this file.

| Service   | URL                          |
|-----------|------------------------------|
| Frontend  | http://localhost:3000        |
| Backend   | http://localhost:8000        |
| API docs  | http://localhost:8000/docs   |

Press **Ctrl+C** to stop all processes and remove the PostgreSQL container.

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `VENICE_ADMIN_KEY` | Required | Venice Admin API key, not an Inference Only key. |
| `ASSISTANT_MODEL` | Optional | Venice model ID for the read-only assistant. Default: `venice-uncensored-1-2`. |
| `APP_PASSWORD` | Conditional | Shared password for the web UI and API. Generate it with `openssl rand -hex 24`. Required unless `ALLOW_INSECURE_NO_AUTH=true`. |
| `ALLOW_INSECURE_NO_AUTH` | Optional | Set to `true` to run without authentication. The default is `false`. |
| `DB_PASSWORD` | Docker only | Password for PostgreSQL in `docker/docker-compose.yml`. Local `./dev.sh` uses separate database settings. |
| `DATABASE_URL` | ✅ | PostgreSQL connection string. |
| `COINGECKO_API_KEY` | Legacy | Accepted in old `.env` files. Live price requests do not use it. |
| `COINGECKO_HOLDING_AMOUNT` | Optional | Manual VVV holdings. This is a legacy variable name. Default: `2750`. |
| `DIEM_HOLDING_AMOUNT` | Optional | DIEM holdings. Default: `0`. |
| `COINGECKO_TOKEN_ID` | Legacy | Accepted in old `.env` files. Live price requests do not use it. |
| `DIEM_TOKEN_ID` | Legacy | Accepted in old `.env` files. Live price requests do not use it. |
| `COINGECKO_CURRENCIES` | Legacy | Accepted in old `.env` files. Live price requests do not use it. |
| `LOG_LEVEL` | Optional | `INFO` or `DEBUG`. Default: `INFO`. |
| `DEBUG` | Optional | Enables `/docs`, `/redoc`, and `/openapi.json`. Default: `false`. |
| `EPOCH_LENGTH_HOURS` | Optional | Hours in a billing epoch. The app uses this value to calculate `epoch_start` from `nextEpochBegins`. Default: `24`. |
| `SNAPSHOT_INTERVAL_SECONDS` | Optional | Seconds between request-path snapshot writes. Request-path pollers record snapshots. The app has no background poller. Default: `300`. |
| `SNAPSHOT_RETENTION_DAYS` | Optional | Days to keep `usage_snapshots` and `price_snapshots` rows. The app removes old rows at each snapshot write and at startup. Default: `90`. |
| `SESSION_SECURE_COOKIE` (frontend) | Optional | When `true`, sets the session cookie with `Secure`. Default: `NODE_ENV === "production"`. Set this value for plaintext HTTP deployments. |
| `ALERT_COOLDOWN_SECONDS` | Optional | Cooldown after an alert acknowledgment before the same alert can fire again. Default: `3600`. |
| `SMTP_HOST` | Optional | SMTP server for email alert delivery. Email stays unavailable until this is set. |
| `SMTP_PORT` | Optional | SMTP port. Default: `587`. |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | Optional | SMTP credentials, when the server requires authentication. |
| `SMTP_FROM` | Optional | Envelope sender for alert email. |
| `SMTP_USE_TLS` | Optional | StartTLS for SMTP. Default: `true`. |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` | Optional | Web Push key pair. Browser push stays unavailable until both are set. |
| `VAPID_SUBJECT` | Optional | VAPID contact (`mailto:` or URL). Default: `mailto:admin@example.com`. |
| `EMBEDDING_MODEL` | Optional | Embeddings model for semantic news search and document RAG. |
| `TTS_MODEL` / `TTS_VOICE` | Optional | Text-to-speech model and voice for briefings and alert audio. |
| `VIDEO_MODEL` | Optional | Video model for asynchronous market recap generation. |

> **Admin key required:** Billing history and balance endpoints need an Admin key. Create one at https://venice.ai/settings/api.
> **Use a separate inference key:** Set `VENICE_API_KEY` to a separate inference-only key. Do not reuse `VENICE_ADMIN_KEY`. This keeps admin credentials out of public endpoints.

---

## Configuration (.env)

See [.env.example](.env.example) for all options and descriptions.

---

## Monitoring and integrations

### Alert signals

Alerts support threshold checks plus two deterministic signal types:

- **Rate of change** — percent change between the latest value and the value at least
  one configured window earlier (default 3600 s, 60–2,592,000 s allowed).
- **Anomaly** — z-score of the latest value against the mean and population standard
  deviation of earlier samples. A minimum baseline sample count applies (default 10).
  A zero-variance baseline is skipped, never fired.

Send optional history with `POST /api/alerts/evaluate`:
`{"metrics": {...}, "history": {"vvv_price_usd": [{"timestamp": "...", "value": 1.2}]}}`.
Insufficient history never fires. The response reports `skipped` reasons. An
unacknowledged event blocks duplicates, and `ALERT_COOLDOWN_SECONDS` (default 3600)
applies after acknowledgment.

### External notifications

The first provider set is Discord, Slack, Telegram, generic HTTPS webhooks, email,
and browser push. Each channel is a durable row; each alert event creates at most one
delivery per channel (unique dedupe key), so duplicate events never send twice.

- Discord and Slack destinations are restricted to their own webhook hosts.
- Generic webhooks and browser push endpoints are resolved and rejected when they
  point at private, loopback, link-local, or reserved addresses (SSRF defense).
- Delivery retries are bounded to three attempts with exponential backoff; HTTP 429
  honors `Retry-After`. Failures show in the Alerts page with a Retry action.
- Webhook URLs, bot tokens, and push keys are stored server-side and masked in API
  responses and logs.
- Email is unavailable until `SMTP_HOST` is set. Browser push is unavailable until
  VAPID keys are set. Missing providers report `available: false`; they do not fail
  silently.

**Recovery:** if a delivery fails, fix the destination in Alerts → Notification
Channels, then use **Send test**. Use the delivery **Retry** action to re-arm a failed
row. Deleting a channel stops future deliveries; existing delivery rows remain for
audit.

### On-chain views and watchlists

Supply, staking KPI, and APR data come from VeniceStats. Wallet balances, transfers,
and staking events come from the Venice crypto RPC with explicit, bounded block
ranges (reported in each response). Staking events derive from VVV transfers that
involve the staking contract: transfer in = stake, transfer out = unstake. Partial
upstream history is never presented as complete.

Holder views are address-specific only. Slice 2.0 verified no all-holder endpoint,
freshness interval, or retention period, so the app does not scan unbounded chain
history. Watchlist entries persist in PostgreSQL and always carry chain and token.

### Chains and tokens

An explicit registry (`backend/core/chains.py`) defines the approved chains and
tokens. Base mainnet is the only approved network today. Cache keys and API responses
identify chain and token; unapproved pairs fail with an explicit error. Adding a
network requires registering its verified contract addresses and data sources first.

### Rate-limit and RPC cost observability

The Usage page reports upstream telemetry separately from this app's own request
limiter:

- Rate-limit and `X-Venice-*` response headers are captured in process with a
  last-seen timestamp.
- The experimental `GET /api_keys/rate_limits/log` event list is proxied when the
  configured key is an ADMIN key. Missing, forbidden, or failed telemetry is shown
  as **unavailable**, never as zero.
- Crypto RPC costs come from authoritative `X-Venice-RPC-Credits` and
  `X-Venice-RPC-Cost-USD` headers per call. Costs are not estimated from call counts.
- A coverage probe samples `/billing/usage-history`. Account-level reconciliation
  stays **unverified** unless RPC charges actually appear in the ledger sample.

**Recovery:** these views are read-only. If upstream telemetry stops, confirm the
key's scopes and Venice status; values repopulate automatically after the next
successful call.

### Wallet sessions

Wallet authentication is separate from the shared-password app session and supports
Base mainnet only. `POST /api/wallet/challenge` issues a one-time, expiring,
chain-bound message; the wallet signs it with `personal_sign`, and
`POST /api/wallet/verify` returns an opaque session token. Replayed, expired, and
wrong-network proofs are rejected. Wallet endpoints are read-only and return only the
authenticated wallet's data. Log out from the On-Chain page to delete the session.

### AI features

- **X/Twitter sentiment** through Venice search models, recorded as a structured signal.
- **Signal history** with direction, confidence, rationale, sources, and deterministic
  outcome tracking (evaluate a signal against the current VVV price).
- **Infographics** generated from the latest structured signal.
- **Voice alerts and daily briefings** through Venice TTS (playable in the UI).
- **Semantic news search and RAG** through Venice embeddings, with cited sources.
- **Document parsing** for PDF, Markdown, text, and JSON with grounded Q&A.
- **Video market recaps** queued asynchronously; completed files are saved under
  `DATA_DIR/media`.
- **Benchmark progress** streams over Server-Sent Events with status-poll fallback.

Model IDs for these features come from `EMBEDDING_MODEL`, `TTS_MODEL`, `TTS_VOICE`,
and `VIDEO_MODEL`. All model output is informational and is not financial advice.

### PWA, offline, and exports

The app ships a web manifest and an offline-shell service worker. Navigations fall
back to `/offline`; API responses are never cached. A banner reports offline status
and offers a retry. Dashboard, usage, prices, alerts, and on-chain views export JSON
snapshots and CSV row sets. The onboarding checklist, keyboard-shortcut help, and
glossary are available from the dashboard and the command palette.

---

## Testing

Run the backend tests with pytest from the repository root:
```bash
cd backend
pip install -r requirements.txt
PYTHONPATH=. pytest tests/ -v
PYTHONPATH=. pytest tests/<file>.py -v   # single file
```

Run the frontend tests with Jest:
```bash
cd web
npm install        # one-time
npm run lint
npm test
npm run test:coverage
```

---

## API Reference

### Venice AI
- `GET /api/v1/api_keys/rate_limits` — current epoch balance and reset time.
- `GET /api/v1/billing/usage-history` — itemized billing records with cursor pagination.
- `GET /api/v1/billing/usage-analytics` — usage grouped by date, model, and key.
- `GET /api/v1/billing/balance` — account balance and consumption currency.
- `GET /api/v1/api_keys` — API keys with use for the last seven days.
- `GET /api/v1/models` — model catalog with deprecation details.

### Web App Endpoints
- `GET /api/health`
- `GET /api/balance`
- `GET /api/usage/daily` — epoch usage after refunds.
- `GET /api/usage/keys` — usage for each key.
- `GET /api/prices`
- `GET /api/models`
- `GET /api/analytics/models`
- `GET /api/analytics/daily`

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

*This project is not affiliated with Venice AI. It is an independent monitoring tool.*
