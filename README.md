# VVV Token Watch

Web-based monitoring tool for Venice AI API usage, account balance, and cryptocurrency prices (VVV & DIEM tokens).

Built with a **FastAPI** backend and **Next.js** frontend, packaged as a single Docker image for self-hosted deployment (Unraid, docker-compose, etc.).

---

## Features

- **Account balance** — Remaining DIEM/USD credit, epoch reset time, and consumption status
- **Epoch usage** — DIEM/USD consumed since the current epoch started (net of refunds/cancellations)
- **API key leaderboard** — 7-day trailing usage per key
- **Price tracking** — VVV and DIEM live prices via CoinGecko, with portfolio value
- **Model catalog** — Browse Venice AI models with capabilities, pricing, and deprecation status
- **Usage analytics** — Per-model and per-key spend breakdowns
- **Real-time refresh** — Configurable polling intervals

---

## Web App

FastAPI backend + Next.js frontend, packaged as a single Docker image. Designed for self-hosted deployment (Unraid, docker-compose, etc.).

### Architecture

```
browser → Next.js (port 3000) → /api/* rewrites → FastAPI (port 8000) → Venice API / CoinGecko
```

### Production (Docker)

```bash
cd docker
cp .env.example .env   # fill in VENICE_ADMIN_KEY etc.
docker compose up -d
```

Open `http://<host>:3000`.

#### Unraid
Import `unraid/vvv-token-watch.xml` via the Community Applications template manager. Fill in the variables in the template — no `.env` file needed.

### Local Development (hot-reload)

Runs Next.js dev server and uvicorn with `--reload` directly on your machine. Only PostgreSQL runs in Docker.

**Prerequisites:** Docker, Python venv with `backend/requirements.txt` installed, Node.js.

```bash
source venv/bin/activate
./dev.sh
```

First run will prompt for your API keys and create a local `.env`. Subsequent runs use the saved file.

| Service   | URL                          |
|-----------|------------------------------|
| Frontend  | http://localhost:3000        |
| Backend   | http://localhost:8000        |
| API docs  | http://localhost:8000/docs   |

Stop with **Ctrl+C** — all processes and the Postgres container are cleaned up automatically.

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `VENICE_ADMIN_KEY` | ✅ | Venice Admin API key (not Inference Only) |
| `APP_PASSWORD` | ✅ | Shared password protecting the web UI and API. Generate with `openssl rand -hex 24`. The app refuses to start without it unless `ALLOW_INSECURE_NO_AUTH=true`. |
| `ALLOW_INSECURE_NO_AUTH` | — | Explicit opt-in to run without authentication (default: `false`). Not recommended. |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `COINGECKO_API_KEY` | — | CoinGecko API key (free tier if omitted) |
| `COINGECKO_HOLDING_AMOUNT` | — | Your VVV holdings (default: 2750) |
| `DIEM_HOLDING_AMOUNT` | — | Your DIEM holdings (default: 0) |
| `COINGECKO_TOKEN_ID` | — | CoinGecko ID for VVV (default: `venice-token`) |
| `DIEM_TOKEN_ID` | — | CoinGecko ID for DIEM (default: `diem`) |
| `COINGECKO_CURRENCIES` | — | Currencies to fetch (default: `usd,aud`) |
| `LOG_LEVEL` | — | `INFO` or `DEBUG` (default: `INFO`) |
| `DEBUG` | — | Enables `/docs`, `/redoc`, `/openapi.json` (default: `false`) |

> **Admin key required:** Regular inference keys return 401 on `/billing/usage`. Create an Admin key at https://venice.ai/settings/api.
> **Use a separate inference key:** Set `VENICE_API_KEY` to a distinct inference-only key rather than reusing `VENICE_ADMIN_KEY`, so public endpoints never expose admin-level credentials.

---

## Configuration (.env)

See [.env.example](.env.example) for all available options with descriptions.

---

## Testing

```bash
pip install -r requirements-dev.txt
python run_tests.py            # all tests
python run_tests.py -c         # with coverage report
python -m pytest tests/test_config.py -v  # single file
```

---

## API Reference

### Venice AI
- `GET /api/v1/api_keys/rate_limits` — current epoch balance and reset time
- `GET /api/v1/billing/usage` — itemised billing transactions
- `GET /api/v1/billing/usage-analytics` — aggregated usage by date, model, and key
- `GET /api/v1/billing/balance` — account balance and consumption currency
- `GET /api/v1/api_keys` — API keys with 7-day trailing usage
- `GET /api/v1/models` — model catalog with deprecation info

### Web App Endpoints
- `GET /api/health`
- `GET /api/balance`
- `GET /api/usage/daily` — epoch usage (net of refunds)
- `GET /api/usage/keys` — per-key usage
- `GET /api/prices`
- `GET /api/models`
- `GET /api/analytics/models`
- `GET /api/analytics/daily`

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

*Not affiliated with Venice AI. Independent monitoring tool.*
