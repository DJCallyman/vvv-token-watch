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
}

export interface DailyUsage {
  date: string
  diem: number
  usd: number
  bundled_credits?: number
  // epoch_start removed — use EpochUsage (getEpochUsage) for epoch data
}

export interface EpochUsage {
  diem: number
  usd: number
  bundled_credits: number
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
}

export interface UsageKeysResponse {
  keys: APIKeyUsage[]
}

export interface PricesData {
  vvv: Record<string, number>
  diem: Record<string, number>
  holdings: {
    vvv: number
    diem: number
  }
  portfolio?: {
    vvv_value_usd: number
    diem_value_usd: number
    total_usd: number
  }
}

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
  network: string
  token_address: string
  staking_contract: string
  decimals: number
  total_supply: number
  staked_in_contract: number
  circulating_estimate: number
}

export interface OnchainStaking {
  network: string
  token_address: string
  staking_contract: string
  staked_vvv: number
  total_supply: number
  staked_percent: number
  note?: string
}

export interface OnchainBalance {
  network: string
  address: string
  token_address: string
  vvv_balance: number
  decimals: number
}

export interface AlertConfig {
  id: number
  name: string
  alert_type: string
  metric: string
  threshold: number
  comparison: string
  enabled: boolean
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

export interface AlertConfigCreate {
  name: string
  alert_type: 'usage_percent' | 'balance_threshold' | 'price_threshold'
  metric: string
  threshold: number
  comparison?: 'gte' | 'lte'
  enabled?: boolean
}

export const api = {
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

  async getPrices(): Promise<PricesData> {
    return fetchAPI<PricesData>('/api/prices')
  },

  async getModels(): Promise<ModelsResponse> {
    return fetchAPI<ModelsResponse>('/api/models')
  },

  async getModelTraits(): Promise<Record<string, unknown>> {
    return fetchAPI<Record<string, unknown>>('/api/models/traits')
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

  async evaluateAlerts(metrics: Record<string, number>): Promise<{ created: number; events: AlertEvent[] }> {
    return fetchAPI<{ created: number; events: AlertEvent[] }>('/api/alerts/evaluate', {
      method: 'POST',
      body: JSON.stringify({ metrics }),
    })
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
}