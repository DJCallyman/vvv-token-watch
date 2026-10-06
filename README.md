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

> **Admin key required:** Billing history and balance endpoints need an Admin key. Create one at https://venice.ai/settings/api.
> **Use a separate inference key:** Set `VENICE_API_KEY` to a separate inference-only key. Do not reuse `VENICE_ADMIN_KEY`. This keeps admin credentials out of public endpoints.

---

## Configuration (.env)

See [.env.example](.env.example) for all options and descriptions.

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
