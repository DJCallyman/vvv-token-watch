# VVV Token Watch Enhancement Roadmap

This document lists planned UI, UX, functionality, and usability changes for VVV Token Watch. It also lists frontend dependency and GitHub Actions maintenance work.

## Status Legend

- [x] Completed
- [ ] Planned

## Completed Features: High Impact

### 1.1 Mobile Responsive Sidebar

- [x] Add a mobile navigation drawer with backdrop and hamburger control.
- [x] Share drawer state between `Sidebar` and `Header`.
- [x] Close the drawer after navigation or backdrop interaction.
- [x] Preserve the desktop sidebar layout.

### 2.1 Real-Time Alert Delivery

- [x] Add authenticated `GET /api/alerts/stream` Server-Sent Events endpoint.
- [x] Stream new alert events with a database cursor.
- [x] Use short-lived database sessions. Do not hold a connection for the stream lifetime.
- [x] Add reconnect handling to the frontend `EventSource` client.
- [x] Invalidate alert queries when an event arrives.

### 3.1 AI-Powered Market Analysis

- [x] Add authenticated `POST /api/insights/analyze` endpoint.
- [x] Gather current VVV/DIEM web context with Venice web search.
- [x] Generate structured market analysis with Venice chat completions.
- [x] Display sentiment, confidence, key events, risks, and sources in `/insights`.
- [x] Mark the output as informational and not financial advice.

### 3.2 Token News Feed

- [x] Add authenticated `GET /api/news` endpoint with server-side caching.
- [x] Add authenticated article retrieval with Venice scrape support.
- [x] Add responsive news cards and article reader at `/news`.
- [x] Add manual refresh and periodic React Query refresh.

### 3.5 Natural Language Query Assistant

- [x] Add authenticated `POST /api/assistant/query` endpoint.
- [x] Add a read-only assistant UI at `/assistant`.
- [x] Add suggested questions for balance, price, and usage queries.
- [x] Define a constrained, read-only tool surface for future tool execution.
- [x] Block arbitrary actions and mutations through the assistant.

### 3.6 On-Chain Transfer History

- [x] Add VVV ERC-20 `Transfer` event lookup with Venice Crypto RPC `eth_getLogs`.
- [x] Support configurable ranges of recent blocks.
- [x] Filter transfers involving the requested wallet.
- [x] Display direction, addresses, amount, and transaction links.
- [x] Link transaction hashes to BaseScan.

## Completed Engineering Maintenance

### Frontend Dependency and CI Maintenance

- [x] Upgrade Next.js to patched `15.5.23`.
- [x] Upgrade `eslint-config-next` to `15.5.16`.
- [x] Upgrade ESLint from version 8 to `9.39.2`.
- [x] Upgrade Jest, jsdom environment, ts-jest, and Testing Library user-event to compatible current versions.
- [x] Upgrade PostCSS to `8.5.26`.
- [x] Add a lodash override at `4.18.1` for the Recharts dependency tree.
- [x] Regenerate `web/package-lock.json`.
- [x] Update the Next proxy because Next 15 removed `NextRequest.ip` from its type surface.
- [x] Set `outputFileTracingRoot` to remove the multiple-lockfile workspace warning.
- [x] Add an explicit frontend lint step to GitHub Actions.
- [x] Make frontend tests fail CI instead of masking failures with `|| echo "No tests yet"`.
- [x] Verify clean `npm ci`, lint, tests, and production build.

Current verification results:

- `npm run lint`: passed with no ESLint warnings or errors.
- Frontend tests: 278 passed.
- `npm run build`: passed.
- Clean `npm ci`: passed.

Known upstream dependency notices that remain during `npm ci`:

- `inflight@1.0.6` and `glob@7.2.3` through Jest/Istanbul's `test-exclude` chain.
- `whatwg-encoding@3.1.1` through `jsdom@26`.
- `glob@10.5.0` through Jest's reporter/configuration packages.

These dependencies come from the current Jest/jsdom stack. Safe removal requires a replacement or a major change to the test toolchain.

`npm audit --omit=dev` still reports issues in the Next-bundled `postcss` and `sharp` packages. The audit tool identifies Next 16 as the automatic fix. Next 16 is a major migration. Handle it in a separate change.

## Roadmap Completion

All phases are complete. Phase 2 and later work landed as independent, tested slices (see the completion review at the end of this document).

### Phase 1: Interaction Foundation — Complete

- [x] Add success and error toast feedback to core user-initiated asynchronous workflows.
- [x] Add a reusable data table with sorting, pagination, and column visibility.
- [x] Add the global command palette for navigation and common actions.
- [x] Add accessible labels and keyboard interactions for core workflows.
- [x] Add content-shaped loading states and contextual empty states to core data views.
- [x] Preserve and identify last-loaded query data when refreshes fail; provide retry actions.

### Phase 2: Monitoring Depth — Complete

Phase 2 improves monitoring while keeping each backend, security, and UI change independently reviewable. Complete slices in order where dependencies require it; data-source investigations are gates, not permission to invent unsupported data.

Database changes must upgrade existing PostgreSQL installations. `create_all` creates missing tables but does not update existing ones; establish and test a supported migration path before the first slice that changes stored schema.

#### Slice 2.0: Foundation and Source Verification — Complete

- [x] Add visible keyboard focus to header controls.
- [x] Finish the Phase 1 feedback follow-up: add success and error feedback for infographic generation, benchmark cost estimates, CharactersView refresh, and benchmark cancel failures.
- [x] Finish the Phase 1 loading-state follow-up: add content-shaped loading states in AlertsView, the UsageView summary and trends, BenchmarkView results, and ModelAnalytics.
- [x] Decide whether preferences are instance-wide or account-specific. Use instance-wide preferences initially unless multi-user authentication is added.
- [x] Establish and test the schema migration path against an existing PostgreSQL database before adding tables or columns.
- [x] Verify authoritative sources and retention limits for price volume, staking events, holder data, Venice Crypto RPC charges, and rate-limit headers/events.
- [x] Select the first external notification channel and define the initial x402 wallet/network scope; keep the remaining requested channels and supported networks in scope for follow-on slices.
- [x] Document how to run the PostgreSQL migration integration test locally, including its dedicated disposable database requirement.

**Done when:** the three UI follow-ups have focused tests; each source-dependent feature has a documented source, freshness/retention limits, and failure behavior; and schema changes can be applied without losing existing data.

**Review note (2026-10-06):** the keyboard-focus, feedback, and loading-state follow-ups are complete with focused tests. The local migration-test recipe is documented in `backend/migrations/README.md`.

Source investigation (2026-10-06):

- **Price and volume:** VeniceStats exposes `/api/metrics` and `/api/charts`; the existing client uses 30-second and 5-minute local caches, and its chart response is LTTB-sampled to at most 200 points. The current chart response reports a seven-day period, while the metrics payload includes `priceLastUpdated` and `lastUpdated`. A direct `/api/charts?metric=volume` request returned HTTP 400. The `/markets` page advertises real-time trading analytics, but no public volume API contract or upstream retention guarantee was verified. Keep volume unavailable until that contract is documented. Locally captured price snapshots are request-driven and retained for 90 days; VeniceStats failures surface as API errors rather than zero prices.
- **Staking events:** Venice Crypto RPC documents `eth_getLogs` as a supported, standard-tier method and recommends stateless logs instead of HTTP filter methods. It does not document an archive window or maximum block range. Use bounded, explicitly reported block ranges; do not imply that partial upstream history is complete. The existing wallet transfer view caps queries at 100,000 blocks and caches results for 60 seconds.
- **Holder data:** the existing VeniceStats `/api/venetians` lookup is address-specific. No documented all-holder endpoint, freshness interval, or retention period was verified. Do not derive a holder list by scanning unbounded chain history.
- **RPC costs:** `X-Venice-RPC-Credits` and `X-Venice-RPC-Cost-USD` report authoritative per-request charges (batch headers report totals); do not estimate charges from call counts. `/billing/usage-history` is cursor-paginated with up to 1,000 entries per page, but its public contract does not specify retention or confirm that RPC charges appear there. Per-call tracking can use response headers; account-level reconciliation remains gated on verifying ledger coverage.
- **Rate limits:** the rate-limit guide documents standard request/token headers and separate Crypto RPC headers that appear only on 429 responses. `GET /api_keys/rate_limits/log` returns the last 50 exceeded-limit events, is experimental, and requires an ADMIN key; no time-based retention is specified. Treat missing, forbidden, or failed upstream telemetry as unavailable, and keep it distinct from this app's own SlowAPI limits.

Sources: [VeniceStats developer API](https://venicestats.com/developers), [VeniceStats markets](https://venicestats.com/markets), [Venice Crypto RPC](https://docs.venice.ai/api-reference/endpoint/crypto/rpc), [Venice rate limits](https://docs.venice.ai/api-reference/rate-limiting), [billing usage history](https://docs.venice.ai/api-reference/endpoint/billing/usage-history), and [rate-limit logs](https://docs.venice.ai/api-reference/endpoint/api_keys/rate_limit_logs).

Initial scope decisions:

- Preferences are instance-wide while authentication uses one shared application password.
- Discord webhooks are the first external notification adapter. Restrict destinations to Discord's webhook hosts; do not accept arbitrary outbound URLs.
- x402 wallet authentication starts with Base only. Add Solana only in a later, separately tested network expansion.

#### Slice 2.1: Preferences and Dashboard Layout — Complete

- [x] Add preferences for refresh intervals, notification settings, display currency, and timezone.
- [x] Add customizable drag-and-drop dashboard layout with persisted ordering and a reset-to-default action.
- [x] Add dashboard layout tests for mobile/desktop viewport behavior, applying the stored layout on mount, save-failure rollback, and move controls disabled at list bounds.
- [x] Add settings tests for frontend rejection of invalid refresh intervals, the SettingsDialog reset action, `/api/settings` route behavior, and PostgreSQL-backed persistence.

**Done when:** validated settings survive reloads, invalid refresh intervals are rejected, defaults and reset behavior are tested, and dashboard layout works at mobile/desktop sizes with keyboard-accessible controls.

#### Slice 2.2: Alert Signals — Complete

- [x] Add rate-of-change alerts using explicitly defined metrics and time windows.
- [x] Add deterministic anomaly alerts with a documented baseline, minimum sample count, and configurable threshold.

**Done when:** alert types and valid metrics are represented in API validation and UI controls; tests cover trigger/non-trigger, missing history, cooldown, deduplication, and re-arming; existing threshold alerts remain compatible.

#### Slice 2.3: Price Chart Analysis — Complete

- [x] Add price comparisons and selected technical indicators.
- [x] Add volume when Slice 2.0 verifies an authoritative source; otherwise record the source limitation in user-facing UI or docs and keep volume unavailable rather than synthesizing it.
- [x] Annotate charts with matching alert events.

**Done when:** chart calculations have deterministic tests for sparse or missing points, comparisons use consistent currency/time ranges, and annotations link to the corresponding alert event.

#### Slice 2.4: External Alert Delivery — Complete

- [x] Add delivery for browser push, webhooks, email, Discord, Slack, and Telegram, one provider adapter per reviewable change.
- [x] Add durable delivery attempts, bounded retries, idempotency, per-channel preferences, and delivery status.
- [x] Expand the instance-wide notification setting from Slice 2.1 into per-channel preferences with a schema migration; keep current behavior when the new fields are absent.

**Done when:** the first selected provider can deliver a test event end to end; duplicate events do not send duplicate notifications; failures are visible and retryable; credentials are not exposed in logs or API responses; outbound webhook handling prevents server-side request forgery.

#### Slice 2.5: On-Chain Views and Watchlists — Complete

- [x] Add staking event history, holder views, and wallet/token watchlists using the sources verified in Slice 2.0.
- [x] Gate holder views on a verified all-holder data source. Slice 2.0 verified only an address-specific lookup and documented no all-holder endpoint, freshness interval, or retention period. If no source is found, restrict holder views to address-specific lookups and document the limitation.
- [x] Bound query ranges and response sizes; do not build holder balances by scanning unbounded chain history through the RPC endpoint.

**Done when:** source attribution, update cadence, pagination/range limits, and stale/error behavior are visible; watchlists persist across reloads; tests cover empty results and upstream failures.

#### Slice 2.6: Multi-Chain and Multi-Token Support — Complete

- [x] Define the approved network and token list before implementation; a network is not approved until it appears in that list.
- [x] Replace Base-only token/contract assumptions with an explicit chain/token registry containing network identifiers, addresses, decimals, and data sources.
- [x] Expand supported on-chain views to the approved networks and tokens without changing existing VVV/DIEM response behavior unexpectedly.

**Done when:** all cache keys and API responses identify chain and token; unsupported pairs fail explicitly; tests cover two chains with distinct token metadata and preserve current Base behavior.

#### Slice 2.7: Rate-Limit and RPC Cost Observability — Complete

- [x] Extend rate-limit monitoring with approved response-header fields and Venice rate-limit events; distinguish upstream Venice limits from this app's own request limiter.
- [x] Define behavior when the configured key is not ADMIN and the experimental rate-limit log endpoint is unavailable; treat missing, forbidden, or failed telemetry as unavailable rather than zero.
- [x] Re-verify that `/billing/usage-history` contains Venice Crypto RPC charges and supports account-level reconciliation before relying on it; Slice 2.0 left ledger coverage unconfirmed.
- [x] Track Venice Crypto RPC costs using the authoritative billing source verified in Slice 2.0; do not estimate costs from call counts unless published pricing supports that calculation.

**Done when:** the dashboard reports freshness and missing-data states; telemetry never stores API keys or other credentials; RPC costs reconcile to source billing data and keep USD, DIEM, bundled credits, earned credits, and refunds correctly separated.

#### Slice 2.8: x402 Wallet Balance and Transactions — Complete

- [x] Implement the approved wallet-auth flow and read-only balance/transaction history for the selected x402 networks.
- [x] Keep wallet authentication separate from the existing password/session flow and do not expose arbitrary wallet data to unauthenticated callers.

**Done when:** wallet ownership uses a one-time, expiring, chain-bound challenge; replayed, expired, and wrong-network proofs are rejected; endpoints are read-only and return only the authenticated wallet's data.

#### Phase 2 Exit Criteria — Met

- [x] All slices are complete, including outstanding follow-up items, the requested notification providers, and approved chain/token coverage.
- [x] Existing PostgreSQL installations upgrade safely; backend and frontend tests cover new contracts and failure paths.
- [x] New external integrations document required configuration, data retention, operational failure behavior, and recovery steps.

### Phase 3: Analysis Features — Complete

- [x] Add X/Twitter sentiment tracking through Venice-supported search models.
- [x] Add structured AI signal history with confidence and outcome tracking.
- [x] Add Server-Sent Events progress updates to benchmark runs.
- [x] Add AI-generated market infographics beyond benchmark results.
- [x] Add voice alerts and daily briefings through Venice TTS.
- [x] Add semantic news search and retrieval-augmented generation through Venice embeddings.
- [x] Add whitepaper, report, and document parsing workflows.
- [x] Add video market recap generation.

### Phase 4: Usability and Distribution — Complete

- [x] Add PWA installability and offline shell behavior.
- [x] Add CSV, JSON, and shareable snapshot export.
- [x] Add an onboarding checklist and first-run guidance.
- [x] Add keyboard shortcut help and contextual help/glossary/tooltips.
- [x] Improve offline handling with cached last-known data, retry controls, and clear status.

All formerly deferred and out-of-scope roadmap items are now included in Phases 2–3. This scope change includes new wallet-auth, notification, cost-tracking, and rate-limit monitoring work; implementation plans must account for their security and operating requirements.

Roadmap review (2026-10-06): corrected the Slice 2.0 and 2.1 completion status, moved the outstanding UI follow-ups into tracked items, and added source, scope, and migration-test gates for Slices 2.3–2.7.

Completion review (2026-10-06): Phases 2–4 are implemented and tested.

- Slice 2.1 follow-ups: dashboard layout tests (stored layout on mount, save-failure rollback, bounds-disabled controls, responsive grid) and settings tests (frontend interval rejection, reset action, `/api/settings` route behavior, PostgreSQL persistence) are in place.
- Slice 2.2: `rate_of_change` and `anomaly` alert types with documented windows, minimum samples, z-score math, insufficient-history reporting, cooldown, deduplication, and re-arming tests.
- Slice 2.3: deterministic chart analysis (SMA/EMA/RSI, sparse handling, percent change, series alignment) with UI indicators, normalized comparisons, alert-event annotations linked to `/alerts`, and an explicit volume-unavailable limitation.
- Slice 2.4: durable delivery for Discord, Slack, Telegram, generic HTTPS webhooks, email, and browser push; unique dedupe keys, bounded retries with `Retry-After`, masked credentials, SSRF guards, delivery status and retry UI, and migration 0003 channel tables.
- Slice 2.5: bounded staking-event history, address-specific holder lookup with the documented all-holder limitation, and persistent watchlists.
- Slice 2.6: explicit chain/token registry; responses and cache keys carry chain and token; unapproved pairs fail explicitly; tests cover two chains with distinct metadata.
- Slice 2.7: response-header telemetry, ADMIN-only event-log handling with unavailable states, billing-ledger coverage probe, and a dashboard card that reports freshness and missing data without showing zeros.
- Slice 2.8: one-time, expiring, chain-bound wallet challenges; opaque read-only sessions; replay/expiry/wrong-network rejection; wallet-scoped balance and transaction endpoints.
- Phase 3: X sentiment, signal history with outcomes, market infographics, TTS briefings and alert audio, semantic news search and RAG, document parsing, video recaps, and SSE benchmark progress.
- Phase 4: PWA manifest/offline shell, JSON/CSV snapshot exports, onboarding checklist, keyboard help and glossary, and offline banner with retry.
