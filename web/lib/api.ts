const API_BASE = ''

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string> | undefined),
  }

  // Auth is handled by the HttpOnly session cookie set at /login, which the
  // browser attaches automatically on same-origin requests. The Next.js
  // route handler proxy (app/api/[...path]/route.ts) validates that cookie
  // and injects the real backend credential server-side — the password
  // itself never reaches client-side JavaScript.
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  if (response.status === 401) {
    if (typeof window !== 'undefined') {
      window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`
    }
    throw new Error('API Error: 401 Unauthorized')
  }

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const errBody = await response.json()
      if (typeof errBody?.detail === 'string') {
        detail = errBody.detail
      } else if (Array.isArray(errBody?.detail)) {
        detail = errBody.detail
          .map((d: { loc?: unknown[]; msg?: string }) => {
            const loc = Array.isArray(d.loc) ? d.loc.join('.') : ''
            return loc ? `${loc}: ${d.msg ?? 'invalid'}` : (d.msg ?? 'invalid')
          })
          .join('; ')
      } else if (errBody?.detail != null) {
        detail = JSON.stringify(errBody.detail)
      }
    } catch {
      // keep status text fallback
    }
    throw new Error(`API Error: ${detail}`)
  }

  return response.json()
}

export interface BalanceData {
  diem: number
  usd: number
  daily_diem_limit: number
  daily_usd_limit: number
  next_epoch_begins: string | null
  // Legacy "remaining-ish" percents (kept for backward compat)
  diem_usage_percent: number
  usd_usage_percent: number
  // BUG-06: canonical consumed percents (preferred for alerts and displays)
  diem_consumed_percent?: number | null
  usd_consumed_percent?: number | null
  consumption_currency?: string
  can_consume?: boolean
  diem_epoch_allocation?: number | null
  bundled_credits?: number
  earned_credits?: number
}

export interface DailyUsage {
  date: string
  diem: number
  usd: number
  bundled_credits?: number
  earned_credits?: number
  // epoch_start removed — use EpochUsage (getEpochUsage) for epoch data
}

export interface EpochUsage {
  diem: number
  usd: number
  bundled_credits: number
  earned_credits: number
  epoch_start: string | null
  next_epoch: string | null
}

export interface APIKeyUsage {
  id: string
  name: string
  diem_usage: number
  usd_usage: number
  created_at: string
  is_active: boolean
  last_used_at?: string | null
  api_key_type?: 'INFERENCE' | 'ADMIN' | string | null
  limit_period?: 'EPOCH' | 'MONTH' | 'LIFETIME' | string | null
  expires_at?: string | null
  last6_chars?: string | null
  consumption_limits_usd?: number | null
  consumption_limits_diem?: number | null
  current_period_usage_usd?: string | null
  current_period_usage_diem?: string | null
  model_privacy?: 'ALL' | 'PRIVATE_TEXT' | 'PRIVATE_ONLY' | string | null
}

export interface UsageKeysResponse {
  keys: APIKeyUsage[]
}

export interface APIKeyAnalyticsResponse {
  key_usage: Array<{
    api_key_id: string | null
    name: string
    total_usd: number
    total_diem: number
    total_units: number
  }>
  period_days: number
  source: string
}

// ---------------------------------------------------------------------------
// API key CRUD (create / edit / revoke)
// ---------------------------------------------------------------------------

export type ApiKeyType = 'INFERENCE' | 'ADMIN'
export type LimitPeriod = 'EPOCH' | 'MONTH' | 'LIFETIME'

export interface ConsumptionLimitInput {
  usd?: number | null
  diem?: number | null
}

export interface ApiKeyCreatePayload {
  apiKeyType: ApiKeyType
  description: string
  consumptionLimit?: ConsumptionLimitInput | null
  limitPeriod?: LimitPeriod | null
  expiresAt?: string | null
}

export interface ApiKeyUpdatePayload {
  id: string
  description?: string | null
  consumptionLimit?: ConsumptionLimitInput | null
  limitPeriod?: LimitPeriod | null
  expiresAt?: string | null
}

export interface ApiKeyCreatedSecret {
  apiKey: string
  id: string
  apiKeyType: ApiKeyType
  description?: string
  limitPeriod?: LimitPeriod
  expiresAt?: string | null
}

export interface ApiKeyCreateResponse {
  data: ApiKeyCreatedSecret
  success: boolean
}

export interface ApiKeyDeleteResponse {
  success: boolean
  id: string
}

/** Shape of the Venice `/api_keys/{id}` detail endpoint. */
export interface ApiKeyDetail {
  id: string
  apiKeyType: ApiKeyType
  description?: string
  consumptionLimits?: ConsumptionLimitInput
  limitPeriod?: LimitPeriod
  createdAt?: string | null
  expiresAt?: string | null
  last6Chars?: string
  lastUsedAt?: string | null
  usage?: { trailingSevenDays: { usd: string; diem: string } }
  currentPeriodUsage?: { usd: string; diem: string }
}

export interface TokenPrice {
  usd: number | null
  aud: number | null
  change_24h?: number | null
  market_cap?: number | null
  fdv?: number | null
}

export interface PricesData {
  vvv: TokenPrice | Record<string, number>
  diem: TokenPrice | Record<string, number>
  holdings: {
    vvv: number
    diem: number
    vvv_source?: 'manual' | 'wallet'
    diem_source?: 'manual' | 'wallet'
    vvv_wallet?: number
    svvv?: number
    unclaimed_rewards?: number
    diem_wallet?: number
    diem_staked?: number
  }
  portfolio?: {
    vvv_value_usd: number
    svvv_value_usd?: number
    unclaimed_rewards_value_usd?: number
    diem_value_usd: number
    gross_exposure_usd?: number
    diem_unlock_offset_usd?: number
    net_worth_usd?: number
    total_usd: number
  }
}

export type VvvHoldingSource = 'manual' | 'wallet'
export type DisplayCurrency = 'USD' | 'AUD'
export type DashboardWidget = 'balance' | 'usage' | 'prices' | 'usage_leaderboard'

export interface AppSettings {
  coingecko_holding_amount: number
  diem_holding_amount: number
  vvv_holding_source: VvvHoldingSource
  vvv_wallet_address: string
  benchmark_max_cost_usd: number
  benchmark_enable_billing_reconciliation: boolean
  benchmark_judge_model: string
  refresh_interval_seconds: number
  in_app_notifications_enabled: boolean
  display_currency: DisplayCurrency
  timezone: string
  dashboard_layout: DashboardWidget[]
}

export type AppSettingsUpdate = Partial<AppSettings>

export interface ModelData {
  id: string
  name?: string
  type?: string
  model_type?: string
  object?: string
  created?: number
  owned_by?: string
  model_spec?: Record<string, unknown>
  spec?: Record<string, unknown>
  input_price_usd?: number | null
  output_price_usd?: number | null
  generation_price_usd?: number | null
  cache_input_price_usd?: number | null
  cache_input_price_diem?: number | null
  cache_write_price_usd?: number | null
  cache_write_price_diem?: number | null
  supports_cache?: boolean
  capabilities?: string[] | Record<string, unknown>
  is_beta?: boolean
  context_window?: number | null
  deprecation?: {
    autoRemap?: boolean
    removesAt?: string
    replacementModelId?: string
    startsAt?: string
    date?: string
  } | null
  [key: string]: unknown
}

export interface ModelsResponse {
  models: ModelData[]
  count: number
  types: string[]
}

/**
 * Response from `GET /models/traits`. Venice returns a map of
 * trait name → recommended model id inside ``data``; the panel uses
 * this to surface Venice-curated picks next to the user-facing filters.
 */
export interface ModelTraitsResponse {
  data: Record<string, string>
  object: 'list'
  type: string
}

export interface ModelCompatibilityResponse {
  data: Record<string, string>
  object: 'list'
  type: string
}

export type TraitModelType =
  | 'text'
  | 'image'
  | 'video'
  | 'tts'
  | 'asr'
  | 'embedding'
  | 'upscale'
  | 'inpaint'
  | 'music'

// ---------------------------------------------------------------------------
// Benchmark types
// ---------------------------------------------------------------------------

export interface BenchmarkRunSummary {
  run_id: string
  filename: string
  generated_at: string
  model_count: number
  timestamp: string
}

export interface BenchmarkRunsResponse {
  runs: BenchmarkRunSummary[]
}

export interface BenchmarkCapabilities {
  supportsFunctionCalling: boolean
  supportsReasoning: boolean
  supportsReasoningEffort: boolean
  supportsResponseSchema: boolean
  supportsVision: boolean
}

export interface BenchmarkModelMeta {
  id: string
  privacy: string
  context_length: number
  max_completion_tokens: number
  capabilities: BenchmarkCapabilities
  pricing_input_usd: number | null
  pricing_output_usd: number | null
  description: string
}

export interface BenchmarkCategoryCost {
  cost_usd: number | null
  cost_per_run_usd: number | null
}

export interface BenchmarkCategory {
  runs_total: number
  runs_success: number
  runs_error: number
  runs_skip: number
  skipped: boolean
  score_mean: number | null
  score_stdev: number | null
  score_effective: number | null
  latency_mean_ms: number | null
  latency_median_ms: number | null
  latency_p90_ms: number | null
  ttft_mean_ms: number | null
  tokens_per_sec_mean: number | null
  tokens_completion_mean: number | null
  tokens_prompt_mean: number | null
  judge_scores?: Array<{ score: number; reasoning?: string }> 
}

export interface BenchmarkModelCosts {
  categories: Record<string, BenchmarkCategoryCost>
  total_cost_usd: number | null
  total_cost_per_run_usd: number | null
}

export interface BenchmarkActualBilledCategory {
  billed_usd: number | null
  billed_diem: number | null
  billed_bundled_credits: number | null
  billed_usd_equivalent: number | null
  billed_per_run_usd_equivalent?: number | null
}

export interface BenchmarkActualBilled {
  categories: Record<string, BenchmarkActualBilledCategory>
  total_usd: number
  total_diem: number
  total_bundled_credits: number
  total_usd_equivalent: number
  diem_price_usd: number | null
}

export interface BenchmarkModelResult {
  model_id: string
  model_meta: BenchmarkModelMeta
  categories: Record<string, BenchmarkCategory>
  costs?: BenchmarkModelCosts
  actual_billed?: BenchmarkActualBilled
  composite_score: number | null
  data_coverage: number | null
  judge_enabled?: boolean
  judge_model?: string | null
}

export interface BenchmarkRunDetail {
  run_id: string
  generated_at: string
  model_count: number
  total_cost_usd?: number | null
  total_actual_billed_usd?: number | null
  total_actual_billed_usd_equivalent?: number | null
  models: BenchmarkModelResult[]
}

export interface BenchmarkModel {
  id: string
  display_name: string
  privacy: string
  capabilities: BenchmarkCapabilities
  pricing_input_usd: number | null
  pricing_output_usd: number | null
  deprecation?: {
    autoRemap?: boolean
    removesAt?: string
    replacementModelId?: string
    startsAt?: string
    date?: string
  } | null
}

export interface BenchmarkModelsResponse {
  models: BenchmarkModel[]
  count: number
}

export interface BenchmarkStartParams {
  models?: string[]
  tests?: string[]
  iterations: number
  workers: number
  privacy: 'both' | 'private' | 'anonymized'
  judge?: boolean
  judge_model?: string
}

export interface BenchmarkEstimateResponse {
  model_count: number
  model_ids: string[]
  tests: string[]
  iterations: number
  workers: number
  privacy: string
  estimated_calls: number
  estimated_usd: number
  judge_cost_usd?: number
  judge_model?: string | null
  skipped_tests_note?: string | null
  note: string
}

export interface BenchmarkJobLogEntry {
  type: 'log' | 'progress' | 'error' | 'done' | string
  line: string
  ts?: number
}

export interface BenchmarkJobStatus {
  status: 'running' | 'done' | 'failed'
  run_id: string | null
  error: string | null
  progress?: { done: number; total: number; model_id?: string | null } | null
  log_count?: number
  logs?: BenchmarkJobLogEntry[]
}

// ---------------------------------------------------------------------------
// Venice Characters (preview API)
// ---------------------------------------------------------------------------

export interface CharacterStats {
  averageRating: number
  imports: number
  ratingCount: number
  ratingSum: number
  userRating: number | null
}

export interface Character {
  id: string
  name: string
  slug: string
  description: string | null
  tags: string[]
  modelId: string
  photoUrl: string | null
  shareUrl: string | null
  adult: boolean
  featured: boolean
  webEnabled: boolean
  author: string
  createdAt: string
  updatedAt: string
  stats: CharacterStats
}

export interface CharactersResponse {
  data: Character[]
  object: 'list'
}

export type CharacterSortBy =
  | 'featured'
  | 'highestRating'
  | 'highlyRated'
  | 'highlyRatedAndRecent'
  | 'imports'
  | 'mostRecent'
  | 'ratingCount'

export type CharacterSortOrder = 'asc' | 'desc'

export interface GetCharactersParams {
  search?: string
  tags?: string[]
  modelId?: string[]
  isAdult?: 'true' | 'false'
  isPro?: 'true' | 'false'
  isWebEnabled?: 'true' | 'false'
  limit?: number
  offset?: number
  sortBy?: CharacterSortBy
  sortOrder?: CharacterSortOrder
}

// ---------------------------------------------------------------------------
// History / on-chain / alerts types
// ---------------------------------------------------------------------------

export interface PriceHistoryPoint {
  timestamp: string | null
  token_id: string
  price_usd: number | null
  price_aud: number | null
  market_cap: number | null
  change_24h: number | null
}

export interface PriceHistoryResponse {
  token: string
  range: string
  count: number
  data: PriceHistoryPoint[]
}

export interface UsageTrendPoint {
  timestamp: string | null
  diem: number
  usd: number
  bundled_credits: number
  earned_credits: number
  epoch_start?: string | null
  next_epoch?: string | null
  target_date?: string | null
  scope: string
}

export interface UsageTrendsResponse {
  scope: string
  count: number
  data: UsageTrendPoint[]
}

export interface OnchainSupply {
  chain?: string
  token_symbol?: string
  network: string
  token_address: string
  staking_contract: string
  decimals: number
  source?: string
  total_supply: number
  staked_in_contract: number
  circulating_estimate: number
  burned_supply?: number
  free_float?: number | null
  free_float_pct_circulating?: number | null
  free_float_pct_total?: number | null
}

export interface OnchainStaking {
  chain?: string
  token_symbol?: string
  network: string
  token_address: string
  staking_contract: string
  staked_vvv: number
  total_supply: number | null
  staked_percent: number | null
  staking_ratio?: number | null
  staking_ratio_change_24h?: number | null
  apr?: number | null
  svvv_locked?: number | null
  svvv_unlocked?: number | null
  lock_ratio?: number | null
  staking_growth_7d?: number | null
  staking_growth_30d?: number | null
  cooldown_vvv?: number | null
  cooldown_wallets?: number | null
  source?: string
  note?: string
}

export interface OnchainBalance {
  chain?: string
  token_symbol?: string
  network: string
  address: string
  token_address: string
  vvv_balance: number
  decimals: number
}

export interface OnchainTransfer {
  from: string
  to: string
  value: string
  value_human: number
  tx_hash: string | null
  block_number: string | null
  log_index: string | null
  direction: 'in' | 'out'
}

export interface OnchainTransfersResponse {
  network: string
  address: string
  token_address: string
  transfers: OnchainTransfer[]
  count: number
  from_block: string
  to_block: string
}

export interface AlertConfig {
  id: number
  name: string
  alert_type: string
  metric: string
  threshold: number
  comparison: string
  enabled: boolean
  window_seconds?: number | null
  min_samples?: number | null
  created_at: string | null
  updated_at: string | null
}

export interface AlertEvent {
  id: number
  alert_config_id: number
  triggered_at: string | null
  message: string
  value: number
  acknowledged: boolean
}

// ---------------------------------------------------------------------------
// Slice 2.2 signal alerts
// ---------------------------------------------------------------------------

export type AlertType =
  | 'usage_percent'
  | 'balance_threshold'
  | 'price_threshold'
  | 'rate_of_change'
  | 'anomaly'

export interface AlertMetricOption {
  value: string
  label: string
}

export const ALERT_METRICS: Record<AlertType, AlertMetricOption[]> = {
  usage_percent: [
    { value: 'diem_usage_percent', label: 'DIEM usage %' },
    { value: 'usd_usage_percent', label: 'USD usage %' },
  ],
  balance_threshold: [
    { value: 'diem_balance', label: 'DIEM balance' },
    { value: 'usd_balance', label: 'USD balance' },
  ],
  price_threshold: [
    { value: 'vvv_price_usd', label: 'VVV price (USD)' },
    { value: 'diem_price_usd', label: 'DIEM price (USD)' },
  ],
  rate_of_change: [
    { value: 'vvv_price_usd', label: 'VVV price (USD)' },
    { value: 'diem_price_usd', label: 'DIEM price (USD)' },
    { value: 'diem_balance', label: 'DIEM balance' },
    { value: 'usd_balance', label: 'USD balance' },
    { value: 'diem_usage_percent', label: 'DIEM usage %' },
    { value: 'usd_usage_percent', label: 'USD usage %' },
  ],
  anomaly: [
    { value: 'vvv_price_usd', label: 'VVV price (USD)' },
    { value: 'diem_price_usd', label: 'DIEM price (USD)' },
    { value: 'diem_balance', label: 'DIEM balance' },
    { value: 'usd_balance', label: 'USD balance' },
    { value: 'diem_usage_percent', label: 'DIEM usage %' },
    { value: 'usd_usage_percent', label: 'USD usage %' },
  ],
}

// ---------------------------------------------------------------------------
// Slice 2.4 notifications
// ---------------------------------------------------------------------------

export type NotificationChannelKind =
  | 'discord'
  | 'slack'
  | 'telegram'
  | 'webhook'
  | 'email'
  | 'browser_push'

export interface NotificationChannel {
  id: number
  kind: NotificationChannelKind | string
  name: string
  enabled: boolean
  destination: string | null
  webhook_url_masked: string | null
  created_at: string | null
  updated_at: string | null
}

export interface NotificationProvider {
  kind: NotificationChannelKind | string
  available: boolean
}

export interface NotificationDelivery {
  id: number
  alert_event_id: number
  channel_id: number
  channel_name: string | null
  channel_kind: string | null
  status: 'pending' | 'sent' | 'failed' | 'skipped' | string
  attempts: number
  last_error: string | null
  next_attempt_at: string | null
  created_at: string | null
  updated_at: string | null
}

// ---------------------------------------------------------------------------
// Slice 2.5 / 2.6 on-chain views and watchlists
// ---------------------------------------------------------------------------

export interface WatchlistItem {
  id: number
  chain: string
  token: string
  address: string
  label: string | null
  created_at: string | null
}

export interface OnchainStakingEvent {
  direction: 'stake' | 'unstake' | string
  counterparty: string
  value: string
  value_human: number
  tx_hash: string | null
  block_number: string | null
  log_index: string | null
}

export interface OnchainStakingEventsResponse {
  chain: string
  network: string
  token_symbol: string
  staking_contract: string
  address: string | null
  events: OnchainStakingEvent[]
  count: number
  truncated: boolean
  from_block: string
  to_block: string
  source: string
  note: string
}

export interface OnchainHolder {
  chain: string
  address: string
  source: string
  holdings: {
    vvv_wallet: number
    svvv_total: number
    svvv_locked: number
    pending_rewards: number
    diem_wallet: number
    diem_staked: number
  }
  all_holders_available: boolean
  note: string
}

export interface ChainTokenInfo {
  symbol: string
  key: string
  address: string | null
  decimals: number
  data_sources: string[]
}

export interface ChainInfo {
  key: string
  chain_id: number
  display_name: string
  rpc_network: string
  explorer_base_url: string
  tokens: ChainTokenInfo[]
}

export interface ChainsResponse {
  approved_chains: string[]
  chains: ChainInfo[]
}

// ---------------------------------------------------------------------------
// Slice 2.7 observability
// ---------------------------------------------------------------------------

export interface RateLimitSnapshot {
  status: 'ok' | 'unavailable' | string
  reason?: string
  note?: string
  fields?: Record<string, { value: string; endpoint: string; timestamp: string }>
  last_seen_at?: string | null
}

export interface UpstreamRateLimitEvents {
  status: 'ok' | 'unavailable' | string
  reason?: string
  detail?: string
  events?: Array<Record<string, unknown>>
  count?: number
  source?: string
  note?: string
}

export interface RateLimitsResponse {
  app_limiter: { status: string; note: string }
  upstream_headers: RateLimitSnapshot
  upstream_events: UpstreamRateLimitEvents
}

export interface RpcCostSnapshot {
  status: 'ok' | 'unavailable' | string
  reason?: string
  note?: string
  totals?: { cost_usd: number; credits: number; count: number }
  latest?: { cost_usd: number | null; credits: number | null }
  sample_count?: number
  samples?: Array<{ endpoint: string; cost_usd: number | null; credits: number | null; timestamp: string }>
  source?: string
}

export interface BillingCoverage {
  status: 'confirmed' | 'unverified' | 'unavailable' | string
  reason?: string
  detail?: string
  scanned?: number
  rpc_entries?: number
  note?: string
}

export interface RpcCostsResponse {
  per_call: RpcCostSnapshot
  billing_coverage: BillingCoverage
  account_reconciliation: { status: string; note: string }
}

export interface ObservabilitySummary {
  headers: RateLimitSnapshot
  rate_limits: RateLimitSnapshot
  rpc_costs: RpcCostSnapshot
  upstream_events: UpstreamRateLimitEvents
  generated_at: string
}

// ---------------------------------------------------------------------------
// Slice 2.8 wallet session
// ---------------------------------------------------------------------------

export interface WalletChallenge {
  challenge_id: number
  address: string
  chain_id: number
  message: string
  expires_at: string
}

export interface WalletSessionInfo {
  token: string
  address: string
  chain_id: number
  expires_at: string
}

export interface WalletBalance {
  address: string
  chain: string
  chain_id: number
  holdings: OnchainHolder['holdings'] | null
  holdings_error: string | null
  onchain: OnchainBalance | null
  onchain_error: string | null
  sources: string[]
  read_only: boolean
}

// ---------------------------------------------------------------------------
// Phase 3 signals / sentiment / media / documents
// ---------------------------------------------------------------------------

export interface SignalRecord {
  id: number
  kind: string
  subject: string
  direction: 'bullish' | 'bearish' | 'neutral' | string
  confidence: number
  rationale: string
  sources: string[]
  metrics: Record<string, unknown>
  entry_price_usd: number | null
  outcome_status: 'pending' | 'hit' | 'miss' | string
  outcome_value_usd: number | null
  outcome_note: string | null
  evaluated_at: string | null
  created_at: string | null
}

export interface XSentimentResponse {
  direction: 'bullish' | 'bearish' | 'neutral' | string
  confidence: number
  summary: string
  drivers: string[]
  posts: NewsArticle[]
  sources: string[]
  model: string
  signal_id: number | null
  source: string
  note: string
}

export interface NewsSearchResult extends NewsArticle {
  score: number
}

export interface NewsAskResponse {
  answer: string
  sources: string[]
  retrieved: NewsSearchResult[]
  model?: string
}

export interface DocumentParseResponse {
  filename: string
  format: string
  input_kind: string
  characters: number
  truncated: boolean
  extracted_text: string
  summary: string
  key_points: string[]
  risk_factors: string[]
  model: string
  note: string
}

export interface BriefingResponse {
  text: string
  audio_b64: string
  mime: string
  voice: string
  model: string
}

export interface VideoRecapQueueResponse {
  queue_id: string
  model: string
  prompt: string
  status: string
}

export interface VideoRecapStatusResponse {
  queue_id: string
  model: string
  status: 'queued' | 'pending' | 'completed' | 'error' | string
  video_url?: string
  bytes?: number
  generated_at?: string
  metadata?: Record<string, unknown>
}

export interface NewsArticle { title: string; url: string | null; snippet: string; date?: string | null; source?: string | null }
export interface NewsResponse { articles: NewsArticle[]; count: number; source?: string }
export interface MarketAnalysis { summary: string; sentiment: 'bullish' | 'bearish' | 'neutral' | string; key_events: string[]; risks: string[]; confidence: number; sources: string[] }

// Typed judgments from Venice's Jev decision model (POST /decisions, beta).
export interface DecisionAnswerNoul { type: 'noul'; noul: number }
export interface DecisionAnswerChoice { type: 'choice'; choice: string; probabilities: Record<string, number>; confidence: number }
export interface DecisionAnswerScore { type: 'score'; score: number; legend: Record<string, string>; probabilities: Record<string, number>; confidence: number }
export type DecisionAnswer = DecisionAnswerNoul | DecisionAnswerChoice | DecisionAnswerScore
export interface DecisionUsage { input_tokens: number; output_tokens: number }
export interface MarketDecisions { model: string; answers: Record<string, DecisionAnswer>; usage: DecisionUsage }
/** "ok" | "unavailable" — why typed judgments are absent (Venice beta endpoint may 500). */
export type DecisionsStatus = 'ok' | 'unavailable' | string

export interface AlertConfigCreate {
  name: string
  alert_type: AlertType
  metric: string
  threshold: number
  comparison?: 'gte' | 'lte'
  enabled?: boolean
  window_seconds?: number | null
  min_samples?: number | null
}

export interface NotificationChannelCreate {
  name: string
  kind?: NotificationChannelKind
  enabled?: boolean
  webhook_url?: string
  url?: string
  telegram_bot_token?: string
  telegram_chat_id?: string
  email_to?: string
  subscription?: {
    endpoint: string
    keys: { p256dh: string; auth: string }
  }
}

export interface WatchlistCreate {
  address: string
  chain?: string
  token?: string
  label?: string | null
}

export interface SignalCreate {
  kind?: 'sentiment' | 'x_sentiment' | 'manual' | 'analysis'
  subject?: string
  direction: 'bullish' | 'bearish' | 'neutral'
  confidence: number
  rationale?: string
  sources?: string[]
  metrics?: Record<string, unknown>
  entry_price_usd?: number | null
}

export const api = {
  async getSettings(): Promise<AppSettings> {
    return fetchAPI<AppSettings>('/api/settings')
  },

  async updateSettings(payload: AppSettingsUpdate): Promise<AppSettings> {
    return fetchAPI<AppSettings>('/api/settings', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  async resetSettings(): Promise<AppSettings> {
    return fetchAPI<AppSettings>('/api/settings/reset', { method: 'POST' })
  },

  async getBalance(): Promise<BalanceData> {
    return fetchAPI<BalanceData>('/api/balance')
  },

  async getDailyUsage(date?: string): Promise<DailyUsage> {
    const params = date ? `?target_date=${date}` : ''
    return fetchAPI<DailyUsage>(`/api/usage/daily${params}`)
  },

  async getEpochUsage(): Promise<EpochUsage> {
    return fetchAPI<EpochUsage>('/api/usage/epoch')
  },

  async getAPIKeysUsage(): Promise<UsageKeysResponse> {
    return fetchAPI<UsageKeysResponse>('/api/usage/keys')
  },

  async getAPIKeyAnalytics(days = 7): Promise<APIKeyAnalyticsResponse> {
    return fetchAPI<APIKeyAnalyticsResponse>(`/api/analytics/keys?days=${days}`)
  },

  async createAPIKey(payload: ApiKeyCreatePayload): Promise<ApiKeyCreateResponse> {
    return fetchAPI<ApiKeyCreateResponse>('/api/keys', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async updateAPIKey(payload: ApiKeyUpdatePayload): Promise<unknown> {
    return fetchAPI<unknown>('/api/keys', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  async deleteAPIKey(id: string): Promise<ApiKeyDeleteResponse> {
    return fetchAPI<ApiKeyDeleteResponse>(
      `/api/keys?id=${encodeURIComponent(id)}`,
      { method: 'DELETE' },
    )
  },

  async getAPIKeyDetail(id: string): Promise<{ data: ApiKeyDetail }> {
    return fetchAPI<{ data: ApiKeyDetail }>(
      `/api/keys/${encodeURIComponent(id)}`,
    )
  },

  async getPrices(): Promise<PricesData> {
    return fetchAPI<PricesData>('/api/prices')
  },

  async getModels(): Promise<ModelsResponse> {
    return fetchAPI<ModelsResponse>('/api/models')
  },

  async getModelTraits(modelType: TraitModelType = 'text'): Promise<ModelTraitsResponse> {
    return fetchAPI<ModelTraitsResponse>(`/api/models/traits?type=${modelType}`)
  },

  async getModelCompatibilityMapping(modelType: TraitModelType | 'code' = 'text'): Promise<ModelCompatibilityResponse> {
    return fetchAPI<ModelCompatibilityResponse>(`/api/models/compatibility-mapping?type=${modelType}`)
  },

  async getHealth(): Promise<{ status: string; timestamp: string }> {
    return fetchAPI<{ status: string; timestamp: string }>('/api/health')
  },

  async get<T>(endpoint: string): Promise<T> {
    return fetchAPI<T>(endpoint)
  },

  async getPriceHistory(token: 'vvv' | 'diem' = 'vvv', range: string = '7d'): Promise<PriceHistoryResponse> {
    return fetchAPI<PriceHistoryResponse>(`/api/prices/history?token=${token}&range=${range}`)
  },

  async getUsageTrends(scope: 'epoch' | 'daily' = 'epoch', limit = 500): Promise<UsageTrendsResponse> {
    return fetchAPI<UsageTrendsResponse>(`/api/usage/history/trends?scope=${scope}&limit=${limit}`)
  },

  async getOnchainSupply(): Promise<OnchainSupply> {
    return fetchAPI<OnchainSupply>('/api/onchain/supply')
  },

  async getOnchainStaking(): Promise<OnchainStaking> {
    return fetchAPI<OnchainStaking>('/api/onchain/staking')
  },

  async getOnchainBalance(address: string): Promise<OnchainBalance> {
    return fetchAPI<OnchainBalance>(`/api/onchain/balance/${encodeURIComponent(address)}`)
  },

  async getOnchainTransfers(address: string, blocks = 10000): Promise<OnchainTransfersResponse> {
    return fetchAPI<OnchainTransfersResponse>(`/api/onchain/transfers?address=${encodeURIComponent(address)}&blocks=${blocks}`)
  },

  async getRateLimitsLog(): Promise<unknown> {
    return fetchAPI<unknown>('/api/rate-limits/log')
  },

  async getAlerts(enabledOnly = false): Promise<{ alerts: AlertConfig[]; count: number }> {
    const q = enabledOnly ? '?enabled_only=true' : ''
    return fetchAPI<{ alerts: AlertConfig[]; count: number }>(`/api/alerts${q}`)
  },

  async createAlert(body: AlertConfigCreate): Promise<AlertConfig> {
    return fetchAPI<AlertConfig>('/api/alerts', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  async updateAlert(id: number, body: Partial<AlertConfigCreate>): Promise<AlertConfig> {
    return fetchAPI<AlertConfig>(`/api/alerts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    })
  },

  async deleteAlert(id: number): Promise<{ deleted: boolean; id: number }> {
    return fetchAPI<{ deleted: boolean; id: number }>(`/api/alerts/${id}`, {
      method: 'DELETE',
    })
  },

  async getAlertEvents(unacknowledgedOnly = false): Promise<{ events: AlertEvent[]; count: number }> {
    const q = unacknowledgedOnly ? '?unacknowledged_only=true' : ''
    return fetchAPI<{ events: AlertEvent[]; count: number }>(`/api/alerts/events${q}`)
  },

  async getUnacknowledgedAlertEvents(): Promise<{ events: AlertEvent[]; count: number }> {
    return fetchAPI<{ events: AlertEvent[]; count: number }>('/api/alerts/events/unacknowledged')
  },

  async acknowledgeAlertEvent(id: number): Promise<AlertEvent> {
    return fetchAPI<AlertEvent>(`/api/alerts/events/${id}/acknowledge`, {
      method: 'POST',
    })
  },

  async evaluateAlerts(
    metrics: Record<string, number>,
    history: Record<string, Array<{ timestamp: string | null; value: number }>> = {},
  ): Promise<{ created: number; events: AlertEvent[]; skipped?: Array<{ alert_id: number; name: string; metric: string; reason: string }> }> {
    return fetchAPI<{ created: number; events: AlertEvent[]; skipped?: Array<{ alert_id: number; name: string; metric: string; reason: string }> }>('/api/alerts/evaluate', {
      method: 'POST',
      body: JSON.stringify({ metrics, history }),
    })
  },

  // Slice 2.4 — notification channels and durable deliveries
  async getNotificationProviders(): Promise<{ providers: NotificationProvider[] }> {
    return fetchAPI<{ providers: NotificationProvider[] }>('/api/notifications/providers')
  },

  async getVapidPublicKey(): Promise<{ status: string; key?: string; reason?: string }> {
    return fetchAPI<{ status: string; key?: string; reason?: string }>(
      '/api/notifications/vapid-public-key',
    )
  },

  async getNotificationChannels(): Promise<{ channels: NotificationChannel[]; count: number }> {
    return fetchAPI<{ channels: NotificationChannel[]; count: number }>('/api/notifications/channels')
  },

  async createNotificationChannel(body: NotificationChannelCreate): Promise<NotificationChannel> {
    return fetchAPI<NotificationChannel>('/api/notifications/channels', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  async updateNotificationChannel(
    id: number,
    body: Partial<NotificationChannelCreate>,
  ): Promise<NotificationChannel> {
    return fetchAPI<NotificationChannel>(`/api/notifications/channels/${id}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    })
  },

  async deleteNotificationChannel(id: number): Promise<{ deleted: boolean; id: number }> {
    return fetchAPI<{ deleted: boolean; id: number }>(`/api/notifications/channels/${id}`, {
      method: 'DELETE',
    })
  },

  async testNotificationChannel(id: number): Promise<{ status: string; error?: string }> {
    return fetchAPI<{ status: string; error?: string }>(`/api/notifications/channels/${id}/test`, {
      method: 'POST',
    })
  },

  async getNotificationDeliveries(
    status?: string,
    alertEventId?: number,
  ): Promise<{ deliveries: NotificationDelivery[]; count: number }> {
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    if (alertEventId != null) params.set('alert_event_id', String(alertEventId))
    const qs = params.toString()
    return fetchAPI<{ deliveries: NotificationDelivery[]; count: number }>(
      `/api/notifications/deliveries${qs ? `?${qs}` : ''}`,
    )
  },

  async retryNotificationDelivery(id: number): Promise<NotificationDelivery> {
    return fetchAPI<NotificationDelivery>(`/api/notifications/deliveries/${id}/retry`, {
      method: 'POST',
    })
  },

  // Slice 2.5 — watchlists, staking events, holder lookup
  async getWatchlist(): Promise<{ items: WatchlistItem[]; count: number }> {
    return fetchAPI<{ items: WatchlistItem[]; count: number }>('/api/watchlists')
  },

  async createWatchlistItem(body: WatchlistCreate): Promise<WatchlistItem> {
    return fetchAPI<WatchlistItem>('/api/watchlists', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  async deleteWatchlistItem(id: number): Promise<{ deleted: boolean; id: number }> {
    return fetchAPI<{ deleted: boolean; id: number }>(`/api/watchlists/${id}`, {
      method: 'DELETE',
    })
  },

  async getStakingEvents(
    blocks = 10000,
    address?: string,
    chain = 'base-mainnet',
    token = 'vvv',
  ): Promise<OnchainStakingEventsResponse> {
    const params = new URLSearchParams({ blocks: String(blocks), chain, token })
    if (address) params.set('address', address)
    return fetchAPI<OnchainStakingEventsResponse>(`/api/onchain/staking/events?${params.toString()}`)
  },

  async getHolderLookup(address: string, chain = 'base-mainnet'): Promise<OnchainHolder> {
    return fetchAPI<OnchainHolder>(
      `/api/onchain/holders/${encodeURIComponent(address)}?chain=${chain}`,
    )
  },

  async getChains(): Promise<ChainsResponse> {
    return fetchAPI<ChainsResponse>('/api/onchain/chains')
  },

  // Slice 2.7 — observability
  async getRateLimits(): Promise<RateLimitsResponse> {
    return fetchAPI<RateLimitsResponse>('/api/observability/rate-limits')
  },

  async getRpcCosts(): Promise<RpcCostsResponse> {
    return fetchAPI<RpcCostsResponse>('/api/observability/rpc-costs')
  },

  async getObservabilitySummary(): Promise<ObservabilitySummary> {
    return fetchAPI<ObservabilitySummary>('/api/observability/summary')
  },

  // Slice 2.8 — wallet session (read-only)
  async createWalletChallenge(address: string, chainId = 8453): Promise<WalletChallenge> {
    return fetchAPI<WalletChallenge>('/api/wallet/challenge', {
      method: 'POST',
      body: JSON.stringify({ address, chain_id: chainId }),
    })
  },

  async verifyWalletChallenge(challengeId: number, signature: string): Promise<WalletSessionInfo> {
    return fetchAPI<WalletSessionInfo>('/api/wallet/verify', {
      method: 'POST',
      body: JSON.stringify({ challenge_id: challengeId, signature }),
    })
  },

  async getWalletBalance(token: string): Promise<WalletBalance> {
    return fetchAPI<WalletBalance>('/api/wallet/balance', {
      headers: { 'X-Wallet-Token': token },
    })
  },

  async getWalletTransactions(token: string, blocks = 10000): Promise<OnchainTransfersResponse> {
    return fetchAPI<OnchainTransfersResponse>(`/api/wallet/transactions?blocks=${blocks}`, {
      headers: { 'X-Wallet-Token': token },
    })
  },

  async logoutWallet(token: string): Promise<{ logged_out: boolean }> {
    return fetchAPI<{ logged_out: boolean }>('/api/wallet/logout', {
      method: 'POST',
      headers: { 'X-Wallet-Token': token },
    })
  },

  // Phase 3 — signals, sentiment, media, documents, semantic news
  async getSignals(limit = 50): Promise<{ signals: SignalRecord[]; count: number }> {
    return fetchAPI<{ signals: SignalRecord[]; count: number }>(`/api/signals?limit=${limit}`)
  },

  async createSignal(body: SignalCreate): Promise<SignalRecord> {
    return fetchAPI<SignalRecord>('/api/signals', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  async evaluateSignal(id: number, currentPriceUsd?: number): Promise<SignalRecord> {
    return fetchAPI<SignalRecord>(`/api/signals/${id}/evaluate`, {
      method: 'POST',
      body: JSON.stringify(
        currentPriceUsd != null ? { current_price_usd: currentPriceUsd } : {},
      ),
    })
  },

  async analyzeXSentiment(
    query = 'VVV OR DIEM Venice AI crypto',
    recordSignal = true,
  ): Promise<XSentimentResponse> {
    return fetchAPI<XSentimentResponse>('/api/sentiment/x', {
      method: 'POST',
      body: JSON.stringify({ query, record_signal: recordSignal }),
    })
  },

  async searchNews(query: string, topK = 5): Promise<{ query: string; results: NewsSearchResult[]; count: number; model: string }> {
    return fetchAPI<{ query: string; results: NewsSearchResult[]; count: number; model: string }>(
      '/api/news/search',
      { method: 'POST', body: JSON.stringify({ query, top_k: topK }) },
    )
  },

  async askNews(question: string, topK = 5): Promise<NewsAskResponse> {
    return fetchAPI<NewsAskResponse>('/api/news/ask', {
      method: 'POST',
      body: JSON.stringify({ question, top_k: topK }),
    })
  },

  async parseDocument(body: { filename: string; text?: string; content_base64?: string }): Promise<DocumentParseResponse> {
    return fetchAPI<DocumentParseResponse>('/api/documents/parse', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  async askDocument(documentText: string, question: string): Promise<{ answer: string }> {
    return fetchAPI<{ answer: string }>('/api/documents/ask', {
      method: 'POST',
      body: JSON.stringify({ document_text: documentText, question }),
    })
  },

  async generateBriefing(text?: string): Promise<BriefingResponse> {
    return fetchAPI<BriefingResponse>('/api/tts/briefing', {
      method: 'POST',
      body: JSON.stringify(text ? { text } : {}),
    })
  },

  async generateAlertVoice(eventId: number): Promise<{ event_id: number; text: string; audio_b64: string; mime: string }> {
    return fetchAPI<{ event_id: number; text: string; audio_b64: string; mime: string }>(
      `/api/tts/alert/${eventId}`,
      { method: 'POST' },
    )
  },

  async generateMarketInfographic(body: {
    summary?: string
    direction?: 'bullish' | 'bearish' | 'neutral'
    confidence?: number
    key_points?: string[]
  }): Promise<{ image_b64: string; prompt: string; signal_count: number }> {
    return fetchAPI<{ image_b64: string; prompt: string; signal_count: number }>(
      '/api/insights/infographic',
      { method: 'POST', body: JSON.stringify(body) },
    )
  },

  async queueVideoRecap(body: { prompt?: string; duration?: string; resolution?: string } = {}): Promise<VideoRecapQueueResponse> {
    return fetchAPI<VideoRecapQueueResponse>('/api/video/recap', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  async getVideoRecap(queueId: string, model?: string): Promise<VideoRecapStatusResponse> {
    const params = new URLSearchParams()
    if (model) params.set('model', model)
    const qs = params.toString()
    return fetchAPI<VideoRecapStatusResponse>(
      `/api/video/recap/${encodeURIComponent(queueId)}${qs ? `?${qs}` : ''}`,
    )
  },

  async getNews(refresh = false): Promise<NewsResponse> {
    return fetchAPI<NewsResponse>(`/api/news${refresh ? '?refresh=true' : ''}`)
  },
  async getNewsArticle(url: string): Promise<{ url: string; title: string; content: string }> {
    return fetchAPI<{ url: string; title: string; content: string }>(`/api/news/article?url=${encodeURIComponent(url)}`)
  },
  async analyzeMarket(prices: Record<string, unknown> = {}, usage: Record<string, unknown> = {}): Promise<{ analysis: MarketAnalysis; articles: NewsArticle[]; decisions: MarketDecisions | null; decisions_status?: DecisionsStatus; signal_id?: number | null }> {
    return fetchAPI<{ analysis: MarketAnalysis; articles: NewsArticle[]; decisions: MarketDecisions | null; decisions_status?: DecisionsStatus; signal_id?: number | null }>('/api/insights/analyze', { method: 'POST', body: JSON.stringify({ prices, usage }) })
  },
  async queryAssistant(query: string, history: Array<{ role: string; content: string }> = []): Promise<{ answer: string; tool_calls: unknown[] }> {
    return fetchAPI<{ answer: string; tool_calls: unknown[] }>('/api/assistant/query', { method: 'POST', body: JSON.stringify({ query, history }) })
  },

  // Benchmark endpoints
  async getBenchmarkRuns(): Promise<BenchmarkRunsResponse> {
    return fetchAPI<BenchmarkRunsResponse>('/api/benchmark/runs')
  },

  async getBenchmarkRun(runId: string): Promise<BenchmarkRunDetail> {
    return fetchAPI<BenchmarkRunDetail>(`/api/benchmark/runs/${encodeURIComponent(runId)}`)
  },

  async getBenchmarkModels(): Promise<BenchmarkModelsResponse> {
    return fetchAPI<BenchmarkModelsResponse>('/api/benchmark/models')
  },

  async estimateBenchmark(params: BenchmarkStartParams): Promise<BenchmarkEstimateResponse> {
    return fetchAPI<BenchmarkEstimateResponse>('/api/benchmark/estimate', {
      method: 'POST',
      body: JSON.stringify(params),
    })
  },

  async startBenchmark(params: BenchmarkStartParams): Promise<{ job_id: string }> {
    return fetchAPI<{ job_id: string }>('/api/benchmark/start', {
      method: 'POST',
      body: JSON.stringify(params),
    })
  },

  async getBenchmarkStatus(jobId: string): Promise<BenchmarkJobStatus> {
    return fetchAPI<BenchmarkJobStatus>(`/api/benchmark/status/${encodeURIComponent(jobId)}`)
  },

  async cancelBenchmark(jobId: string): Promise<{ status: string; message: string }> {
    return fetchAPI<{ status: string; message: string }>(
      `/api/benchmark/cancel/${encodeURIComponent(jobId)}`,
      { method: 'POST' },
    )
  },

  async generateInfographic(runId: string): Promise<{ image_b64: string; prompt: string }> {
    return fetchAPI<{ image_b64: string; prompt: string }>(
      `/api/benchmark/infographic/${encodeURIComponent(runId)}`,
      { method: 'POST' },
    )
  },

  // Character endpoints
  async getCharacters(params: GetCharactersParams = {}): Promise<CharactersResponse> {
    const search = new URLSearchParams()
    if (params.search) search.set('search', params.search)
    if (params.limit != null) search.set('limit', String(params.limit))
    if (params.offset != null) search.set('offset', String(params.offset))
    if (params.sortBy) search.set('sortBy', params.sortBy)
    if (params.sortOrder) search.set('sortOrder', params.sortOrder)
    if (params.isAdult) search.set('isAdult', params.isAdult)
    if (params.isPro) search.set('isPro', params.isPro)
    if (params.isWebEnabled) search.set('isWebEnabled', params.isWebEnabled)
    if (params.tags?.length) {
      params.tags.forEach((t) => search.append('tags', t))
    }
    if (params.modelId?.length) {
      params.modelId.forEach((m) => search.append('modelId', m))
    }
    const qs = search.toString()
    const path = qs ? `/api/characters?${qs}` : '/api/characters'
    return fetchAPI<CharactersResponse>(path)
  },

  async getCharacter(slug: string): Promise<{ data: Character; object: 'character' }> {
    return fetchAPI<{ data: Character; object: 'character' }>(
      `/api/characters/${encodeURIComponent(slug)}`,
    )
  },
}
