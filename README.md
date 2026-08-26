# VVV Token Watch

VVV Token Watch monitors Venice AI API usage, account balance, and VVV and DIEM prices.

The application uses a **FastAPI** backend and a **Next.js** frontend. A single Docker image contains both applications for self-hosted deployment with Unraid or Docker Compose.

---

## Features

- **Account balance** — Shows remaining DIEM and USD credit, the epoch reset time, and consumption status.
- **Epoch usage** — Shows DIEM and USD use since the current epoch started. The calculation nets refunds and cancellations.
- **API key leaderboard** — Shows trailing seven-day use for each key.
- **Price tracking** — Gets current VVV and DIEM prices from CoinGecko and calculates portfolio value.
- **Model catalog** — Shows Venice AI models, capabilities, prices, and deprecation status.
- **Usage analytics** — Shows spending by model and API key.
- **Real-time refresh** — Uses configurable polling intervals.

---

## Web App

The FastAPI backend and Next.js frontend run from one Docker image. You can deploy the image with Unraid or Docker Compose.

### Architecture

```
browser → Next.js (port 3000) → /api/* rewrites → FastAPI (port 8000) → Venice API / CoinGecko
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

`DB_PASSWORD` is required by the production Compose PostgreSQL service. It is
used to build the default `DATABASE_URL`; set both values if you use a custom
database connection. `APP_PASSWORD` may be empty only when
`ALLOW_INSECURE_NO_AUTH=true`. The application, not Compose, enforces that
authentication rule.

#### PostgreSQL permissions

The backend creates its tables at startup. The PostgreSQL role in
`DATABASE_URL` must have permission to use the `public` schema and create
objects in it. PostgreSQL normally grants this permission to the database
owner. An external PostgreSQL installation can use a different owner. Run
this command once as a PostgreSQL administrator. Replace the role and
database names with the values in `DATABASE_URL`:

```sql
GRANT USAGE, CREATE ON SCHEMA public TO vvvwatch;
```

For a PostgreSQL Docker container, run this command:

```bash
docker exec -it <postgres-container> psql -U <admin-user> -d <database> \
	-c "GRANT USAGE, CREATE ON SCHEMA public TO vvvwatch;"
```

#### Unraid
Import `unraid/vvv-token-watch.xml` through the Community Applications template manager. Set the variables in the template. You do not need an `.env` file.

### Local Development (hot-reload)

The script runs the Next.js development server and uvicorn with `--reload` on your machine. Only PostgreSQL runs in Docker.

**Prerequisites:** Docker, a Python virtual environment with `backend/requirements.txt` installed, and Node.js.

```bash
source venv/bin/activate
./dev.sh
```

The first run asks for your API keys and creates a local `.env` file. Later runs use this file.

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
| `APP_PASSWORD` | Conditional | Shared password for the web UI and API. Generate it with `openssl rand -hex 24`. Required unless `ALLOW_INSECURE_NO_AUTH=true`. |
| `ALLOW_INSECURE_NO_AUTH` | Optional | Set to `true` to run without authentication. The default is `false`. |
| `DB_PASSWORD` | Docker only | PostgreSQL password required by `docker/docker-compose.yml`. Local development via `./dev.sh` uses its own development database settings. |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `COINGECKO_API_KEY` | Optional | CoinGecko API key. The free tier is used when this value is empty. |
| `COINGECKO_HOLDING_AMOUNT` | Optional | VVV holdings. The default is `2750`. |
| `DIEM_HOLDING_AMOUNT` | Optional | DIEM holdings. The default is `0`. |
| `COINGECKO_TOKEN_ID` | Optional | CoinGecko ID for VVV. The default is `venice-token`. |
| `DIEM_TOKEN_ID` | Optional | CoinGecko ID for DIEM. The default is `diem`. |
| `COINGECKO_CURRENCIES` | Optional | Currencies to fetch. The default is `usd,aud`. |
| `LOG_LEVEL` | Optional | `INFO` or `DEBUG`. The default is `INFO`. |
| `DEBUG` | Optional | Enables `/docs`, `/redoc`, and `/openapi.json`. The default is `false`. |
| `EPOCH_LENGTH_HOURS` | Optional | Billing epoch length in hours. The application uses this value to calculate `epoch_start` from `nextEpochBegins`. The default is `24`. |
| `SNAPSHOT_INTERVAL_SECONDS` | Optional | Interval in seconds for request-path snapshot writes. Request-path pollers record snapshots. The application does not include a background poller. The default is `300`. |
| `SNAPSHOT_RETENTION_DAYS` | Optional | Retention period for `usage_snapshots` and `price_snapshots` rows. The application removes older rows during each snapshot write and at startup. The default is `90`. |
| `SESSION_SECURE_COOKIE` (frontend) | Optional | When `true`, sets the session cookie with `Secure`. The default is `NODE_ENV === "production"`. Set this value for plaintext HTTP deployments. |

> **Admin key required:** Regular inference keys return 401 for `/billing/usage`. Create an Admin key at https://venice.ai/settings/api.
> **Use a separate inference key:** Set `VENICE_API_KEY` to a separate inference-only key. Do not reuse `VENICE_ADMIN_KEY`. This keeps admin credentials out of public endpoints.

---

## Configuration (.env)

See [.env.example](.env.example) for all available options and descriptions.

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
- `GET /api/v1/billing/usage` — itemized billing transactions.
- `GET /api/v1/billing/usage-analytics` — usage grouped by date, model, and key.
- `GET /api/v1/billing/balance` — account balance and consumption currency.
- `GET /api/v1/api_keys` — API keys with trailing seven-day usage.
- `GET /api/v1/models` — model catalog with deprecation information.

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
