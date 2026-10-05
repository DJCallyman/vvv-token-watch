# VVV Token Watch — Copilot Instructions

## Project Overview

This is a web-only application:

- `backend/`: FastAPI, async SQLAlchemy, PostgreSQL
- `web/`: Next.js App Router, React Query, Tailwind CSS, shadcn/ui
- `docker/`: self-hosted Docker packaging

Run the app with `./dev.sh` for local development or Docker Compose for
deployment. There is no PySide6 desktop app.

## Venice API Rules

- Use `backend/core/venice_api_client.py` for Venice API requests.
- Use `VENICE_ADMIN_KEY` for billing and API-key administration endpoints.
- Prefer `VENICE_API_KEY` for public catalog and inference requests; use the
  admin key only as a fallback where configured.
- Use `/billing/usage-history` with cursor pagination. `/billing/usage` is
  sunset and must not be called.
- Ledger charges are negative and refunds are positive. Sum amounts and negate
  the result; never use `abs()` to calculate net spend.
- Keep USD, DIEM, bundled credits, and earned credits separate.
- Discover models through `/models` and traits through `/models/traits`. Model
  IDs change; add availability checks for configured model IDs.

## Architecture

- API routes: `backend/api/routes/`
- Venice clients, billing aggregation, caches, model metadata: `backend/core/`
- Pydantic schemas and SQLAlchemy models: `backend/models/`
- React Query hooks and typed API calls: `web/lib/`
- Feature components: `web/components/`
- Database schema changes must support existing PostgreSQL installations;
  `create_all` does not alter existing tables.

Use the shared async Venice client and avoid synchronous network calls in
FastAPI handlers.

## Configuration and Prices

- Backend configuration uses Pydantic Settings in `backend/config.py`.
- Prices and on-chain supply/staking metrics come from VeniceStats.
- USD-to-AUD conversion uses Frankfurter/ECB rates.
- Some `COINGECKO_*` names remain for stored settings or old `.env`
  compatibility; live price requests do not use CoinGecko.
- Do not commit `.env`, API keys, or runtime data.

## Development and Tests

```bash
source .venv/bin/activate
pytest backend/tests
cd web && npm run lint && npm test
```

Run focused tests first. Backend route tests may require the configured
PostgreSQL service. Frontend tests use Jest and Testing Library. Follow local
patterns, keep changes scoped, and add tests for behavior changes. Do not
commit changes unless requested.