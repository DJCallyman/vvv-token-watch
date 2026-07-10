const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''
const APP_PASSWORD = process.env.NEXT_PUBLIC_APP_PASSWORD || ''

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string> | undefined),
  }
  if (APP_PASSWORD) {
    headers.Authorization = `Bearer ${APP_PASSWORD}`
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}

export interface BalanceData {
  diem: number
  usd: number
  daily_diem_limit: number
  daily_usd_limit: number
  next_epoch_begins: string | null
  diem_usage_percent: number
  usd_usage_percent: number
  consumption_currency?: string
  can_consume?: boolean
  diem_epoch_allocation?: number | null
}

export interface DailyUsage {
  date: string
  diem: number
  usd: number
  epoch_start?: string
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

export interface BenchmarkModelResult {
  model_id: string
  model_meta: BenchmarkModelMeta
  categories: Record<string, BenchmarkCategory>
  composite_score: number | null
  data_coverage: number | null
}

export interface BenchmarkRunDetail {
  run_id: string
  generated_at: string
  model_count: number
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

export interface BenchmarkJobStatus {
  status: 'running' | 'done' | 'failed'
  run_id: string | null
  error: string | null
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

  async startBenchmark(params: BenchmarkStartParams): Promise<{ job_id: string }> {
    return fetchAPI<{ job_id: string }>('/api/benchmark/start', {
      method: 'POST',
      body: JSON.stringify(params),
    })
  },

  async getBenchmarkStatus(jobId: string): Promise<BenchmarkJobStatus> {
    return fetchAPI<BenchmarkJobStatus>(`/api/benchmark/status/${encodeURIComponent(jobId)}`)
  },

  async generateInfographic(runId: string): Promise<{ image_b64: string; prompt: string }> {
    return fetchAPI<{ image_b64: string; prompt: string }>(
      `/api/benchmark/infographic/${encodeURIComponent(runId)}`,
      { method: 'POST' },
    )
  },
}