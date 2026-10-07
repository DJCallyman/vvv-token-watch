# VVV Token Watch — Copilot Instructions

## Project Overview

This is a web-only app:

- `backend/`: FastAPI, async SQLAlchemy, PostgreSQL
- `web/`: Next.js App Router, React Query, Tailwind CSS, shadcn/ui
- `docker/`: self-hosted Docker packaging

Run local development with `./dev.sh`. Use Docker Compose for deployment. This
repo does not include a PySide6 desktop app.

## Venice API Rules

- Use `backend/core/venice_api_client.py` for Venice API requests.
- Use `VENICE_ADMIN_KEY` for billing and API-key administration endpoints.
- Prefer `VENICE_API_KEY` for public catalog and inference requests. Use the
  admin key only as a configured fallback.
- Use `/billing/usage-history` with cursor pagination. Do not call
  `/billing/usage`. Venice retired this endpoint.
- Ledger charges are negative. Refunds are positive. Sum the amounts and
  negate the sum. Never use `abs()` to calculate net spend.
- Keep USD, DIEM, bundled credits, and earned credits separate.
- Discover models through `/models` and traits through `/models/traits`. Model
  IDs change. Add availability checks for configured model IDs.

## Architecture

- API routes: `backend/api/routes/`
- Venice clients, billing aggregation, caches, and model metadata: `backend/core/`
- Pydantic schemas and SQLAlchemy models: `backend/models/`
- React Query hooks and typed API calls: `web/lib/`
- Feature components: `web/components/`
- Design database schema changes to support existing PostgreSQL installations.
  `create_all` does not alter existing tables.

Use the shared async Venice client. Do not make synchronous network calls in
FastAPI handlers.

## Configuration and Prices

- Backend settings use Pydantic Settings in `backend/config.py`.
- VeniceStats supplies prices and on-chain supply/staking metrics.
- Use Frankfurter/ECB rates to convert USD to AUD.
- Some `COINGECKO_*` names remain for stored settings or old `.env`
  compatibility. Live price requests do not use CoinGecko.
- Do not commit `.env`, API keys, or runtime data.

## Development and Tests

```bash
source .venv/bin/activate
pytest backend/tests
cd web && npm run lint && npm test
```

Run focused tests first. Backend route tests may need the configured PostgreSQL
service. Frontend tests use Jest and Testing Library. Match local patterns and
keep changes scoped. Add tests for behavior changes. Do not commit changes
unless asked.